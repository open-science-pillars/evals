# Shard: grace-leakage, N=20 per arm

Both arms completed and no gate refused. The rendered delta is **+0.091**, and
it should not be read as the knowledge-layer effect for this case. Three
separate reasons are set out below: half of the forty trials were lost to the
turn allowance and the two arms were thinned unequally; the bundle-off arm
reproduces the graded behaviour without reading the concept the case cites; and
the record already on the default branch says a stopping condition was met
before this run started.

## Provenance

Harness repositories on their default branch:

| repo | HEAD |
|---|---|
| evals | `90164a8c5b7abf2395328637bfb910219dd92fb7` |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` |

Capabilities at the refs the catalog serves, confirmed against
`released_refs.py` rather than against a list kept beside it:

| plugin | ref served | checkout | lock | installed |
|---|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77` | current | 0.6.0 |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d` | current | 0.9.0 |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef00` | current | 2026.9.5-6b0ef007a964 |

Each installed tree was compared to its tag checkout by recursive content
digest and was byte identical. Each plugin has exactly one install, in one
catalog cache; the dependency install of `nasa-daac-knowledge` and the later
explicit install resolved to the same copy rather than to a second one.

The three locks were checked while the knowledge was still in place, before
anything moved, and all three read `current` (`release-locks.json`). The arms
themselves then ran with the lock check suppressed, so `release_lock_current`
is recorded as unchecked inside `results_on.json` and `results_off.json`. Both
values are reported here because they answer different questions.

## Isolation

An `evals` checkout was present at `/home/user/evals` when this run began, that
is, outside the tree the run was prepared from. It was clean, with no
uncommitted work and no stashes, and its HEAD was the same commit as the fresh
clone, so nothing was lost by removing it. Its contents including its `.git`
directory were deleted before the workspace was prepared; an empty directory
was left at that path so the working directory of the running shell stayed
valid. A readable checkout there would have been visible to a trial reading an
absolute path, which is the condition the bundle-off arm exists to exclude.

`prepare_workspace.py` dropped eleven directories and certified the result.
`/home/user/src` was deleted before the run started. Both arms' leak checks
ran against the filesystem root, and the second of them passed only because the
checkout above had already been removed.

Leak check verdicts, verbatim from `run.log`:

```
checked against the frozen fingerprints: no recorded answer to the 1 cases is readable under /; the cited concepts are readable, which is what this arm is
```

```
checked against the frozen fingerprints: no copy of a cited concept and no recorded answer to the 1 cases is readable under /
```

Both arms were graded by the same text, `notes`, which is what allows the
scoreboard to render a delta between them at all. The trial model and the judge
model were the same value in both arms and are recorded in the results files.

## Results, as the run produced them

| arm | passes | valid trials | errors | rate | Wilson 95% CI |
|---|---|---|---|---|---|
| ON | 9 | 9/20 | 11 | 1.000 | [0.701, 1.000] |
| OFF | 10 | 11/20 | 9 | 0.909 | [0.623, 0.984] |

Threshold 0.8. Both arms return the verdict PASS. Rendered delta: **+0.091**.

Wall clock 51m27s, from 16:15:36Z to 17:07:03Z. The ON arm finished at
16:44:46Z and the OFF arm at 17:07:03Z. Concurrency 4. Per trial, counting
every trial including the lost ones: ON min 123s, median 168s, mean 214s, max
764s; OFF min 128s, median 206s, mean 241s, max 412s. Among trials that
actually graded, the median was 171s in the ON arm and 286s in the OFF arm.

Transcripts for all forty trials are committed beside this record under
`transcripts_on/` and `transcripts_off/`, so every claim below can be checked.
Trial outcomes by number, from `results_off.json`: OFF passes are trials 2, 4,
8, 12, 13, 14, 15, 17, 19 and 20; trial 3 is the single graded failure; trials
1, 5, 6, 7, 9, 10, 11, 16 and 18 were lost to the turn allowance.

## Outages

Twenty of the forty trials were lost. Every one of them failed the same way,
with a twenty nine character transcript reading `Error: Reached max turns (30)`
against the manifest allowance of `max_turns: 30`. None of them is a failure
and none is in any rate above.

| arm | lost | of | fraction |
|---|---|---|---|
| ON | 11 | 20 | 0.55 |
| OFF | 9 | 20 | 0.45 |

The scoreboard flags this itself, and its wording is the right one: the arms did
not lose trials at the same rate, so a difference across samples thinned
unequally is not read as a treatment effect without saying so. The effect runs
in the direction that inflates the ON arm, because consulting the bundle costs
turns, so the arm holding the knowledge exhausts its allowance more readily and
the trials that survive it are the atypically brief ones.

This loss rate is far outside what the five sibling records on other branches
report for the same allowance. Their ON arms lost 8, 1, 0, 3 and 1 of 20, and
their OFF arms 7, 0, 0, 5 and 3 of 20. At 11 and 9 this run is the worst of the
set by a wide margin, and the interval it reports is correspondingly wide. The
point estimates rest on 9 and 11 trials, not on the 20 per arm that was
registered.

