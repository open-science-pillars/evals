"""The cross-runtime record every results file carries.

A result is comparable across runtimes only when it says what ran: which
capability at which version and release lock, on which runtime and
projection, with which model, on which date, and how many trials. The
scientific cases and the graders do not change between runtimes (the
capability contract is the same); this record is the dimension that
does. The fields follow the multi-runtime packaging decision (ADR B in
the marketplace repository).

    capability            the package under test, from .osp/package.yaml
    capability_version    its version
    release_lock          sha256 of .osp/release-lock.json as a value, so
                          two runs can be shown to have exercised the same
                          governed release; None when the tree has no lock
    release_lock_current  whether the lock still matches the tree (build-kit's
                          osp.py lock --check, when build-kit is in the
                          workspace); a result on a moved tree says so
    runtime               name, projection (claude or agent-plugins) and
                          the runtime's own version string
    model                 the model the trials ran on
    judge_model           the model the rubric judge ran on (the judge is a
                          Claude Code call whatever the runtime, so grading
                          is held constant across runtimes)
    suite                 the manifest name
    trials                trials requested per case
    date                  the UTC date of the run
"""
import hashlib
import json
import subprocess
import datetime as dt
from pathlib import Path

import yaml

RECORD_VERSION = 2

# Which projection each runtime installs (the runtime distribution note in
# the marketplace repository): the Claude family installs the Claude
# package files; every other client consumes the Agent Plugins package.
RUNTIMES = {
    "claude-code": "claude",
    "claude-cowork": "claude",
    "claude-science": "claude",
    "openai-codex": "agent-plugins",
    "gemini-cli": "agent-plugins",
    "goose": "agent-plugins",
}


def value_digest(value) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def lock_current(ws: Path, plugin: str):
    """True, False, or None when build-kit is not in the workspace."""
    tool = ws / "build-kit" / "scripts" / "osp.py"
    if not tool.is_file():
        return None
    try:
        r = subprocess.run(["uv", "run", "--quiet", str(tool), "lock", str(ws / plugin), "--check"],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.returncode == 0


def capability_record(ws: Path, plugin: str, check_lock: bool = True) -> dict:
    """What the capability under test is: name, version, release lock."""
    root = ws / plugin
    version = None
    pkg = root / ".osp" / "package.yaml"
    if pkg.is_file():
        try:
            version = str(yaml.safe_load(pkg.read_text())["package"]["version"])
        except (KeyError, TypeError, yaml.YAMLError):
            version = None
    if version is None:
        manifest = root / ".claude-plugin" / "plugin.json"
        if manifest.is_file():
            try:
                version = json.loads(manifest.read_text()).get("version")
            except json.JSONDecodeError:
                version = None
    lock_path = root / ".osp" / "release-lock.json"
    lock = None
    if lock_path.is_file():
        try:
            lock = json.loads(lock_path.read_text())
        except json.JSONDecodeError:
            lock = None
    return {
        "name": plugin,
        "version": version,
        "release_lock": value_digest(lock) if lock is not None else None,
        "release_lock_version": (lock or {}).get("version"),
        "release_lock_current": lock_current(ws, plugin) if (lock is not None and check_lock) else None,
    }


def runtime_version(runtime: str):
    """The runtime's own version string, asked of its CLI when there is one."""
    command = {"claude-code": ["claude", "--version"], "openai-codex": ["codex", "--version"],
               "gemini-cli": ["gemini", "--version"], "goose": ["goose", "--version"]}.get(runtime)
    if not command:
        return None
    try:
        r = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (r.stdout or r.stderr).strip().splitlines()
    return text[0] if text else None


def runtime_record(runtime: str, version=None) -> dict:
    if runtime not in RUNTIMES:
        raise ValueError(f"unknown runtime {runtime!r}; one of {', '.join(RUNTIMES)}")
    return {"name": runtime, "projection": RUNTIMES[runtime],
            "version": version if version is not None else runtime_version(runtime)}


def build_record(ws: Path, plugins, runtime: str, runtime_ver, model: str, judge_model,
                 suite: str, trials: int, check_lock: bool = True) -> dict:
    return {
        "record_version": RECORD_VERSION,
        "suite": suite,
        "runtime": runtime_record(runtime, runtime_ver),
        "model": model,
        "judge_model": judge_model,
        "trials": trials,
        "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "capabilities": {p: capability_record(ws, p, check_lock) for p in sorted(set(plugins))},
    }
