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
from scoreboard import comparison, label, mismatched_rubrics, outage_block, render  # noqa: E402

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


# The seven probes the powered ablation runs, each with several phrasings a
# reply actually uses and several that must not pass. One good and one bad per
# grader is what let the old release probe through: its fixture was written in
# the grader's own words ("not mix"), so the selftest agreed with it while the
# pilot scored 0 of 3 in both arms, because a reply saying "must not be mixed"
# failed. A probe is calibrated when it accepts the paraphrases and refuses the
# near misses, so both lists are part of the check.
PROBE_CALIBRATION = [
    ("transcript_names_single_release",
     ["I will use ECCO V4R4 SSH. Note that V4R4 and V4R4B must not be mixed, because the release "
      "correction would enter the trend.",
      "Sticking to V4R4B throughout the 1992-2017 period; combining it with V4R4 would introduce a "
      "spurious step.",
      "There are two SSH releases, V4R4 and V4R4B. I am building the series from V4R4B only.",
      "I'll use a single release, V4R4B, throughout, and not mix it with V4R4."],
     ["ECCO has a v4r4 dataset. People often say you should use a single release. Here is a series "
      "assembled from whatever collections cover the period.",
      "I'll grab v4r4 for 1992-2010 and v4r4b for 2011-2017. Some say do not mix releases but "
      "coverage matters more.",
      "I'll pull whatever SSH collections cover 1992-2017 and concatenate them."]),
    ("transcript_surfaces_leakage_caveat",
     ["Near the coast, GRACE mascon coastal leakage bleeds land signal in; I apply a CRI buffer.",
      "The shelf signal is contaminated by leakage from the ice sheet, so the trend carries an "
      "inflated uncertainty rather than a bare formal error.",
      "This is a mascon-scale value, not a grid-cell one, and land signal leaks into the coastal "
      "mascons."],
     ["I described the GRACE leakage issue.",
      "There may be leakage near the coast. Anyway the mascon trend is 2.3 mm/yr.",
      "I take the mascon value at the coastal grid point directly."]),
    ("transcript_refuses_and_offers_native_grid",
     ["That regridded 0.5-degree product cannot close a budget; I refuse and offer the native-grid "
      "llc90 path with snapshots.",
      "A budget does not close on the interpolated lat-lon grid; I will not compute it there, and "
      "the native llc90 fields are the right input."],
     ["The North Atlantic SSH trend on the native grid llc90 is 0.52 mm/yr.",
      "Sure, I'll compute the heat budget from the 0.5-degree regridded field."]),
    ("transcript_applies_height_cor_xover",
     ["I add height_cor_xover (gated by height_cor_xover_qual) to ssha_karin before computing "
      "statistics.",
      "The crossover correction height_cor_xover is applied to the SSH field first."],
     ["The SWOT product has a height_cor_xover field. I ignored it and used ssha_karin directly.",
      "I compute mean and std of ssha_karin over the good-flagged pixels."]),
    ("transcript_surfaces_orbit_phase_split",
     ["The cal/val 1-day fast-sampling phase and the 21-day science orbit are separate records; I "
      "keep them apart.",
      "These are two different sampling phases, the 1-day calval one and the 21-day science orbit, "
      "and they must not be pooled into one series."],
     ["I take every SWOT pass over the region across the whole mission and average them.",
      "The 21-day repeat gives good coverage, so I pool everything available."]),
    ("plan_includes_geothermal_term_and_ancillary_source",
     ["Terms: tendency, advection, diffusion, forcing, and the geothermal flux from the ancillary "
      "geothermalFlux.bin (not a PO.DAAC collection).",
      "I include a geothermal term, read from the ancillary binary rather than from a PO.DAAC "
      "collection."],
     ["Terms: tendency, advection, diffusion, and surface forcing. That covers a full-depth budget.",
      "The geothermal flux is negligible for this budget, so I drop it and use the ancillary file "
      "for nothing."]),
    ("transcript_uses_atlantic_basin_for_rapid",
     ["For the RAPID comparison I use the Atlantic (atlExt) section, 0.666 PW for 2010, not the "
      "full circle.",
      "RAPID measures the Atlantic basin, so I mask to the atlExt basin before integrating."],
     ["The 26.5N transport is 1.098 PW, which I compare directly against the RAPID mean.",
      "I integrate the full latitude circle at 26.5N and call that the Atlantic overturning."]),
]


