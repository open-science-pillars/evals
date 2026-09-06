# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Open Science Pillars eval runner.

Headless N-trial execution of the plugins' eval cases against Claude Code, with
programmatic + rubric-judge grading and binomial-CI pass rates. A trial passes
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
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import run_programmatic  # noqa: E402
from judge import judge_trial  # noqa: E402
from stats import verdict  # noqa: E402


ERROR_MARKERS = ("reached your", "usage-credits", "/usage-credits")

# A trial at 30 turns has been measured above 600 s with judging still to
# come; the default leaves headroom so a slow but complete trial is graded
# rather than discarded. A trial past the limit is an error, never a failure.
DEFAULT_TIMEOUT = 1200


def run_trial(prompt, allowed_tools, max_turns, model, timeout=DEFAULT_TIMEOUT):
    """One headless Claude Code trial.

    Returns (stdout, stderr, elapsed_seconds, timed_out). On a timeout the
    partial stdout is returned so it can be kept beside the error."""
    cmd = ["claude", "-p", prompt, "--model", model,
           "--allowedTools", allowed_tools, "--max-turns", str(max_turns)]
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
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
    return any(m in t.lower() for m in ERROR_MARKERS) and len(t) < 400


def grade(case, transcript, ws, no_judge=False):
    """A trial passes iff every present grader agrees."""
    results = {}
    ok = True
    for g in case.get("graders", []):
        if "programmatic" in g:
            p = run_programmatic(g["programmatic"], transcript)
            if p is not None:
                results["programmatic"] = p
                ok = ok and p
        if "rubric" in g and not no_judge:
            # A dedicated rubric file overrides; a case may also carry the
            # rubric text inline (a value with whitespace is text, not a
            # path); otherwise the case's own `notes` field is the rubric
            # (it already states pass/fail intent).
            spec = g["rubric"]
            rp = ws / case["_plugin"] / "evals" / spec
            if spec.strip() and not any(c.isspace() for c in spec.strip()) and rp.exists():
                rubric = rp.read_text()
            elif any(c.isspace() for c in spec.strip()):
                rubric = spec
            else:
                rubric = f"Grade this trial against the eval case's intent:\n{case.get('notes', '')}"
            j = judge_trial(rubric, transcript)
            results["rubric"] = j
            ok = ok and (j.get("grade") == "PASS")
    return ok, results


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
    ap.add_argument("--out", default="scoreboard/results.json")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="seconds allowed per trial before it is recorded as an error")
    ap.add_argument("--transcripts", default="",
                    help="directory to keep every trial's transcript, stderr and grader detail")
    ap.add_argument("--bundle", default="on", choices=["on", "off"],
                    help="knowledge bundle present ('on') or removed ('off') for the ablation")
    ap.add_argument("--no-judge", action="store_true",
                    help="programmatic graders only; skip the LLM rubric judge (faster pilot)")
    args = ap.parse_args()

    ws = Path(args.workspace)
    man = yaml.safe_load(Path(args.manifest).read_text())
    only = set(filter(None, args.cases.split(",")))
    troot = Path(args.transcripts) if args.transcripts else None

    out = {"manifest": man["name"], "model": args.model, "bundle": args.bundle,
           "trials": args.trials, "timeout": args.timeout, "cases": []}
    for entry in man["cases"]:
        if only and entry["id"] not in only:
            continue
        case = yaml.safe_load((ws / entry["case"]).read_text())
        case["_plugin"] = entry["plugin"]
        max_turns = entry.get("max_turns", 20)
        tdir = troot / entry["id"] if troot else None
        passes = 0
        errors = 0
        trials = []
        for n in range(1, args.trials + 1):
            t, err, elapsed, timed_out = run_trial(
                case["prompt"], entry["allowed_tools"], max_turns, args.model,
                timeout=args.timeout)
            detail = {"trial": n, "elapsed_s": round(elapsed), "chars": len(t)}
            if timed_out or is_error_transcript(t):
                detail["error"] = "timeout" if timed_out else "empty or limit message"
                errors += 1
            else:
                ok, graders = grade(case, t, ws, no_judge=args.no_judge)
                detail["pass"] = ok
                detail["graders"] = graders
                passes += int(ok)
            trials.append(detail)
            keep(tdir, n, t, err, detail)
            state = detail.get("error") or ("PASS" if detail["pass"] else "FAIL")
            print(f"  {entry['id']} trial {n}: {state} ({detail['elapsed_s']}s, "
                  f"{detail['chars']} chars)", flush=True)
        valid = args.trials - errors
        v = verdict(passes, valid, case.get("pass_threshold", 0.8))
        v["id"] = entry["id"]
        v["type"] = case.get("type")
        v["errors"] = errors
        v["trials_requested"] = args.trials
        v["max_turns"] = max_turns
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
