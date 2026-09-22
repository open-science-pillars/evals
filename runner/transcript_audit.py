"""Did the bundle-off arm read the knowledge, or only name it?

A bundle-off transcript that cites `knowledge/podaac/gotchas/x.md` has not
necessarily read it. The skills cite concept paths and the skills are not
ablated, by the registered design, so an off trial reads a skill, sees a path,
and repeats it at a file that is no longer on the machine. Naming is not
reading.

On 2026-09-22 the first shard to complete both arms was halted by a stopping
rule of mine that grepped for those paths. Nineteen of its twenty off
transcripts cited the case's own concept and not one reproduced a line of it,
so the rule fired on the wrong thing and a valid result was nearly discarded.
This is the right test: the frozen fingerprints, which are prose, against the
transcripts.

Reproduced prose in the off arm means the knowledge was reachable and the arm
was not off. Path citations without prose mean the opposite, and are worth
counting rather than alarming at.

  uv run runner/transcript_audit.py <shard out dir> --case native-grid-refusal
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from leak_check import digest, windows  # noqa: E402

PATH_MARK = "knowledge/"


def audit(outdir: Path, case: str, marks_file: Path):
    doc = json.loads(marks_file.read_text())
    salt, size = doc["salt"], doc.get("words", 14)
    marks = set()
    for ms in doc["cases"].get(case, {}).values():
        marks |= set(ms)
    if not marks:
        raise SystemExit(f"the frozen fingerprints hold no case called {case}")

    report = {}
    for arm in ("on", "off"):
        root = outdir / f"transcripts_{arm}"
        prose, paths, seen = [], 0, 0
        for f in sorted(root.rglob("trial*.txt")):
            seen += 1
            text = " ".join(f.read_text().split())
            if {digest(salt, w) for w in windows(text, size)} & marks:
                prose.append(f.name)
            paths += text.count(PATH_MARK)
        report[arm] = {"transcripts": seen, "reproduce_prose": prose,
                       "path_mentions": paths}
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("outdir")
    ap.add_argument("--case", required=True)
    ap.add_argument("--fingerprints",
                    default=str(Path(__file__).parent / "concept-fingerprints.json"))
    args = ap.parse_args()

    r = audit(Path(args.outdir), args.case, Path(args.fingerprints))
    for arm in ("on", "off"):
        a = r[arm]
        print(f"{arm} arm: {a['transcripts']} transcripts, "
              f"{len(a['reproduce_prose'])} reproduce concept prose, "
              f"{a['path_mentions']} path mentions")
        if a["reproduce_prose"]:
            print("   " + ", ".join(a["reproduce_prose"]))

    off = r["off"]
    if off["reproduce_prose"]:
        print("STOP: a bundle-off transcript reproduces the cited concept's prose, "
              "so the knowledge was reachable and this arm was not off.")
        return 1
    print(f"the bundle-off arm reproduced no concept prose in {off['transcripts']} "
          f"transcripts; its {off['path_mentions']} path mentions are names, not reads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
