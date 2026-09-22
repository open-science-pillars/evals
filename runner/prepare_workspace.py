"""Build the workspace a run may use, from one that holds more than it may.

A trial reads whatever is on the machine. Setting the subprocess working
directory does not change that: a headless run whose working directory was an
empty temporary directory read an absolute path under the workspace without
difficulty, checked on 2026-09-22. So the only workspace that keeps a run honest
is one that does not contain the things a trial must not see, and this builds it.

What comes out is not smaller for tidiness. Two kinds of file defeat the
experiment and they defeat it differently:

  a recorded answer   a graded answer to a case the run will grade contaminates
                      the rate in both arms, so it is removed here and never
                      restored
  a knowledge tree    the checked-out copy of the bundle defeats the contrast
                      between the arms, and it stays, because the release lock
                      digests it and ablate.sh moves it aside for both arms once
                      the lock has been checked

The result is certified rather than asserted: leak_check runs over the prepared
tree and the preparation fails if an answer survives it.

  uv run runner/prepare_workspace.py /home/user /home/user/run
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Directory names that never belong in a run workspace. `transcripts` and
# `results` hold graded answers to these very cases, under three earlier result
# sets and this repository's own grader fixtures; `grader-calibration` holds
# answers written to calibrate a grader; `scoreboard` holds prior runs' per-trial
# detail, judge reasons included.
DROP_DIRS = {".git", "transcripts", "results", "grader-calibration", "scoreboard",
             "__pycache__", ".venv", "node_modules"}


def prepare(source: Path, dest: Path) -> list[str]:
    """Copy the workspace without the directories a run may not hold."""
    dropped = []

    def ignore(directory, names):
        skip = {n for n in names if n in DROP_DIRS}
        for n in sorted(skip):
            dropped.append(str(Path(directory, n).relative_to(source)))
        return skip

    if dest.exists():
        raise SystemExit(f"{dest} exists; prepare writes a fresh tree and will not "
                         "merge into one that is already there")
    shutil.copytree(source, dest, ignore=ignore, symlinks=True)
    return dropped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("dest")
    ap.add_argument("--manifest", default="evals/manifests/ablation.yaml",
                    help="relative to the prepared workspace")
    ap.add_argument("--cases", default="")
    args = ap.parse_args()

    source, dest = Path(args.source).resolve(), Path(args.dest).resolve()
    if dest.is_relative_to(source):
        raise SystemExit(f"{dest} is inside {source}; the copy would descend into "
                         "itself and the prepared tree would contain the source")

    dropped = prepare(source, dest)
    print(f"prepared {dest} from {source}, without {len(dropped)} director"
          f"{'y' if len(dropped) == 1 else 'ies'}:")
    for d in dropped:
        print("  " + d)

    marks = dest / "evals" / "runner" / "concept-fingerprints.json"
    cmd = ["uv", "run", "--with", "pyyaml==6.0.2",
           str(dest / "evals" / "runner" / "leak_check.py"), str(dest),
           str(dest / args.manifest), "--arm", "on", "--root", str(dest)]
    if marks.is_file():
        cmd += ["--fingerprints", str(marks)]
    if args.cases:
        cmd += ["--cases", args.cases]
    print("\ncertifying the prepared tree:")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"\nthe prepared tree still holds an answer to a case; {dest} is not "
              "usable for a run and is left in place for inspection")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
