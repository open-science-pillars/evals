# Seven cases, second registered model, N=20 per arm

Both arms of all seven gotcha-avoidance cases, run on one machine rather
than one machine per case. That difference is the reason this record is
worth reading twice: it found five faults in the harness, four of which
weaken a guarantee earlier records relied on.

## Result

```
case                                 ON          OFF       RD          Newcombe 95% out
native-grid-refusal         6/20 0.300  11/20 0.550   -0.250  [-0.496, +0.052] 0/0
swot-calval-window         12/16 0.750   5/18 0.278   +0.472  [+0.136, +0.685] 4/2
ecco-release-mixing         7/17 0.412   3/17 0.176   +0.235  [-0.070, +0.491] 3/3
mht-basin-scope             8/20 0.400   1/19 0.053   +0.347  [+0.082, +0.565] 0/1
swot-crossover-unapplied    1/20 0.050   1/19 0.053   -0.003  [-0.201, +0.188] 0/1
grace-leakage              17/18 0.944  13/19 0.684   +0.260  [+0.001, +0.489] 2/1
geothermal-omission         7/20 0.350   4/19 0.211   +0.139  [-0.140, +0.390] 0/1
--------------------------------------------------------------------------------
POOLED (7 of 7)            58/131 0.443  38/131 0.290   +0.153  [+0.036, +0.264] 9/9
outages: ON 9/140 = 6.4%   OFF 9/140 = 6.4%
```

Reported beside the first model's `+0.131 [+0.003, +0.254]` and never
pooled with it. The two land within 0.022 of each other with heavily
overlapping intervals, on different models and different machines.

This run kept 94 percent of its trials against about 81 percent, and its
losses fall evenly on the two arms rather than ten points apart on one
case. Every loss in both arms is the turn cap, none is rate limiting.

`native-grid-refusal` scored better without the bundle here and was the
strongest positive on the first model. A case that reverses sign between
models is a result about the case and is the first place to look.

## The arm was off

No bundle-off transcript reproduces a line of the concepts its case
cites, audited against every window of those concepts rather than the
three the gate freezes, minus windows shared with material the design
leaves in place:

| case | windows | on arm | off arm |
|---|---|---|---|
| native-grid-refusal | 178 | 1/20 | 0/20 |
| swot-calval-window | 962 | 0/20 | 0/20 |
| ecco-release-mixing | 295 | 0/20 | 0/20 |
| mht-basin-scope | 305 | 0/20 | 0/20 |
| swot-crossover-unapplied | 843 | 0/20 | 0/20 |
| grace-leakage | 526 | 8/20 | 0/20 |
| geothermal-omission | 696 | 0/20 | 0/20 |

The nine bundle-on hits are the positive control: the test fires where
trials could read the concept and is silent where they could not. Eight
fall on grace-leakage, the same case and the same count the first model
produced.

## Provenance

Capabilities at the refs the marketplace serves: `core--v0.6.0`,
`ocean-science--v0.9.0`, `nasa-daac-knowledge--v2026.9.5`. All three
release locks current, checked before anything moved. Scope check passed
at 45, 12 and 243 concepts. Rubric `notes` on both arms, same grader,
same trial count, same turn cap.

This machine held a previous run and months of unrelated work, so the
gate was asked what was readable rather than trusted to guess. It named
226 concept copies and several recorded answers across twenty four
directories. Sixteen trees and files were set aside for the off arm and
all sixteen were put back.

Two installs had to be removed before the run could start, both flagged
by the scope check refusing: a second marketplace serving the same
capability, and a stale second version of another. Both were archived
before removal.

## The two invocations

The off arm was refused by its own gate, correctly, for a leak this
harness created, and then failed on an incomplete fix to that leak.
Rather than discard 140 completed and validly gated bundle-on trials,
the harness was fixed and the off arm run separately against the same
workspace, model, trial count and quarantine discipline.

Every case on the first model ran both arms in one invocation. This one
did not. Recorded because it is true, not because it is thought
harmless.

## What is not measured here

The registered design does not ablate the skills, and the skills carry
more of this material than a pointer. The bundle-off arm is concept
absent, not knowledge absent. The difference above is the effect of
removing the concept files and is not the effect of removing the
knowledge.
