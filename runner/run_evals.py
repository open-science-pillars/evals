#!/usr/bin/env python3
"""Open Science Pillars eval runner.

Headless N-trial execution of the plugins' eval cases against Claude Code, with
programmatic + rubric-judge grading and binomial-CI pass rates. A trial passes
only if every grader present agrees (programmatic AND rubric): the programmatic
check is a conservative gate, the judge is authoritative.

Usage:
  python run_evals.py --manifest manifests/ocean-science.yaml --trials 20 \
      --workspace /path/to/osp --model claude-fable-5 --out scoreboard/results.json
  # add --cases id1,id2 to run a subset; --trials 3 for a quick demonstration.

The full N=20 sweep is a CI job (hundreds of agentic invocations); on a laptop
run a subset at low --trials to demonstrate the runner reproduces seed grades.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import run_programmatic  # noqa: E402
from judge import judge_trial  # noqa: E402
from stats import verdict  # noqa: E402


ERROR_MARKERS = ("reached your", "usage-credits", "/usage-credits")


def run_trial(prompt, allowed_tools, max_turns, model, timeout=600):
    """One headless Claude Code trial; returns the transcript text."""
    try:
        r = subprocess.run(
            ["claude", "-p", prompt, "--model", model,
             "--allowedTools", allowed_tools, "--max-turns", str(max_turns)],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""


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
            # A dedicated rubric file overrides; otherwise the case's own
            # `notes` field is the rubric (it already states pass/fail intent).
            rp = ws / case["_plugin"] / "evals" / g["rubric"]
            rubric = rp.read_text() if rp.exists() else (
                f"Grade this trial against the eval case's intent:\n{case.get('notes', '')}")
            j = judge_trial(rubric, transcript)
            results["rubric"] = j
            ok = ok and (j.get("grade") == "PASS")
    return ok, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--model", default="claude-fable-5")
    ap.add_argument("--cases", default="")
    ap.add_argument("--out", default="scoreboard/results.json")
    ap.add_argument("--bundle", default="on", choices=["on", "off"],
                    help="knowledge bundle present ('on') or removed ('off') for the ablation")
    ap.add_argument("--no-judge", action="store_true",
                    help="programmatic graders only; skip the LLM rubric judge (faster pilot)")
    args = ap.parse_args()

    ws = Path(args.workspace)
    man = yaml.safe_load(Path(args.manifest).read_text())
    only = set(filter(None, args.cases.split(",")))

    out = {"manifest": man["name"], "model": args.model, "bundle": args.bundle,
           "trials": args.trials, "cases": []}
    for entry in man["cases"]:
        if only and entry["id"] not in only:
            continue
        case = yaml.safe_load((ws / entry["case"]).read_text())
        case["_plugin"] = entry["plugin"]
        passes = 0
        errors = 0
        for _ in range(args.trials):
            t = run_trial(case["prompt"], entry["allowed_tools"],
                          entry.get("max_turns", 20), args.model)
            if is_error_transcript(t):
                errors += 1
                continue
            ok, _detail = grade(case, t, ws, no_judge=args.no_judge)
            passes += int(ok)
        valid = args.trials - errors
        v = verdict(passes, valid, case.get("pass_threshold", 0.8))
        v["id"] = entry["id"]
        v["type"] = case.get("type")
        v["errors"] = errors
        v["trials_requested"] = args.trials
        out["cases"].append(v)
        flag = " (ALL TRIALS ERRORED)" if valid == 0 else ""
        print(f"{entry['id']}: {v['passes']}/{valid} valid (rate {v['rate']}, "
              f"{errors} errors) CI {v['ci95']} -> {'PASS' if v['pass'] else 'FAIL'}{flag}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
