"""Is the knowledge the cases cite reachable from where a trial runs?

Every failure of this experiment so far has been a copy of the knowledge that
nobody thought to look for. The first harness moved one installed tree and
called it bundle-OFF, and thirteen of the suite's fourteen citations lived in a
dependency it never touched. The scope was then derived from the manifest's
plugins and their declared dependencies, which moved three trees instead of
one, and the arm was still not off: the same knowledge sits in the workspace as
ordinary checked-out files, and recorded passing answers to these exact cases
sit beside it under results and fixtures directories.

Each of those fixes was a better guess about where copies live. This is not a
guess. It takes text out of the concepts the cases cite and looks for that text
on disk, so a copy is found because it is a copy and not because someone
predicted its location.

Two things are checked, and they are not the same thing:

  the bundle-off arm  no cited concept's text is readable anywhere, which is
                      what bundle-off means
  either arm          no recorded answer to a case in the run is readable,
                      because an answer to the case contaminates the rate in
                      both arms and not merely the difference between them

Whitespace is collapsed before matching. A concept wraps its prose at seventy
columns and a transcript quoting it does not, so a line-oriented search reports
a copy as absent; that mistake was made by hand on 2026-09-22 while reading
this very leak, and the normalisation is here so it is not made again.

A shard container must not hold the knowledge at all, or the check has nothing
to prove. So the fingerprints are frozen once, where the concepts are readable,
and carried as salted hashes rather than as text: a file of concept prose in the
run workspace would be the very leak this closes. The shard then checks against
hashes and never has a word of the knowledge on disk.

  uv run runner/leak_check.py <workspace> <manifest> --freeze concept-fingerprints.json
  uv run runner/leak_check.py <workspace> <manifest> --arm off --fingerprints f.json
  uv run runner/leak_check.py <workspace> <manifest> --arm on --cases a,b
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

# Directories that never hold a readable copy worth reporting: object stores,
# caches and virtual environments. Skipped for speed, not for safety.
# Package and build caches are skipped by name for speed: a first run spent two
# and a half minutes inside the uv build cache alone. Note that `.cache` is
# skipped and `cache` is not, which is deliberate: the installed plugin cache
# lives at ~/.claude/plugins/cache and is exactly what the bundle-off arm has to
# prove empty.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "dist", "build", ".tox",
             ".cache", ".cargo", ".rustup", ".npm", ".nvm", "site-packages",
             ".uv", ".local", "shell-snapshots", "projects", "statsig"}
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".sh", ".rst", ".html"}
MAX_BYTES = 4_000_000

# How much of a concept to fingerprint. Long enough that an unrelated file will
# not carry it by chance, short enough to survive a quotation that trims the
# ends.
FINGERPRINT_WORDS = 14


def normalise(text: str) -> str:
    """One line, single spaces, so wrapping cannot hide a copy."""
    return " ".join(text.split())


def fingerprints(concept: Path, per_file: int = 3) -> list[str]:
    """Distinctive runs of words from a concept's prose.

    Frontmatter and headings are skipped: a heading is short and repeats across
    concepts, and frontmatter keys appear in every file of the bundle.
    """
    lines = [ln for ln in concept.read_text().splitlines()
             if ln.strip() and not ln.startswith(("#", "-", "*", ">", "|", "---"))
             and ":" not in ln[:24]]
    body = normalise(" ".join(lines)).split()
    if len(body) < FINGERPRINT_WORDS:
        return []
    step = max(1, (len(body) - FINGERPRINT_WORDS) // max(1, per_file))
    out, seen = [], set()
    for i in range(0, len(body) - FINGERPRINT_WORDS + 1, step):
        f = " ".join(body[i:i + FINGERPRINT_WORDS])
        if f not in seen:
            seen.add(f)
            out.append(f)
        if len(out) == per_file:
            break
    return out


def digest(salt: str, text: str) -> str:
    """One fingerprint, as a hash. Short because a collision costs a false alarm."""
    return hashlib.blake2b((salt + text).encode(), digest_size=16).hexdigest()


def windows(text: str, size: int = FINGERPRINT_WORDS) -> set:
    """Every run of `size` words in a file, normalised, as raw strings."""
    words = text.split()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def freeze(ws: Path, manifest: Path, only, out: Path) -> int:
    """Write the cited concepts' fingerprints as hashes, once, where they exist."""
    by_case, allowed = cited_concepts(ws, manifest, only)
    salt = "osp-ablation-leak-check"
    # The fixtures a case may expose travel with the fingerprints. By the time
    # the check runs the case files are set aside, so it cannot read them to
    # learn what a case is allowed to have beside it.
    doc = {"salt": salt, "words": FINGERPRINT_WORDS, "cases": {},
           "fixtures": sorted(str(f.relative_to(ws)) for f in allowed)}
    total = 0
    for cid, concepts in by_case.items():
        doc["cases"][cid] = {}
        for concept in concepts:
            marks = [digest(salt, f) for f in fingerprints(concept)]
            # Keyed by path, not basename: geothermal-omission cites two files
            # both called ecco-heat-budget.md, one the capability's attested
            # computation and one the provider's recipe, and a basename key
            # dropped one of them silently.
            doc["cases"][cid][str(concept.relative_to(ws))] = marks
            total += len(marks)
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"froze {total} fingerprints for {len(by_case)} cases into {out}; "
          "no concept text is written, only hashes")
    return 0


def load_frozen(path: Path, ws: Path):
    """The frozen fingerprints and the fixtures a case may expose beside it."""
    doc = json.loads(path.read_text())
    cases = {cid: {name: set(marks) for name, marks in concepts.items()}
             for cid, concepts in doc["cases"].items()}
    allowed = {(ws / f).resolve() for f in doc.get("fixtures", [])}
    return doc["salt"], doc.get("words", FINGERPRINT_WORDS), cases, allowed


