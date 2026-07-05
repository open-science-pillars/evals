#!/usr/bin/env python3
"""Deterministic self-test of the eval runner's grading and aggregation.

Feeds known good/bad transcript snippets to the programmatic graders and asserts
correct classification, then checks the binomial verdict. This exercises the
runner logic without slow, flaky live agentic trials (the full N=20 live sweep
is the CI job). Run: `python selftest.py` (exit 0 = green).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import run_programmatic  # noqa: E402
from stats import verdict  # noqa: E402

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
    # Aggregation: 5/5 seed reproduces PASS at 0.8; 3/5 does not.
    assert verdict(5, 5, 0.8)["pass"] is True
    assert verdict(3, 5, 0.8)["pass"] is False
    assert verdict(18, 20, 0.8)["pass"] is True   # point rate 0.9 >= 0.8

    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print(f"selftest: {len(CASES)} graders classify good/bad transcripts correctly; "
          "verdict aggregation correct")
    print("evals runner selftest: PASSED")


if __name__ == "__main__":
    main()
