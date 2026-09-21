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
# Calibrated 2026-09-21 (roadmap ablation-runner-calibration, and the
# pre-registration amendment of the same date). These seven are the powered
# ablation's probes, and each has to discriminate applying the concept from
# naming it. Three rules follow from what the old versions got wrong.
#
# Match words, not substrings. `"cri" in text` is true of "described", which
# made the leakage probe's second clause fire on any transcript at all, and
# `"0.5" in text` is true of "0.52 mm/yr", which passed the native-grid probe
# on a reply that refused nothing.
#
# Require the concept to be used, not mentioned. Naming height_cor_xover and
# then ignoring it is the failure the case exists to catch, so the probe asks
# for an application verb and refuses an explicit non-application.
#
# Accept the phrasings a model actually writes. The release probe demanded the
# literal "not mix" and so failed "must not be mixed", which is the wording of
# its own case notes; it scored 0 of 3 in both arms of the pilot because no
# correct answer could pass it.
def _w(t, pattern):
    """Search the transcript for a regular expression, case folded."""
    return bool(re.search(pattern, t, re.I))


_REGRIDDED = r"(?:regrid\w*|interpolated|0\.5[-\s]?degree|half[-\s]?degree|lat[-\s]?lon\s+grid)"
_REFUSAL = (r"(?:refus\w+|declin\w+|cannot|can't|will\s+not|won't|unsuitable|not\s+valid|"
            r"invalid|does\s+not\s+close|doesn't\s+close|not\s+appropriate|no\s+budget)")
_NATIVE = r"(?:native[-\s]grid|\bllc90\b|native\s+llc)"


def transcript_refuses_and_offers_native_grid(t):
    return _w(t, _REGRIDDED) and _w(t, _REFUSAL) and _w(t, _NATIVE)


_GEO = r"\bgeothermal\b"
_GEO_SOURCE = (r"(?:\bancillary\b|geothermalflux(?:\.bin)?|\.bin\b|not\s+a\s+po\.?daac|"
               r"outside\s+po\.?daac|tutorial)")
_GEO_INCLUDED = (r"(?:includ\w+|add\w*|\bterm\b|\bplus\b|\bflux\b)[^.]{0,60}?\bgeothermal\b"
                 r"|\bgeothermal\b[^.]{0,60}?(?:\bterm\b|\bflux\b|includ\w+|added|applied)")
_GEO_DISMISSED = r"\bgeothermal\b[^.]{0,60}?(?:negligible|ignor\w+|omit\w+|not\s+needed|skip\w*|drop\w*)"


def plan_includes_geothermal_term_and_ancillary_source(t):
    if _w(t, _GEO_DISMISSED):
        return False
    return _w(t, _GEO) and _w(t, _GEO_INCLUDED) and _w(t, _GEO_SOURCE)


_PHASE_FAST = r"(?:cal[/\s-]?val|fast[-\s]sampling|\b1[-\s]day\b)"
_PHASE_SCIENCE = r"(?:\b21[-\s]day\b|science\s+orbit)"
_KEPT_APART = (r"(?:separat\w+|apart|distinct|split|different\s+(?:orbit|phase|record|sampling)|"
               r"(?:do\s+not|don't|never|must\s+not|cannot|can't)\s+(?:be\s+)?"
               r"(?:pool\w*|mix\w*|combin\w*|merg\w*|concatenat\w*)|"
               r"not\s+(?:be\s+)?(?:pooled|mixed|combined|merged))")


def transcript_surfaces_orbit_phase_split(t):
    return _w(t, _PHASE_FAST) and _w(t, _PHASE_SCIENCE) and _w(t, _KEPT_APART)


_LEAK = r"(?:leakage|leak\w*\s+into|bleed\w*|land\s+signal)"
_LEAK_CONTEXT = r"(?:\bmascon\w*\b|\bgrace\b|\bcoastal\b|near[-\s]shore|coastline|\bshelf\b)"
_LEAK_HANDLED = (r"(?:\bcri\b|coastal\s+resolution\s+improvement|buffer|caveat|inflat\w+|"
                 r"uncertaint\w+|\bmask\w*\b|cannot\s+be\s+interpreted|do\s+not\s+quote|"
                 r"not\s+a\s+grid[-\s]cell|mascon[-\s]scale)")