def cited_concepts(ws: Path, manifest: Path, only: set[str] | None):
    """Each case's concept files, and the fixture files the case may expose.

    Only the exact files a case declares are allowed beside it. Not the
    directory holding them: the native-grid fixture's own README states the
    correct behaviour for its case in one sentence, sitting next to the file
    the case has to expose, and a directory-level exemption would wave it
    through.
    """
    man = yaml.safe_load(manifest.read_text())
    found, allowed = {}, set()
    for entry in man["cases"]:
        if only and entry["id"] not in only:
            continue
        case = yaml.safe_load((ws / entry["case"]).read_text())
        paths = []
        for cited in case.get("concept_basis") or []:
            for root in sorted(p for p in ws.iterdir() if p.is_dir()):
                if (root / cited).is_file():
                    paths.append(root / cited)
        found[entry["id"]] = paths
        case_root = (ws / entry["case"]).parent.parent.parent
        for fx in case.get("fixtures") or []:
            for base in (case_root, ws):
                if (base / fx).is_file():
                    allowed.add((base / fx).resolve())
    return found, allowed


def walk(roots: list[Path]):
    """Every readable text file under the roots, once each."""
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if not path.is_file() or path.is_symlink():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                real = path.resolve()
                if real in seen:
                    continue
                seen.add(real)
                yield path, normalise(path.read_text(errors="ignore"))
            except OSError:
                continue


def scan(roots: list[Path], by_case: dict[str, list[Path]], case_ids: set[str],
         allowed: set[Path]):
    """Files holding a cited concept's text, and files holding a case's answer."""
    marks = []
    for cid, concepts in by_case.items():
        for concept in concepts:
            for f in fingerprints(concept):
                marks.append((cid, concept, f))
    concept_hits, answer_hits = [], []
    for path, text in walk(roots):
        if path.resolve() in allowed:
            continue
        for cid, concept, f in marks:
            if f in text:
                concept_hits.append((cid, concept, path))
                break
        parts = {p.lower() for p in path.parts}
        if parts & {"transcripts", "results", "fixtures"}:
            for cid in case_ids:
                if cid in path.stem or cid in text[:4000]:
                    answer_hits.append((cid, path))
                    break
    return concept_hits, answer_hits


def scan_frozen(roots, salt, size, frozen, case_ids, allowed):
    """The same search, against hashes, with no concept text on this machine."""
    concept_hits, answer_hits = [], []
    for path, text in walk(roots):
        if path.resolve() in allowed:
            continue
        marks = {digest(salt, w) for w in windows(text, size)}
        for cid, concepts in frozen.items():
            hit = next((name for name, wanted in concepts.items() if wanted & marks), None)
            if hit:
                concept_hits.append((cid, hit, path))
                break
        parts = {p.lower() for p in path.parts}
        if parts & {"transcripts", "results", "fixtures"}:
            for cid in case_ids:
                if cid in path.stem or cid in text[:4000]:
                    answer_hits.append((cid, path))
                    break
    return concept_hits, answer_hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace")
    ap.add_argument("manifest")
    ap.add_argument("--arm", choices=["on", "off"])
    ap.add_argument("--freeze", help="write the fingerprints as hashes to this file "
                                     "and do nothing else")
    ap.add_argument("--fingerprints", help="check against frozen hashes rather than "
                                           "against concepts read from the workspace")
    ap.add_argument("--cases", default="", help="comma-separated subset")
    ap.add_argument("--root", action="append", default=[],
                    help="extra directory to search, repeatable (default: the "
                         "workspace, the home directory and the plugin cache)")
    args = ap.parse_args()

    ws, manifest = Path(args.workspace).resolve(), Path(args.manifest).resolve()
    only = {c.strip() for c in args.cases.split(",") if c.strip()} or None
    if args.freeze:
        return freeze(ws, manifest, only, Path(args.freeze))
    if not args.arm:
        print("ERROR: --arm is required unless --freeze is given")
        return 2

    roots = [Path(r).resolve() for r in args.root] or [ws, Path.home()]

    if args.fingerprints:
        # Frozen mode reads no case and no concept, which is the point: it runs
        # where neither is on the machine.
        salt, size, frozen, allowed = load_frozen(Path(args.fingerprints), ws)
        if only:
            frozen = {c: v for c, v in frozen.items() if c in only}
        case_ids = set(frozen)
        concept_hits, answer_hits = scan_frozen(roots, salt, size, frozen,
                                                case_ids, allowed)
        named = "the frozen fingerprints"
    else:
        by_case, allowed = cited_concepts(ws, manifest, only)
        case_ids = set(by_case)
        concept_hits, answer_hits = scan(roots, by_case, case_ids, allowed)
        named = "the concepts read from the workspace"

    problems = []
    if args.arm == "off" and concept_hits:
        problems.append("the bundle-off arm can still read the knowledge it is "
                        "supposed to have removed:")
        for cid, concept, path in sorted(set(concept_hits), key=lambda h: str(h[2])):
            name = concept if isinstance(concept, str) else concept.name
            problems.append(f"  {cid}: {name} is readable at {path}")
    if answer_hits:
        problems.append("a recorded answer to a case in this run is readable, which "
                        "contaminates both arms and not only the difference:")
        for cid, path in sorted(set(answer_hits), key=lambda h: str(h[1])):
            problems.append(f"  {cid}: {path}")

    if problems:
        print("ERROR: " + "\n".join(problems))
        return 1

    print(f"checked against {named}: no copy of a cited concept and no recorded "
          f"answer to the {len(case_ids)} cases is readable under "
          f"{', '.join(str(r) for r in roots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
