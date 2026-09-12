# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Deterministic self-test of the eval runner's grading and aggregation.

Feeds known good/bad transcript snippets to the programmatic graders and asserts
correct classification, then checks the binomial verdict. This exercises the
runner logic without slow, flaky live agentic trials (the full N=20 live sweep
is the CI job). Run: `uv run runner/selftest.py` (exit 0 = green).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import run_programmatic  # noqa: E402
from toolspec import tool_names  # noqa: E402
from judge import parse_judgement  # noqa: E402
from stats import verdict  # noqa: E402
from record import RUNTIMES, build_record, capability_record, runtime_record, value_digest  # noqa: E402
from drivers import command_for  # noqa: E402
from scoreboard import comparison, label, render  # noqa: E402

# (checker_id, good transcript, bad transcript)
CASES = [
    ("transcript_refuses_and_offers_native_grid",
     "That regridded 0.5-degree product cannot close a budget; I refuse and offer the native-grid llc90 path with snapshots.",
     "Sure, I'll compute the heat budget from the 0.5-degree regridded field."),
    ("plan_includes_geothermal_term_and_ancillary_source",
     "Terms: tendency, advection, diffusion, forcing, and the geothermal flux from the ancillary geothermalFlux.bin (not a PO.DAAC collection).",
     "Terms: tendency, advection, diffusion, and surface forcing. That covers a full-depth budget."),
    ("transcript_uses_atlantic_basin_for_rapid",
     "For the RAPID comparison I use the Atlantic (atlExt) section, 0.666 PW for 2010, not the full circle.",
     "The 26.5N transport is 1.098 PW, which I compare directly against the RAPID mean."),
    ("transcript_applies_height_cor_xover",
     "I add height_cor_xover (gated by height_cor_xover_qual) to ssha_karin before computing statistics.",
     "I compute mean and std of ssha_karin over the good-flagged pixels."),
    ("transcript_names_single_release",
     "I'll use a single release, V4R4B, throughout, and not mix it with V4R4 or the correction enters the trend.",
     "I'll pull whatever SSH collections cover 1992-2017 and concatenate them."),
    ("transcript_detects_sentinels_before_stats",
     "First a fill-value audit: the field has -9999 sentinels; I mask them before any statistic.",
     "The global-mean trend over the raw field is -412 K/decade."),
    ("computation_uses_area_weights",
     "I take the cos(lat) area-weighted mean over the grid.",
     "I take df.mean() over all grid cells."),
    ("headline_carries_uncertainty_or_waiver",
     "The trend is 0.20 +/- 0.03 K/decade (95% CI, block bootstrap).",
     "The trend is 0.20 K/decade."),
    ("transcript_surfaces_leakage_caveat",
     "Near the coast, GRACE mascon coastal leakage bleeds land signal in; I apply a CRI buffer.",
     "I take the mascon value at the coastal grid point directly."),
    ("transcript_surfaces_orbit_phase_split",
     "The cal/val 1-day fast-sampling phase and the 21-day science orbit are separate records; I keep them apart.",
     "I concatenate all cycles into one continuous SSH record."),
    ("nothing_downloaded_gate_presented",
     "That request is ~690 GB, far over the 2 GB gate; I estimate the size and stop for confirmation before download.",
     "Downloading all node granules for every continent now."),
    ("trend_test_is_autocorrelation_aware",
     "Monthly series are autocorrelated; I use a Hamed-Rao modified Mann-Kendall with effective sample size.",
     "I fit an ordinary least squares line and report its p-value."),
]


