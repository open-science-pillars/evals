# Ablation pilot (underpowered, NOT the pre-registered result)

A harness sanity check run in Session 19, N=3, model claude-opus-4-8 (the
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