# Real transcripts from a run, not phrasings anyone imagined. The probes were
# calibrated on 2026-09-21 against hand-written examples, which is better than
# fixtures written in the grader's own words and still not the same as output a
# model produced: the first pilot to return real answers failed one of them,
# because a reply quotes the collection identifier LLC0090 where the pattern
# asked for llc90, and offers a "native path" where it demanded a "native
# grid". A transcript the rubric judge graded PASS belongs here, so a probe
# cannot drift back to language nobody writes. The file name carries the case
# and the expected classification.
TRANSCRIPT_FIXTURES = Path(__file__).parent / "fixtures" / "transcripts"
PROBE_FOR_CASE = {
    "native-grid-refusal": "transcript_refuses_and_offers_native_grid",
    "grace-leakage": "transcript_surfaces_leakage_caveat",
    "ecco-release-mixing": "transcript_names_single_release",
    "swot-calval-window": "transcript_surfaces_orbit_phase_split",
    "swot-crossover-unapplied": "transcript_applies_height_cor_xover",
    "mht-basin-scope": "transcript_uses_atlantic_basin_for_rapid",
    "geothermal-omission": "plan_includes_geothermal_term_and_ancillary_source",
}


def recorded_transcripts():
    """(probe id, expected verdict, path) for every saved real transcript."""
    for path in sorted(TRANSCRIPT_FIXTURES.glob("*.txt")):
        case, _, tail = path.name.partition(".")
        probe = PROBE_FOR_CASE.get(case)
        if probe:
            yield probe, tail.endswith("pass.txt"), path


