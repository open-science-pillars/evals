# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Open Science Pillars eval runner.

Headless N-trial execution of the plugins' eval cases against a runtime (Claude
Code by default), with programmatic + rubric-judge grading and binomial-CI
pass rates. Every results file carries the cross-runtime record (record.py):
capability, version, release lock, runtime and projection, model, judge model,
suite, trials and date, so identical cases compare across runtimes. A trial passes
only if every grader present agrees (programmatic AND rubric): the programmatic
check is a conservative gate, the judge is authoritative.

Usage:
  uv run runner/run_evals.py --manifest manifests/ocean-science.yaml --trials 20 \
      --workspace /path/to/osp --model claude-fable-5 --out scoreboard/results.json \
      --transcripts scoreboard/transcripts
  # add --cases id1,id2 to run a subset; --trials 3 for a quick demonstration.

Every trial's verdict is recorded in the results file (elapsed seconds, error
kind, grader outcomes and the judge's reason), so a failed case can be read
without rerunning it. With --transcripts DIR the transcript itself, the
stderr and the grader detail of every trial are written under
DIR/<case id>/trial<n>.* as well; a rate is not a diagnosis, the transcript is.

The full N=20 sweep is a CI job (hundreds of agentic invocations); on a laptop
run a subset at low --trials to demonstrate the runner reproduces seed grades.
"""
import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import run_programmatic  # noqa: E402
from judge import judge_trial  # noqa: E402
from toolspec import tool_names  # noqa: E402
from stats import verdict  # noqa: E402
from record import RUNTIMES, build_record  # noqa: E402
from drivers import command_for  # noqa: E402


# A trial that never really ran. The turn limit belongs here and did not
# carry one until 2026-09-21: "Error: Reached max turns (12)" is 29
# characters, so it cleared the empty-transcript test by nine, and it says
# "reached max" rather than "reached your", so it cleared the quota test
# too. It was scored as a substantive failure instead, which is what the
# comment below already says it must not be.
ERROR_MARKERS = ("reached your", "usage-credits", "/usage-credits")
# The turn limit, which carried no marker until 2026-09-21: "Error: Reached
# max turns (12)" is 29 characters, so it cleared the empty-transcript test by
# nine, and it says "reached max" rather than "reached your", so it cleared the
# quota test too. It was scored as a substantive failure instead, which is what
# the comment below already says it must not be.
TURN_LIMIT = re.compile(r"reached max turns", re.I)

# A trial at 30 turns has been measured above 600 s with judging still to
# come; the default leaves headroom so a slow but complete trial is graded
# rather than discarded. A trial past the limit is an error, never a failure.
DEFAULT_TIMEOUT = 1200

# Serialises trial lines when an arm runs its trials concurrently.
PRINT_LOCK = threading.Lock()


def read_dirs_for(ws, plugin: str):
    """The checkout under test, plus the plugin bundles it declares as
    dependencies and that are present in the workspace.

    A concept a plugin relies on can live in another bundle: the DSWx
    concepts a hydrology case tests are in the provider bundle, because
    provider-product facts belong there. Opening only the plugin under
    test would measure the isolation rather than the knowledge, and a
    trial would fail for want of a file a real install would have."""
    dirs = [ws / plugin]
    manifest = ws / plugin / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        try:
            for dep in json.loads(manifest.read_text()).get("dependencies", []):
                d = ws / dep.get("name", "")
                if d.is_dir() and d not in dirs:
                    dirs.append(d)
        except (json.JSONDecodeError, OSError):
            pass
    return dirs


def run_trial(prompt, allowed_tools, max_turns, model, timeout=DEFAULT_TIMEOUT,
              claude_args=(), runtime="claude-code"):
    """One headless trial on the runtime (Claude Code unless told otherwise).

    Returns (stdout, stderr, elapsed_seconds, timed_out). On a timeout the
    partial stdout is returned so it can be kept beside the error.
    claude_args are handed to the runtime's command verbatim (a --plugin-dir
    for a checkout under test, a --settings override); the results file
    records them."""
    cmd, stdin_text, _ = command_for(runtime, prompt, allowed_tools, max_turns, model, claude_args)
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=stdin_text)
        return r.stdout, r.stderr, time.monotonic() - t0, False
    except subprocess.TimeoutExpired as e:
        def _text(b):
            return b.decode(errors="replace") if isinstance(b, bytes) else (b or "")
        return _text(e.stdout), _text(e.stderr), time.monotonic() - t0, True


def is_error_transcript(t):
    """A trial that never really ran (empty, or a quota/limit message) must not
    be counted as a failure: it is an infrastructure error, tracked separately."""
    if len(t.strip()) < 20:
        return True
    low = t.lower()
    # Turn exhaustion is an outage at any length: a trial cut off after twelve
    # turns of real work was still cut off rather than answered, and counting
    # it as a failure reads the harness's own bound as the package's behaviour.
    # Anchored on the transcript ending in the runner's error line, so a
    # complete answer that happens to discuss turn limits is not swept up.
    last = next((ln for ln in reversed(low.splitlines()) if ln.strip()), "")
    if TURN_LIMIT.search(last):
        return True
    return any(m in low for m in ERROR_MARKERS) and len(t) < 400


# The rubric spec that means "the case's own notes are the rubric". Spelled
# out rather than inferred from a lookup that missed.
RUBRIC_FROM_NOTES = "notes"


def resolve_rubric(case, ws):
    """The text that grades this case, and a record of where it came from.

    Three forms, and a name that resolves to nothing is not one of them. A
    value holding whitespace is the rubric itself, written inline. The exact
    word `notes` is the case's own notes field, which already states pass and
    fail intent. Anything else is a path under the plugin's evals directory
    and has to exist.

    Until 2026-09-22 a path that did not exist fell through to the notes in
    silence. Nine cases named rubric documents that have never existed
    anywhere in the workspace, including all seven of the ablation's, so the
    grader in force was never the grader the case named and no results file
    said which text had graded it. The pre-registration commits to grading
    both arms by the same rubric per case and to freezing the grader before
    the second arm runs; neither is checkable against a record that does not
    hold the rubric. Raises ValueError so a caller can collect every case's
    problem instead of stopping at the first.
    """
    spec = ""
    for g in case.get("graders", []):
        if "rubric" in g:
            spec = str(g["rubric"])
    if not spec.strip():
        return None, None
    if any(c.isspace() for c in spec.strip()):
        return spec, "inline"
    if spec.strip() == RUBRIC_FROM_NOTES:
        notes = (case.get("notes") or "").strip()
        if not notes:
            raise ValueError(f"{case['id']}: its rubric is `{RUBRIC_FROM_NOTES}` "
                             "and the case has no notes to grade against")
        return f"Grade this trial against the eval case's intent:\n{notes}", "notes"
    rp = ws / case["_plugin"] / "evals" / spec.strip()
    if not rp.is_file():
        raise ValueError(f"{case['id']}: names the rubric {spec.strip()}, which is not "
                         f"at {rp}. Write it, or say `rubric: {RUBRIC_FROM_NOTES}` to "
                         "grade against the case's own notes.")
    return rp.read_text(), str(rp)


def grade(case, transcript, ws, no_judge=False, model="claude-fable-5"):
    """A trial passes iff every present grader agrees.

    Returns (ok, results, judge_error): a judge that did not answer sets
    judge_error, and the caller records the trial as an infrastructure error
    rather than as a failure."""
    results = {}
    ok = True
    judge_error = None
    for g in case.get("graders", []):
        if "programmatic" in g:
            p = run_programmatic(g["programmatic"], transcript)
            if p is not None:
                results["programmatic"] = p
                ok = ok and p
        if "rubric" in g and not no_judge:
            # Resolved once per case before any trial runs, so a case cannot
            # discover mid-arm that the text grading it is not the text it names.
            rubric = case["_rubric"]
            j = judge_trial(rubric, transcript, model=model)
            results["rubric"] = j
            if j.get("grade") == "ERROR":
                judge_error = j.get("reason", "judge error")
            ok = ok and (j.get("grade") == "PASS")
    return ok, results, judge_error


def keep(tdir, n, transcript, stderr, detail):
    """Write one trial's transcript, stderr and grader detail under tdir."""
    if tdir is None:
        return
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f"trial{n}.txt").write_text(transcript)
    (tdir / f"trial{n}.stderr").write_text(stderr)
    (tdir / f"trial{n}.json").write_text(json.dumps(detail, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--model", default="claude-fable-5")
    ap.add_argument("--cases", default="")
    ap.add_argument("--concurrency", type=int, default=1,
                    help="trials to run at once within one arm; the arm change is never "
                         "concurrent, so this changes when trials run and not what they do")
    ap.add_argument("--out", default="scoreboard/results.json")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="seconds allowed per trial before it is recorded as an error")
    ap.add_argument("--transcripts", default="",
                    help="directory to keep every trial's transcript, stderr and grader detail")
    ap.add_argument("--bundle", default="on", choices=["on", "off"],
                    help="knowledge bundle present ('on') or removed ('off') for the ablation")
    ap.add_argument("--no-judge", action="store_true",
                    help="programmatic graders only; skip the LLM rubric judge (faster pilot)")
    ap.add_argument("--claude-arg", action="append", default=[],
                    help="extra argument handed to claude verbatim, repeatable (for example "
                         "--claude-arg=--plugin-dir --claude-arg=/path/to/checkout to test a "
                         "checkout, or a --settings override); recorded in the results file")
    ap.add_argument("--runtime", default="claude-code", choices=sorted(RUNTIMES),
                    help="the runtime the trials run on; recorded with its projection and version")
    ap.add_argument("--runtime-version", default=None,
                    help="the runtime's version string, when its CLI cannot be asked")
    ap.add_argument("--judge-model", default=None,
                    help="model for the rubric judge (default: --model); the judge is a Claude Code "
                         "call on every runtime, so grading is held constant")
    ap.add_argument("--no-lock-check", action="store_true",
                    help="record the release lock without asking build-kit whether it is current")
    args = ap.parse_args()
    judge_model = args.judge_model or args.model

    ws = Path(args.workspace)
    man = yaml.safe_load(Path(args.manifest).read_text())
    only = set(filter(None, args.cases.split(",")))
    troot = Path(args.transcripts) if args.transcripts else None

    selected = [e for e in man["cases"] if not only or e["id"] in only]
    plugins = [e["plugin"] for e in selected]

    # Every selected case's rubric is resolved before the first trial runs. A
    # case naming a rubric that resolves to nothing stops the run here instead
    # of being graded quietly by something else, and the text that grades a
    # case is fixed before any trial sees it.
    rubrics, unresolved = {}, []
    for entry in selected:
        pre = yaml.safe_load((ws / entry["case"]).read_text())
        pre["_plugin"] = entry["plugin"]
        try:
            rubrics[entry["id"]] = resolve_rubric(pre, ws)
        except ValueError as exc:
            unresolved.append(str(exc))
    if unresolved:
        print("ERROR: a case names a rubric that does not resolve, so the grader in "
              "force would not be the grader the case names:")
        for u in unresolved:
            print("  " + u)
        raise SystemExit(1)
    record = build_record(ws, plugins, args.runtime, args.runtime_version, args.model,
                          judge_model, man["name"], args.trials, check_lock=not args.no_lock_check)
    out = {"manifest": man["name"], "model": args.model, "bundle": args.bundle,
           "trials": args.trials, "timeout": args.timeout,
           "claude_args": args.claude_arg, **record, "cases": []}
    for name, cap in record["capabilities"].items():
        lock = cap["release_lock"] or "no release lock"
        current = {True: "current", False: "STALE", None: "unchecked"}[cap["release_lock_current"]]
        print(f"{name} {cap['version']}: {lock} ({current}) on {args.runtime} "
              f"({record['runtime']['version'] or 'version unknown'})", flush=True)
    for entry in selected:
        case = yaml.safe_load((ws / entry["case"]).read_text())
        case["_plugin"] = entry["plugin"]
        case["_rubric"], rubric_source = rubrics[entry["id"]]
        max_turns = entry.get("max_turns", 20)
        tdir = troot / entry["id"] if troot else None
        def one_trial(n):
            """One trial, whole: run it, grade it, keep it. Independent of every
            other trial in this arm, which is why they may run together."""
            t, err, elapsed, timed_out = run_trial(
                case["prompt"], entry["allowed_tools"], max_turns, args.model,
                timeout=args.timeout, claude_args=args.claude_arg, runtime=args.runtime)
            detail = {"trial": n, "elapsed_s": round(elapsed), "chars": len(t)}
            if timed_out or is_error_transcript(t):
                detail["error"] = "timeout" if timed_out else "empty or limit message"
            else:
                ok, graders, judge_error = grade(case, t, ws, no_judge=args.no_judge,
                                                 model=judge_model)
                detail["graders"] = graders
                if judge_error:
                    # The trial ran; the judge did not. Counting this as a
                    # failure would put a wrong rate in the record.
                    detail["error"] = f"judge unavailable ({judge_error})"
                else:
                    detail["pass"] = ok
            keep(tdir, n, t, err, detail)
            state = detail.get("error") or ("PASS" if detail["pass"] else "FAIL")
            # One line at a time, or concurrent trials interleave mid-line and
            # the run log stops being readable at the moment it matters most.
            with PRINT_LOCK:
                print(f"  {entry['id']} trial {n}: {state} ({detail['elapsed_s']}s, "
                      f"{detail['chars']} chars)", flush=True)
            return detail

        # Trials inside one arm are independent and may run together. What must
        # never overlap is the arm change: ablate.sh moves the installed
        # knowledge tree between the arms, on a plugin cache every trial shares,
        # and two runs sharing one cache disagreed with each other on
        # 2026-09-21 and were both discarded. Within an arm the tree does not
        # move, so concurrency here changes when trials run and nothing about
        # what any one of them does.
        if args.concurrency > 1:
            with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                trials = list(pool.map(one_trial, range(1, args.trials + 1)))
        else:
            trials = [one_trial(n) for n in range(1, args.trials + 1)]
        trials.sort(key=lambda d: d["trial"])
        errors = sum(1 for d in trials if "error" in d)
        passes = sum(1 for d in trials if d.get("pass"))
        valid = args.trials - errors
        v = verdict(passes, valid, case.get("pass_threshold", 0.8))
        v["id"] = entry["id"]
        v["type"] = case.get("type")
        cap = record["capabilities"][entry["plugin"]]
        v["capability"] = cap["name"]
        v["capability_version"] = cap["version"]
        v["release_lock"] = cap["release_lock"]
        v["errors"] = errors
        v["trials_requested"] = args.trials
        v["max_turns"] = max_turns
        # Which text graded this case, so a reader can check the arms were
        # graded alike without rerunning either of them.
        v["rubric"] = rubric_source
        v["trial_detail"] = trials
        out["cases"].append(v)
        flag = " (ALL TRIALS ERRORED)" if valid == 0 else ""
        print(f"{entry['id']}: {v['passes']}/{valid} valid (rate {v['rate']}, "
              f"{errors} errors) CI {v['ci95']} -> {'PASS' if v['pass'] else 'FAIL'}{flag}",
              flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
