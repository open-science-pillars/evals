# WITHDRAWN 2026-09-22: this pilot measured nothing

Everything below this notice is what was published on 2026-07-05. It is
kept as published rather than deleted, and none of its numbers should be
read as a result.

**The bundle-OFF arm was never off.** It moved one knowledge tree aside,
the ocean capability's own. Every case in this suite names its ground
truth by `concept_basis`, and thirteen of the suite's fourteen citations
name concepts in the provider knowledge bundle, a separate plugin
installed into a separate cache that neither arm touched. A shard probe
on 2026-09-21 proved it from the transcripts rather than from a reading
of the harness: an off-arm trial cites both of its case's concepts by
their paths in the provider bundle and opens "I read the bundle concepts
before touching data, and they stop this computation as specified", in
the arm where that knowledge is supposed to be gone.

So the pooled 0.76 in both arms and the per-case delta of 0.00 below
compared an arm holding the cited knowledge against an arm holding the
cited knowledge. The identity between the arms is what the harness was
bound to produce. The design conclusion the page draws from it, that the
skills carry the gotcha rules and the concept files add nothing, does not
follow: the pilot is no evidence for that reading and none against it.
The confound may well be real and is an untested hypothesis again.

The harness derives the arm's scope now instead of assuming it, walking
the plugins the cases name plus every dependency those plugins declare,
and it stops a run whose cases cite knowledge the arm cannot remove.
`runner/ablation_scope.py` is that check. The withdrawal is recorded in
the pre-registration's amendments under 2026-09-22, and the powered run
will be the first measurement this experiment has made.

---

# Ablation pilot (underpowered, NOT the pre-registered result)

A harness sanity check run 2026-07-05, N=3, model claude-opus-4-8 (the
pre-registered model claude-fable-5 was quota-exhausted this session). The
powered run is N=20 on the recorded model in a CI/cloud environment; the
go/stop conditions in the pre-registration are tied to THAT run, not this.

## What the pilot showed

- The harness works end to end: the bundle-OFF arm stripped `knowledge/` from
  the installed plugin and restored it; the scoreboard renders the delta.
- **No detectable ON-OFF difference** (pooled 0.76 both arms, per-case delta
  0.00 across all 7 cases). At N=3 this is underpowered, but the perfect
  identity points at a design confound: the skills carry the gotcha rules
  (the Must-NOT lists and Knowledge-first restatements live in the skill
  bodies, which stay loaded in both arms), so stripping only the `knowledge/`
  concept files does not change behaviour on these prompts.

## Implication for the powered run

The pre-registered ablation ("knowledge/ removed, skills untouched") may not
isolate the knowledge layer, because the skills duplicate the gotcha rules.
The powered run should either (a) also ablate the gotcha content from the
skills, or (b) target cases where the answer needs the concept's detail (the
numeric anchors, uncertainty structure) that the skills defer to the concepts
for, not just the trap's existence. `ecco-release-mixing` failed in BOTH arms
(0/3), a separate signal that either the skill does not route to it or the
grader is too strict; worth checking before the powered run.