def main():
    fails = []
    for cid, good, bad in CASES:
        g = run_programmatic(cid, good)
        b = run_programmatic(cid, bad)
        if g is not True:
            fails.append(f"{cid}: good transcript classified {g}, expected True")
        if b is not False:
            fails.append(f"{cid}: bad transcript classified {b}, expected False")
    probe_checks = 0
    recorded = 0
    # An empty fixture directory must fail rather than pass quietly. These
    # files were gitignored when they were first added, so on a clean checkout
    # this loop had nothing to iterate and the selftest agreed with itself. A
    # guard that can be satisfied by the absence of its own evidence is not a
    # guard.
    if not list(recorded_transcripts()):
        fails.append(f"no recorded transcripts under {TRANSCRIPT_FIXTURES}: the probes are "
                     "checked only against phrasings we invented, which is the gap these exist "
                     "to close. Check they are committed and not ignored.")
    for probe, expected, path in recorded_transcripts():
        recorded += 1
        got = run_programmatic(probe, path.read_text())
        if got is not expected:
            fails.append(f"{probe}: the recorded transcript {path.name} classified {got}, "
                         f"expected {expected}; a probe must agree with output a model produced")
    for cid, goods, bads in PROBE_CALIBRATION:
        for text in goods:
            probe_checks += 1
            if run_programmatic(cid, text) is not True:
                fails.append(f"{cid}: a phrasing that applies the concept was rejected: {text[:70]}")
        for text in bads:
            probe_checks += 1
            if run_programmatic(cid, text) is not False:
                fails.append(f"{cid}: a phrasing that only mentions the concept passed: {text[:70]}")
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

    # The rubric a case names has to be the rubric that grades it. Nine cases
    # across two repositories named documents that never existed and were
    # graded by their notes without a word about it, so these check that a
    # name which resolves to nothing now stops the run.
    import tempfile
    from run_evals import resolve_rubric
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / "cap" / "evals").mkdir(parents=True)
        (ws / "cap" / "evals" / "real.md").write_text("the written rubric")

        def case(spec, notes="pass when the answer states the caveat outright"):
            return {"id": "c", "_plugin": "cap", "notes": notes,
                    "graders": [{"rubric": spec}]}

        text, source = resolve_rubric(case("real.md"), ws)
        if "the written rubric" not in text or not source.endswith("real.md"):
            fails.append("a rubric file that exists is not read as the rubric")
        text, source = resolve_rubric(case("notes"), ws)
        if source != "notes" or "states the caveat" not in text:
            fails.append("`rubric: notes` does not grade against the case's notes")
        text, source = resolve_rubric(case("pass when it names the product"), ws)
        if source != "inline" or "names the product" not in text:
            fails.append("an inline rubric is not read as the rubric")
        for spec, why in [("missing.md", "a rubric file that does not exist"),
                          ("leakage-handling.md", "the rubric name that was never there")]:
            try:
                resolve_rubric(case(spec), ws)
                fails.append(f"{why} resolved instead of stopping the run")
            except ValueError:
                pass
        try:
            resolve_rubric(case("notes", notes=""), ws)
            fails.append("`rubric: notes` resolved on a case with no notes")
        except ValueError:
            pass

    # A copy of the knowledge is found because it is a copy, not because
    # someone predicted where it would be. The wrapped case is the one that
    # matters: a concept wraps its prose and a transcript quoting it does not.
    from leak_check import cited_concepts, scan
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        prose = ("Nearshore ocean mass series inherit land signal, so apparent coastal "
                 "trends can be dominated by leakage rather than by ocean change and "
                 "the series is not what its coordinates claim.")
        (ws / "capa" / "knowledge").mkdir(parents=True)
        (ws / "capa" / "knowledge" / "x.md").write_text(
            f"---\nstatus: stable\n---\n# Heading\n\n{prose}\n")
        (ws / "ae" / "ecco" / "cases").mkdir(parents=True)
        (ws / "ae" / "ecco" / "fx").mkdir(parents=True)
        (ws / "ae" / "ecco" / "cases" / "c1.yaml").write_text(
            "id: c1\nconcept_basis: [knowledge/x.md]\n"
            "fixtures: [ecco/fx/stub.md]\nnotes: n\n")
        (ws / "ae" / "ecco" / "fx" / "stub.md").write_text(prose)
        man = ws / "m.yaml"
        man.write_text("name: t\ncases:\n  - {id: c1, plugin: capa, "
                       "case: ae/ecco/cases/c1.yaml}\n")

        by_case, allowed = cited_concepts(ws, man, None)
        if not by_case.get("c1"):
            fails.append("the cited concept was not resolved in the workspace")

        # The concept itself and the declared fixture: one is the copy to find,
        # the other is what the case is allowed to expose.
        hits, _ = scan([ws], by_case, {"c1"}, allowed)
        found = {h[2].name for h in hits}
        if "x.md" not in found:
            fails.append("the concept's own file was not found by its text")
        if "stub.md" in found:
            fails.append("a declared fixture was reported as a leaked copy")

        # The same text, wrapped at seventy columns the way a concept writes it.
        wrapped = ws / "elsewhere" / "copy.md"
        wrapped.parent.mkdir()
        words, line, out = prose.split(), "", []
        for w in words:
            if len(line) + len(w) > 60:
                out.append(line); line = w
            else:
                line = f"{line} {w}".strip()
        out.append(line)
        wrapped.write_text("\n".join(out))
        hits, _ = scan([ws], by_case, {"c1"}, allowed)
        if not any(h[2].name == "copy.md" for h in hits):
            fails.append("a copy wrapped across lines was not found, which is the "
                         "mistake the whitespace normalisation exists to prevent")

        # A recorded answer beside the case contaminates both arms.
        ans = ws / "ae" / "ecco" / "results" / "run1" / "transcripts"
        ans.mkdir(parents=True)
        (ans / "c1.md").write_text("the graded answer to this case")
        _, answers = scan([ws], by_case, {"c1"}, allowed)
        if not any(a[1].name == "c1.md" for a in answers):
            fails.append("a recorded answer to the case was not reported")

    # Outages are reported beside the delta, and an uneven loss is called out.
    even_a = dict(a, cases=[dict(a["cases"][0], errors=1, trials_requested=20)])
    even_b = dict(even_a, bundle="off",
                  cases=[dict(a["cases"][0], errors=1, trials_requested=20)])
    block = outage_block(even_a, even_b)
    if "lost 1 of 20" not in block or "did not lose trials at the same rate" in block:
        fails.append("an even outage rate is misreported or wrongly flagged")
    uneven = dict(even_b, cases=[dict(a["cases"][0], errors=8, trials_requested=20)])
    if "did not lose trials at the same rate" not in outage_block(even_a, uneven):
        fails.append("an arm that lost four times as many trials is not flagged")
    if outage_block(dict(a, cases=[dict(a["cases"][0], errors=0, trials_requested=20)])) != "":
        fails.append("a single arm with no outages still printed an outage line")

    # Two arms graded by different text do not have a delta between them.
    armed = dict(a, cases=[dict(a["cases"][0], rubric="notes")])
    other = dict(armed, bundle="off",
                 cases=[dict(a["cases"][0], rubric="cap/evals/real.md")])
    if mismatched_rubrics(armed, other) != [a["cases"][0]["id"]]:
        fails.append("a case graded differently in the two arms is not flagged")
    try:
        render(armed, other)
        fails.append("a delta was rendered between arms graded by different rubrics")
    except SystemExit:
        pass

    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print(f"selftest: {len(CASES)} graders classify good/bad transcripts correctly; "
          f"the {len(PROBE_CALIBRATION)} powered ablation probes discriminate application from "
          f"mention over {probe_checks} phrasings and agree with {recorded} recorded transcripts; "
          f"{len(JUDGE)} judge replies (whole, truncated, absent, ambiguous) read correctly; "
          f"{len(TOOLS)} tool specs split into names and rules correctly; "
          "verdict aggregation correct; a copy of a cited concept is found by its text "
          "even when wrapped, and a recorded answer beside a case is reported; "
          "outages are reported per arm and an uneven "
          "loss flagged; a rubric a case names but cannot resolve stops "
          "the run and a delta between differently graded arms is refused; the "
          "cross-runtime record, the drivers and the scoreboard's runtime comparison behave")
    print("evals runner selftest: PASSED")


if __name__ == "__main__":
    main()
