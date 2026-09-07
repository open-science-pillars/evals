"""The two lists a manifest's allowed_tools has to become.

`--tools` names tools; `Bash(uv run*)` is a permission rule on one of
them, and its argument can hold spaces and commas of its own. Kept in
its own module so the selftest can assert it without the runner's
dependencies: the selftest runs on a bare interpreter in CI.
"""
import re


def tool_names(allowed_tools: str):
    """The bare tool names in a manifest's allowed_tools string."""
    # A rule's argument can hold spaces and commas of its own
    # (`Bash(uv run*)`), so the arguments come off before anything is
    # split: splitting first turns one tool into two nonexistent ones.
    bare = re.sub(r"\([^)]*\)", "", allowed_tools)
    names = []
    for part in re.split(r"[,\s]+", bare.strip()):
        if not part:
            continue
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