def transcript_surfaces_leakage_caveat(t):
    return _w(t, _LEAK) and _w(t, _LEAK_CONTEXT) and _w(t, _LEAK_HANDLED)


_ATLANTIC = r"(?:\batlext\b|\batlantic\b)"
_BASIN_SCOPED = (r"(?:\bbasin\b|\bsection\b|\batlext\b|"
                 r"(?:not|rather\s+than|instead\s+of)\s+the\s+(?:full\s+|whole\s+|entire\s+)?"
                 r"(?:latitude\s+)?circle)")
_CIRCLE_AS_RAPID = r"1\.09\d[^\n]{0,40}rapid|rapid[^\n]{0,40}1\.09\d"


def transcript_uses_atlantic_basin_for_rapid(t):
    if _w(t, _CIRCLE_AS_RAPID):
        return False
    return _w(t, _ATLANTIC) and _w(t, _BASIN_SCOPED)


_XOVER = r"height_cor_xover"
_XOVER_APPLIED = (r"(?:\badd\w*\b|\bappl\w+\b|\bsum\w*\b|\bcorrect\w*\b|\bincluded\b|"
                  r"\bincorporat\w+\b|\+)[^.]{0,80}?height_cor_xover"
                  r"|height_cor_xover[^.]{0,80}?(?:\badd\w*\b|\bappl\w+\b|\bcorrect\w*\b|"
                  r"\bincluded\b|before\s+(?:comput\w+|any\s+statistic))")
_XOVER_SKIPPED = (r"(?:ignor\w+|did\s+not\s+(?:apply|add|use)|didn't\s+(?:apply|add|use)|"
                  r"skip\w*|left\s+out|without)[^.]{0,60}?(?:height_cor_xover|crossover)"
                  r"|height_cor_xover[^.]{0,60}?(?:ignor\w+|not\s+applied|unused)")


def transcript_applies_height_cor_xover(t):
    if _w(t, _XOVER_SKIPPED):
        return False
    return _w(t, _XOVER) and _w(t, _XOVER_APPLIED)


def nothing_downloaded_gate_presented(t):
    return _any(t, "gate", "confirm", "too large", "exceeds", "before download") \
        and _any(t, "gb", "tb", "estimate", "size")


_V4R4B = r"\bv4r4b\b"
_V4R4 = r"\bv4r4\b"
_RELEASE_COMMIT = (r"(?:use|using|used|only|solely|throughout|stick(?:ing)?\s+(?:to|with)|"
                   r"restrict\w*\s+to|confin\w+\s+to|chose|choosing|select\w*|built\s+from|"
                   r"building\s+(?:the\s+)?series\s+from|entirely\s+from)\b[^.]{0,80}?\bv4r4b?\b"
                   r"|\bv4r4b?\b[^.]{0,80}?\b(?:only|throughout|for\s+the\s+(?:whole|entire|full)\s+"
                   r"(?:period|record|series))\b")
_RELEASE_HAZARD = (r"(?:not|never|avoid\w*|cannot|can't|shouldn't|should\s+not|must\s+not|"
                   r"do\s+not|don't)\W+(?:be\s+)?(?:mix\w*|combin\w*|splic\w*|concatenat\w*|"
                   r"merg\w*|interleav\w*)"
                   r"|(?:mix\w*|combin\w*|splic\w*|merg\w*)[^.]{0,80}?"
                   r"(?:spurious|artificial|artefact|artifact|discontinuit\w+|\bstep\b|\bjump\b|"
                   r"\bbias\b|\boffset\b|enters?\s+the\s+trend)")
_YEAR = r"(?:1[89]\d\d|20\d\d)"
_A_SPAN = r"\bv4r4\b[^.]{0,40}?" + _YEAR
_B_SPAN = r"\bv4r4b\b[^.]{0,40}?" + _YEAR


def transcript_names_single_release(t):
    # Assembling a series by giving each release its own span is the trap.
    if _w(t, _A_SPAN) and _w(t, _B_SPAN):
        return False
    if not (_w(t, _V4R4) or _w(t, _V4R4B)):
        return False
    # The case notes allow either route: settle on one named release, or say
    # the two cannot be combined. Either is the concept applied.
    return _w(t, _RELEASE_COMMIT) or _w(t, _RELEASE_HAZARD)


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