## What the bundle-off arm actually read

The quarantine worked. No bundle-off transcript cites the concept the case is
built on, and several describe probing for it and finding nothing. Concept file
paths named anywhere in the transcripts, counted by citation:

| arm | citations |
|---|---|
| ON | `grace-coastal-leakage.md` 8, `grace-fo-mascons.md` 7, `grace-mass-to-sea-level.md` 4, `grace-intermission-gap.md` 3, four others once each |
| OFF | `grace-mass-to-sea-level.md` 3, `sea-level-budget-closure.md` 3, three others once each, across 6 of 20 transcripts |

Eight of the nine passing ON trials cite `grace-coastal-leakage.md` by path. No
OFF trial cites it at any point. Yet all ten passing OFF trials discuss coastal
leakage, between three and six times each, and nine of the ten name the CRI
filter. So the graded behaviour survives the removal of the concept, and the
question is what carries it.

Three of the ten say in the response itself that they read no concept. Trial 2
is the clearest, and it passed:

> **Not read:** every one of those concepts.

> So: **no installed concept was actually read.** Everything below is general
> method, labeled as such, and the numbers that would settle it live in concepts
> I could not open.

Trial 8 states "no installed concept was read, and nothing below is cited to
one", and is careful in the other direction, saying of the leakage and GIA
concepts that it "won't work around them from memory". Trial 13 does attribute
its leakage arithmetic to "general knowledge rather than a concept". So of the
three, two say the substance is their own and one declines to substitute for
the concept while still passing. The judge passed all three. The other seven
passing trials make no declaration either way, so their provenance is not
established by the transcript.

Two things outside every ablated tree are named by those trials. First, the
skills, which bundle-off does not touch, name the hazard and point at the
concept. `skills/sea-level/SKILL.md`:

> the GRACE effective resolution, coastal-leakage, and GIA facts live in the
> GRACE dataset concept and its gotchas

> Its effective resolution, coastal leakage, and the baked-in GIA correction
> are first-order and live in the GRACE dataset concept and its gotchas;
> consult and cite them.

Second, and more than a pointer, a script in the same skills tree states CRI
substance directly. `skills/sea-level-budget/scripts/slb_mass_mascons.py`:

> The CRI partition of the coastal mascons is the product's; no further coastal
> buffer is applied, and the stamp says so.

Trial 2 cites that file by name and reproduces exactly that point. The full
concept slug `grace-coastal-leakage` appears nowhere outside a `knowledge/`
tree, but the phrase `coastal-leakage`, the CRI filter and the effective
resolution caveat all do.

What this supports, and what it does not. The surviving text accounts for the
off arm naming the filter and the hazard: those words are on disk in files the
arm does not remove. It does not contain the substance the passing trials
actually supply, which is that Greenland ice loss dominates those coastal
mascons, that the effective resolution is a few hundred kilometres against a
narrower shelf strip, and that the sign of the contamination is a trap. Three
trials say in so many words that they supplied that from their own knowledge.
For the other seven the transcripts do not say. So the honest statement is
narrower than a demonstrated confound and wider than an impression: the bundle
off arm here is not knowledge absent. It is concept absent, with the topic
pointers and one substantive script retained, and with the runtime supplying
material it states it did not read. On the evidence in this run the residual
text and the runtime's own knowledge cannot be separated, and no claim is made
that either alone produced the rate.

## The stopping condition recorded before this run

`scoreboard/shard-opus-native-grid-refusal/SHARD.md`, merged to the default
branch, ends by stating that the remaining thirteen shards must not start until
the ablation scope question is settled, because the arm it measured compared
knowledge against knowledge. Five sibling branches carry completed records
dated the same day, and none of the other four mentions that condition. This
run was started and completed after that record was merged, and the section
above is the same finding reached again by a different route: there the rule was
restated in a skill, here the concept is genuinely gone and the behaviour
arrives anyway.

The number in this record is reported exactly as the run produced it. It is not
evidence that the stopping condition has been resolved.

## Restoration

Every tree came back, and the holding directory is empty.

| tree | files |
|---|---|
| `run/agent-evals/ecco/cases` | 17 |
| `run/ocean-science/knowledge` | 84 |
| `run/core/knowledge` | 12 |
| `run/nasa-daac-knowledge/knowledge` | 243 |
| cache `ocean-science/0.9.0/knowledge` | 84 |
| cache `core/0.6.0/knowledge` | 12 |
| cache `nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge` | 243 |
| `transcripts_on` | 60 |
| `transcripts_off` | 60 |

`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` returns nothing.

## What was not changed

No threshold, trial count, turn allowance, grader, case, manifest or harness
file was edited, before, during or after the run. Nothing was deleted to
satisfy a gate. The deletion recorded under Isolation was of a duplicate
checkout outside the prepared tree, which the procedure calls for, and it
removed no unique content. The transcript directories are excluded by
`.gitignore` and were added with `git add -f`, which is how the two sibling
records already in this repository carry theirs; `.gitignore` itself was not
edited.
