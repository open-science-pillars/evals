"""Merge the per-shard results of one ablation arm into one arm result.

The powered ablation is 7 cases by 2 arms at 20 trials, and ablate.sh moves
the installed knowledge tree to make the bundle-off arm. That mutation is on
the shared plugin cache, so two shards must never share a machine: on
2026-09-21 two concurrent qualification runs sharing one cache disagreed with
each other and both were discarded. Shards therefore run one per container,
and this is what brings their results back together.

A shard is one case's pair of arms, run whole in one container, so the
comparison the experiment turns on is never split across machines. This tool
merges the same arm across shards and refuses to merge shards that are not
comparable: a different model, a different arm, a different package version or
release lock, or a different runtime. Summing those would produce a headline
number describing no run that happened.

Per case it sums passes, valid trials and errors, then recomputes the rate and
the Wilson interval from the totals rather than averaging the shards' rates,
which would weight a shard that errored most as heavily as a complete one.

  uv run runner/merge_shards.py shard*/results_on.json --out results_on.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from stats import verdict  # noqa: E402

# What every shard of one arm must agree on before its numbers may be added to
# another's. Each is a reason the trials were not the same experiment.
MUST_MATCH = ("manifest", "model", "bundle", "judge_model", "suite", "record_version")


def capability_fingerprint(doc):
    """The packages a shard ran against, as a comparable value."""
    return {
        name: (cap.get("version"), cap.get("release_lock"))
        for name, cap in sorted((doc.get("capabilities") or {}).items())
    }


def runtime_fingerprint(doc):
    rt = doc.get("runtime") or {}
    return (rt.get("name"), rt.get("projection"))


def incompatible(first, first_path, other, other_path):
    """Every reason these two shards may not be merged, as readable lines."""
    problems = []
    for key in MUST_MATCH:
        if first.get(key) != other.get(key):
            problems.append(f"{key}: {first_path} has {first.get(key)!r}, "
                            f"{other_path} has {other.get(key)!r}")
    if capability_fingerprint(first) != capability_fingerprint(other):
        problems.append(f"the packages differ: {first_path} ran "
                        f"{capability_fingerprint(first)}, {other_path} ran "
                        f"{capability_fingerprint(other)}")
    if runtime_fingerprint(first) != runtime_fingerprint(other):
        problems.append(f"the runtime differs: {first_path} ran {runtime_fingerprint(first)}, "
                        f"{other_path} ran {runtime_fingerprint(other)}")
    return problems


def merge(docs):
    """One arm result from several shards of that arm."""
    first, first_path = docs[0]
    problems = []
    for other, other_path in docs[1:]:
        problems += incompatible(first, first_path, other, other_path)
    if problems:
        raise SystemExit("these shards are not the same experiment and are not merged:\n  "
                         + "\n  ".join(problems))

    totals = {}
    order = []
    for doc, path in docs:
        for case in doc.get("cases", []):
            cid = case["id"]
            if cid not in totals:
                totals[cid] = {"passes": 0, "trials": 0, "errors": 0,
                               "threshold": case.get("threshold", 0.8),
                               "type": case.get("type"), "shards": []}
                order.append(cid)
            acc = totals[cid]
            acc["passes"] += case.get("passes", 0)
            acc["trials"] += case.get("trials", 0)
            acc["errors"] += case.get("errors", 0)
            acc["shards"].append(path)

    cases = []
    for cid in order:
        acc = totals[cid]
        row = verdict(acc["passes"], acc["trials"], acc["threshold"])
        row.update(id=cid, type=acc["type"], errors=acc["errors"], shards=acc["shards"])
        cases.append(row)

    out = dict(first)
    out["cases"] = cases
    out["trials"] = sum(doc.get("trials", 0) for doc, _ in docs)
    out["merged_from"] = [path for _, path in docs]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("shards", nargs="+", help="one arm's per-shard results files")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    docs = [(json.loads(Path(p).read_text()), p) for p in args.shards]
    merged = merge(docs)
    Path(args.out).write_text(json.dumps(merged, indent=2) + "\n")

    cases = merged["cases"]
    measured = sum(c["trials"] for c in cases)
    errored = sum(c["errors"] for c in cases)
    print(f"merged {len(docs)} shards of the {merged['bundle']} arm on {merged['model']}: "
          f"{len(cases)} cases, {measured} valid trials, {errored} errored")
    for c in cases:
        print(f"  {c['id']}: {c['passes']}/{c['trials']} (rate {c['rate']}) "
              f"CI {c['ci95']} from {len(c['shards'])} shard(s)")
    empty = [c["id"] for c in cases if not c["trials"]]
    if empty:
        print("a case measured nothing, so this arm is an outage and not a result: "
              + ", ".join(empty))
        return 1
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
