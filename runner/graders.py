"""Programmatic graders: transcript predicates named by the eval cases.

Each returns True (pass) or False (fail) on the transcript text of one trial.
These are fast, deterministic first-pass checks; the rubric judge (judge.py) is
the authoritative grader. A trial passes only if every grader present agrees, so
the programmatic check is a conservative gate, never a rubber stamp.

Registry keys match the `programmatic:` ids in the plugins' eval cases. An id
with no entry here returns None and defers entirely to the rubric judge.
"""
import re


def _has(t, *terms):
    t = t.lower()
    return all(term.lower() in t for term in terms)


def _any(t, *terms):
    t = t.lower()
    return any(term.lower() in t for term in terms)


# --- core ---
def computation_uses_area_weights(t):
    return _any(t, "area weight", "cos(lat", "coslat", "cell area", "weighted(",
                "grid-cell area", "latitude weight")


def headline_carries_uncertainty_or_waiver(t):
    return _any(t, "confidence interval", "95%", "+/-", "±", "uncertainty",
                "standard error", "spread", "no uncertainty", "cannot quantify")


def trend_test_is_autocorrelation_aware(t):
    return _any(t, "autocorrel", "mann-kendall", "hamed", "yue", "block bootstrap",
                "effective sample size", "prewhiten", "serial correlation")


def transcript_detects_sentinels_before_stats(t):
    return _any(t, "-9999", "9999", "fill value", "fill-value", "sentinel") \
        and _any(t, "mask", "exclude", "remove", "audit")


# --- ocean-science ---
def transcript_refuses_and_offers_native_grid(t):
    return _any(t, "regridded", "0.5", "half-degree") \
        and _any(t, "native", "llc90", "refuse", "cannot") \
        and _any(t, "native grid", "native-grid", "llc90")


def plan_includes_geothermal_term_and_ancillary_source(t):
    return _has(t, "geothermal") and _any(t, "ancillary", "geothermalflux", ".bin",
                                          "not a po.daac", "not a podaac", "tutorial")


def transcript_surfaces_leakage_caveat(t):
    return _any(t, "leakage", "land signal", "bleed", "leak into") \
        and _any(t, "mascon", "grace", "cri", "buffer", "coastal")


def transcript_surfaces_orbit_phase_split(t):
    return _any(t, "cal/val", "calval", "cal-val", "fast-sampling", "1-day", "21-day") \
        and _any(t, "orbit", "phase", "science orbit", "separate")


def nothing_downloaded_gate_presented(t):
    return _any(t, "gate", "confirm", "too large", "exceeds", "before download") \
        and _any(t, "gb", "tb", "estimate", "size")


def transcript_uses_atlantic_basin_for_rapid(t):
    atlantic = _any(t, "atlext", "atlantic")
    circle_as_rapid = bool(re.search(r"1\.09\d[^\n]{0,40}rapid|rapid[^\n]{0,40}1\.09\d", t.lower()))
    return atlantic and not circle_as_rapid


def transcript_applies_height_cor_xover(t):
    return _has(t, "height_cor_xover")


def transcript_names_single_release(t):
    return _any(t, "v4r4b", "v4r4") and _any(t, "one release", "single release",
                                             "not mix", "don't mix", "do not mix", "same release")


REGISTRY = {
    "computation_uses_area_weights": computation_uses_area_weights,
    "headline_carries_uncertainty_or_waiver": headline_carries_uncertainty_or_waiver,
    "trend_test_is_autocorrelation_aware": trend_test_is_autocorrelation_aware,
    "transcript_detects_sentinels_before_stats": transcript_detects_sentinels_before_stats,
    "transcript_refuses_and_offers_native_grid": transcript_refuses_and_offers_native_grid,
    "plan_includes_geothermal_term_and_ancillary_source": plan_includes_geothermal_term_and_ancillary_source,
    "transcript_surfaces_leakage_caveat": transcript_surfaces_leakage_caveat,
    "transcript_surfaces_orbit_phase_split": transcript_surfaces_orbit_phase_split,
    "nothing_downloaded_gate_presented": nothing_downloaded_gate_presented,
    "transcript_uses_atlantic_basin_for_rapid": transcript_uses_atlantic_basin_for_rapid,
    "transcript_applies_height_cor_xover": transcript_applies_height_cor_xover,
    "transcript_names_single_release": transcript_names_single_release,
}


def run_programmatic(checker_id, transcript):
    fn = REGISTRY.get(checker_id)
    if fn is None:
        return None  # unknown id: defer entirely to the rubric judge
    return bool(fn(transcript))
