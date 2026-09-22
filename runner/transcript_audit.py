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
from leak_check import cited_concepts, digest, fingerprints, normalise, windows  # noqa: E402

PATH_MARK = "knowledge/"


def full_marks(ws: Path, manifest: Path, case: str):
    """Every window of the case's concepts, minus the windows of what stays.

    The frozen fingerprints take three windows per concept. That is ample for
    the gate, which asks whether a copy of a whole file is readable and finds
    one by any of its windows, and thin here, where the question is whether a
    transcript reproduced prose: a trial can quote a paragraph and miss three
    windows out of hundreds. Where the concepts are readable, which is where
    an audit runs and not where the gate runs, every window can be used.

    Windows that also occur in material the design leaves in place are
    dropped. The skills are not ablated and they quote the knowledge, so a
    trial repeating a skill would otherwise be recorded as reading a concept
    that was not on the machine.
    """
    by_case, _ = cited_concepts(ws, manifest, {case})
    concepts = by_case.get(case) or []
    if not concepts:
        raise SystemExit(f"the manifest gives no concepts for a case called {case}")

    # Everything in the workspace that is not knowledge and not this run's own
    # output: the skills above all, which cite and paraphrase the concepts and
    # are deliberately left in place. A window shared with them says nothing
    # about whether a concept was readable. The skills of every bundle count,
    # not only the bundle the concept lives in, since a case's concept and the
    # skill that quotes it are routinely in different bundles.
    skip = {".git", "knowledge", "transcripts_on", "transcripts_off",
            "scoreboard", "results", "node_modules", "__pycache__"}
    keep = set()
    for md in ws.rglob("*.md"):
        if skip & set(md.parts):
            continue
        keep |= set(_body_windows(md))

    marks = set()
    for concept in concepts:
        marks |= set(_body_windows(concept))
    return marks - keep, len(concepts)


def _body_windows(path: Path):
    """The windows of a file's prose, filtered the way the freeze filters."""
    lines = [ln for ln in path.read_text(errors="ignore").splitlines()
             if ln.strip() and not ln.startswith(("#", "-", "*", ">", "|", "---"))
             and ":" not in ln[:24]]
    return windows(normalise(" ".join(lines)))


def audit(outdir: Path, case: str, marks_file: Path, full=None):
    """Which transcripts reproduce the case's concept prose, and which name it.

    `full` is a set of raw windows, used when the concepts are readable.
    Otherwise the frozen hashes are used, which is the only option where they
    are not.
    """
    if full is None:
        doc = json.loads(marks_file.read_text())
        salt, size = doc["salt"], doc.get("words", 14)
        marks = set()
        for ms in doc["cases"].get(case, {}).values():
            marks |= set(ms)
        if not marks:
            raise SystemExit(f"the frozen fingerprints hold no case called {case}")
    else:
        size = 14

    report = {}
    for arm in ("on", "off"):
        root = outdir / f"transcripts_{arm}"
        prose, paths, seen = [], 0, 0
        for f in sorted(root.rglob("trial*.txt")):
            seen += 1
            text = " ".join(f.read_text(errors="ignore").split())
            seen_windows = windows(text, size)
            hit = (seen_windows & full if full is not None
                   else {digest(salt, w) for w in seen_windows} & marks)
            if hit:
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
    ap.add_argument("--workspace", help="audit against every window of the cited "
                    "concepts, read from this workspace, rather than the three "
                    "frozen per concept. Use it wherever the concepts are "
                    "readable, which is anywhere an audit runs.")
    ap.add_argument("--manifest", help="the manifest naming the case's concepts; "
                    "defaults to manifests/ablation.yaml under the workspace")
    args = ap.parse_args()

    full = None
    if args.workspace:
        ws = Path(args.workspace).resolve()
        man = Path(args.manifest) if args.manifest else ws / "evals/manifests/ablation.yaml"
        full, n = full_marks(ws, man, args.case)
        print(f"auditing against {len(full)} windows across {n} concepts read at "
              f"{ws}, not the three frozen per concept")

    r = audit(Path(args.outdir), args.case, Path(args.fingerprints), full)
    for arm in ("on", "off"):
        a = r[arm]
        print(f"{arm} arm: {a['transcripts']} transcripts, "
              f"{len(a['reproduce_prose'])} reproduce concept prose, "
              f"{a['path_mentions']} path mentions")
        if a["reproduce_prose"]:
            print("   " + ", ".join(a["reproduce_prose"]))

    # An arm with no transcripts is not a clean arm, it is an unexamined one.
    # Read literally, the sentence below would report zero reproductions over
    # zero files and call that evidence the arm was off. A shard that pushed
    # its results without its transcripts produced exactly that.
    missing = [arm for arm in ("on", "off") if r[arm]["transcripts"] == 0]
    if missing:
        print(f"STOP: no transcripts for the {' and '.join(missing)} arm, so "
              "there is nothing to audit. This is not a clean result; it is an "
              "absent one. Look for the transcripts before reading anything "
              "into the arm's rate.")
        return 2

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
