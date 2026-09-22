"""The refs a run must check out: the ones the marketplace actually serves.

A shard installs the capability from the marketplace, which pins each plugin to
a release tag, and the trials read that installed tree. The workspace checkout
is a different thing: the runner reads the version and the release lock from it
and records them as the capability under test. Clone the plugins at main and
those two trees are not the same tree, so the record describes something the
trials never read.

That went unnoticed until 2026-09-22, when a shard refused to start because
core's lock was stale on main: an eval case had been edited after the release,
which is ordinary, and the checkout had drifted from the tag the install came
from, which is the part that matters. At the tag the lock is current, because a
release is what a lock digests.

So the refs come from the catalog rather than from a list someone maintains
alongside it. The harness repositories are not plugins and are not listed here;
they stay on their default branch, because they are the instrument and not the
thing being measured.

  uv run runner/released_refs.py <marketplace checkout>
  uv run runner/released_refs.py <marketplace checkout> --only core,ocean-science
"""
import argparse
import json
from pathlib import Path


def served(marketplace: Path) -> list[tuple[str, str, str]]:
    """Each plugin the catalog serves, as (name, repository, ref)."""
    catalog = json.loads((marketplace / ".claude-plugin" / "marketplace.json").read_text())
    out = []
    for entry in catalog.get("plugins", []):
        source = entry.get("source") or {}
        repo, ref = source.get("repo"), source.get("ref")
        if not repo or not ref:
            raise SystemExit(f"{entry.get('name')} has no pinned ref in the catalog; "
                             "a run cannot check out what the install serves")
        out.append((entry["name"], repo, ref))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("marketplace")
    ap.add_argument("--only", default="", help="comma-separated plugin names")
    ap.add_argument("--clone-into", default="",
                    help="print a git clone command per plugin into this directory")
    args = ap.parse_args()

    only = {n.strip() for n in args.only.split(",") if n.strip()}
    rows = [r for r in served(Path(args.marketplace)) if not only or r[0] in only]
    missing = only - {r[0] for r in rows}
    if missing:
        raise SystemExit(f"the catalog serves no plugin called {', '.join(sorted(missing))}")

    for name, repo, ref in rows:
        if args.clone_into:
            print(f"git clone --depth 1 --branch {ref} "
                  f"https://github.com/{repo} {args.clone_into}/{name}")
        else:
            print(f"{name}\t{repo}\t{ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