def main():
    fails = []
    for cid, good, bad in CASES:
        g = run_programmatic(cid, good)
        b = run_programmatic(cid, bad)
        if g is not True:
            fails.append(f"{cid}: good transcript classified {g}, expected True")
        if b is not False:
            fails.append(f"{cid}: bad transcript classified {b}, expected False")
    # The judge's reply, in every shape it comes back in. A verdict that
    # was stated is a verdict even when the envelope is damaged; only a
    # reply that states no grade is an error, because an outage read as a
    # FAIL and a truncated FAIL read as an outage are both wrong rates.
    JUDGE = [
        ('{"grade": "PASS", "reason": "names the seam"}', "PASS", False),
        ('here you go\n{"grade": "FAIL", "reason": "no run declared"}', "FAIL", False),
        ('{"grade": "FAIL", "reason": "refused correctly but then delivered a closure by another route \u2014 P',
         "FAIL", True),
        ('{"grade": "PASS", "reason": "the masked fraction is stated and the volume is over the measured',
         "PASS", True),
        ("You've reached your Fable 5 limit. Switch to another model, or manage usage credits.", "ERROR", False),
        ("", "ERROR", False),
        ("I read the transcript and thought about it at some length, but here is only prose.", "ERROR", False),
        ('{"grade": "PASS"} and also {"grade": "FAIL"}', "ERROR", False),
    ]
    for reply, want, salvaged in JUDGE:
        got = parse_judgement(reply)
        if got["grade"] != want:
            fails.append(f"judge reply {reply[:40]!r}: graded {got['grade']}, expected {want}")
        if bool(got.get("salvaged")) != salvaged:
            fails.append(f"judge reply {reply[:40]!r}: salvaged={got.get('salvaged')}, expected {salvaged}")

    # The tool set handed to --tools is the bare names; the permission
    # rules keep their arguments and go to --allowedTools. Getting this
    # wrong silently disarms the isolation, so it is asserted here.
    TOOLS = [
        ("Read,Skill", ["Read", "Skill"]),
        ("Read,Skill,Bash(uv run*),Write", ["Read", "Skill", "Bash", "Write"]),
        ("Read, Skill , Bash(uv run*)", ["Read", "Skill", "Bash"]),
        ("Bash(uv run*),Bash(git status)", ["Bash"]),
        ("", []),
    ]
    for spec, want in TOOLS:
        got = tool_names(spec)
        if got != want:
            fails.append(f"tool_names({spec!r}) = {got}, expected {want}")

    # Aggregation: 5/5 seed reproduces PASS at 0.8; 3/5 does not.
    assert verdict(5, 5, 0.8)["pass"] is True
    assert verdict(3, 5, 0.8)["pass"] is False
    assert verdict(18, 20, 0.8)["pass"] is True   # point rate 0.9 >= 0.8

    # The cross-runtime record. A scratch workspace with one capability
    # carrying a package file and a release lock, and no build-kit, so the
    # lock is recorded and its currency is unchecked rather than guessed.
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        (ws / "ocean-science" / ".osp").mkdir(parents=True)
        (ws / "ocean-science" / ".osp" / "package.yaml").write_text(
            "schema_version: 1\npackage: {name: ocean-science, version: 0.8.2, type: capability}\n"
            "content: {}\ndependencies: {capabilities: [], knowledge: []}\n")
        lock = {"schema_version": 1, "package": "ocean-science", "version": "0.8.2",
                "skills_digest": "sha256:abc"}
        (ws / "ocean-science" / ".osp" / "release-lock.json").write_text(json.dumps(lock))
        cap = capability_record(ws, "ocean-science")
        if cap["version"] != "0.8.2" or cap["release_lock"] != value_digest(lock) \
                or cap["release_lock_version"] != "0.8.2" or cap["release_lock_current"] is not None:
            fails.append(f"capability record wrong: {cap}")
        (ws / "core" / ".claude-plugin").mkdir(parents=True)
        (ws / "core" / ".claude-plugin" / "plugin.json").write_text('{"name": "core", "version": "0.5.0"}')
        bare = capability_record(ws, "core")
        if bare["version"] != "0.5.0" or bare["release_lock"] is not None:
            fails.append(f"manifest-only capability record wrong: {bare}")
        rec = build_record(ws, ["ocean-science", "core", "core"], "openai-codex", "codex 0.50.0",
                           "gpt-5", "claude-fable-5", "ocean-science", 20)
        if rec["record_version"] != 2 or rec["runtime"] != {"name": "openai-codex", "projection": "agent-plugins", "version": "codex 0.50.0"} \
                or sorted(rec["capabilities"]) != ["core", "ocean-science"] or rec["judge_model"] != "claude-fable-5" \
                or len(rec["date"]) != 10 or rec["suite"] != "ocean-science" or rec["trials"] != 20:
            fails.append(f"record wrong: {rec}")
    for rt, proj in RUNTIMES.items():
        if runtime_record(rt, "x")["projection"] != proj:
            fails.append(f"runtime {rt} projection wrong")
    try:
        runtime_record("emacs", "x")
        fails.append("unknown runtime accepted")
    except ValueError:
        pass
    # Drivers: Claude Code keeps its exact command; Codex takes the prompt on
    # stdin; a runtime with no headless command is refused, not guessed.
    argv, stdin, _ = command_for("claude-code", "hi", "Read,Skill", 25, "claude-fable-5", ["--plugin-dir", "/x"])
    if argv != ["claude", "-p", "hi", "--model", "claude-fable-5", "--allowedTools", "Read,Skill",
                "--max-turns", "25", "--plugin-dir", "/x"] or stdin is not None:
        fails.append(f"claude-code command wrong: {argv} {stdin}")
    argv, stdin, notes = command_for("openai-codex", "hi", "Read", 25, "gpt-5")
    if argv[:2] != ["codex", "exec"] or stdin != "hi" or "--model" not in argv or not notes:
        fails.append(f"codex command wrong: {argv} {stdin}")
    try:
        command_for("claude-cowork", "hi", "Read", 25, "m")
        fails.append("cowork driver should be refused")
    except ValueError:
        pass
    # Scoreboard: an old results file without the record still renders; two
    # files on different runtimes render as a runtime comparison, the same
    # runtime with bundle off as the ablation.
    old = {"manifest": "m", "model": "claude-fable-5", "bundle": "on", "trials": 1,
           "cases": [{"id": "a", "type": "t", "rate": 1.0, "ci95": [0.2, 1.0], "pass": True}]}
    if "runtime" in label(old) or "<td>a</td>" not in render(old):
        fails.append("old results file does not render")
    a = dict(old, runtime={"name": "claude-code", "projection": "claude", "version": "2.1"},
             capabilities={"ocean-science": {"version": "0.8.2", "release_lock": "sha256:abcdef0123456789", "release_lock_current": True}},
             date="2026-09-12")
    b = dict(a, runtime={"name": "openai-codex", "projection": "agent-plugins", "version": "0.5"},
             cases=[{"id": "a", "type": "t", "rate": 0.5, "ci95": [0.1, 0.9], "pass": False}])
    if comparison(a, b)[0] != "runtime" or comparison(a, dict(a, bundle="off"))[0] != "bundle":
        fails.append("comparison kind wrong")
    html = render(a, b)
    for needle in ("claude-code against openai-codex", "openai-codex: rate", "ocean-science 0.8.2", "+0.5", "runtime's, not the science's"):
        if needle not in html:
            fails.append(f"runtime comparison lacks {needle!r}")
    if "bundle off: rate" not in render(a, dict(a, bundle="off")):
        fails.append("ablation columns lost")

    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print(f"selftest: {len(CASES)} graders classify good/bad transcripts correctly; "
          f"{len(JUDGE)} judge replies (whole, truncated, absent, ambiguous) read correctly; "
          f"{len(TOOLS)} tool specs split into names and rules correctly; "
          "verdict aggregation correct; the cross-runtime record, the drivers and the "
          "scoreboard's runtime comparison behave")
    print("evals runner selftest: PASSED")


if __name__ == "__main__":
    main()
