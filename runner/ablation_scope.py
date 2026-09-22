"""Which installed knowledge trees the bundle-OFF arm must move aside.

Until 2026-09-21 the ablation moved one tree, the capability's own, and called
that bundle-OFF. It was not. Every case in the ablation manifest cites its
ground truth by `concept_basis`, and thirteen of the suite's fourteen citations
name concepts in nasa-daac-knowledge, a separate plugin with a separate cache
the arm never touched. The bundle-OFF transcripts prove it: one of them opens
"I read the bundle concepts before touching data" and cites both files by path,
in the arm where the knowledge is supposed to be gone.

So every ON minus OFF number the ablation has produced, including the pilot
null of 2026-07-05 recorded in the pre-registration, compared an arm holding
the cited knowledge against an arm holding the cited knowledge.

The scope is now derived rather than assumed: the plugins the manifest's cases
name, plus every dependency those plugins declare, because an installed
capability brings its dependencies and a reader consulting knowledge reaches
all of them. The cases are checked against that scope, and a case whose
concept_basis falls outside it stops the run rather than quietly measuring
nothing.

The installed cache is not the only copy. The workspace carries the same trees
as ordinary checked-out files, and a trial reads those just as readily, so
--workspace-trees names them too. They move aside for both arms rather than for
the off arm alone: with them present the bundle-on arm is not reading the
installed bundle either, and what the experiment manipulates has to be the only
copy there is.

  uv run runner/ablation_scope.py <workspace> <manifest>   # installed cache trees
  uv run runner/ablation_scope.py <workspace> <manifest> --workspace-trees
  uv run runner/ablation_scope.py <workspace> <manifest> --plugins
  uv run runner/ablation_scope.py <workspace> <manifest> --check
"""
import sys
from pathlib import Path

import yaml


def declared_dependencies(ws: Path, plugin: str) -> list[str]:
    """The plugin names a capability declares, capabilities and knowledge alike."""
    pkg = ws / plugin / ".osp" / "package.yaml"
    if not pkg.is_file():
        return []
    data = yaml.safe_load(pkg.read_text()) or {}
    deps = data.get("dependencies") or {}
    names = []
    for group in ("capabilities", "knowledge"):
        for entry in deps.get(group) or []:
            names.append(entry["name"] if isinstance(entry, dict) else str(entry))
    return names


def plugins_in_scope(ws: Path, manifest: Path) -> list[str]:
    """Every plugin whose knowledge an installed reader of this suite reaches."""
    man = yaml.safe_load(manifest.read_text())
    seen, queue = [], [c["plugin"] for c in man["cases"]]
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.append(name)
        queue.extend(declared_dependencies(ws, name))
    return seen


def installed_trees(plugins: list[str]) -> dict[str, list[Path]]:
    """The installed knowledge tree of each plugin, found not pinned."""
    cache = Path.home() / ".claude" / "plugins" / "cache"
    return {p: sorted(cache.glob(f"*/{p}/*/knowledge")) for p in plugins}


def unreachable_citations(ws: Path, manifest: Path, plugins: list[str]) -> list[str]:
    """Cases whose ground truth lives outside the scope, which the arm cannot remove."""
    man = yaml.safe_load(manifest.read_text())
    problems = []
    for entry in man["cases"]:
        case = yaml.safe_load((ws / entry["case"]).read_text())
        for cited in case.get("concept_basis") or []:
            if not any((ws / p / cited).is_file() for p in plugins):
                problems.append(f"{entry['id']}: {cited} is in no plugin this arm removes")
    return problems


def main() -> int:
    ws, manifest = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    check = "--check" in sys.argv[3:]
    plugins = plugins_in_scope(ws, manifest)
    trees = installed_trees(plugins)

    if check:
        print(f"plugins in scope: {', '.join(plugins)}")
        for name, found in trees.items():
            concepts = sum(len(list(t.rglob('*.md'))) for t in found)
            where = ", ".join(str(t) for t in found) or "NOT INSTALLED"
            print(f"  {name}: {concepts} concepts  {where}")
            if len(found) > 1:
                print(f"    ERROR: {name} is installed from more than one marketplace; "
                      "the arm would not know which tree the trials read")
                return 1
        missing = unreachable_citations(ws, manifest, plugins)
        if missing:
            print("ERROR: a case's ground truth is outside the arm's reach, so bundle-OFF "
                  "would not be off for it:")
            for m in missing:
                print("  " + m)
            return 1
        if not any(trees.values()):
            print("ERROR: none of the plugins in scope has an installed knowledge tree")
            return 1
        print("every cited concept is inside a tree this arm removes")
        return 0

    if "--plugins" in sys.argv[3:]:
        for name in plugins:
            print(name)
        return 0

    if "--workspace-trees" in sys.argv[3:]:
        for name in plugins:
            tree = ws / name / "knowledge"
            if tree.is_dir():
                print(tree)
        return 0

    for found in trees.values():
        for tree in found:
            print(tree)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
