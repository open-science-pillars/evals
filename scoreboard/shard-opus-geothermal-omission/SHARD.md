# Shard: geothermal-omission, N=20 per arm

Both arms completed and no gate refused. The decisive check came back empty: the
bundle-off arm reproduced no concept prose in any of its twenty transcripts.

**The rates below are not the rates the case's authoritative grader produced.**
Every failing trial in both arms failed on one clause of the programmatic
predicate, and that clause fired on correct answers. This is set out under
"Why both arms sit on the floor" and is the main thing this shard has to report.

## Provenance

| repo | HEAD |
|---|---|
| evals | `90164a8c5b7abf2395328637bfb910219dd92fb7` (#62 r7-leakcheck-wording) |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` (#40 r7-fixture-leak) |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` (#89) |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` (#119 r7-prereg-leak) |

| plugin | ref served | checkout | lock | installed |
|---|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77` | current | 0.6.0 |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d` | current | 0.9.0 |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef00` | current | 2026.9.5-6b0ef007a964 |

Refs were resolved by `released_refs.py` against the catalog, not from a list,
and all three match the tags this run checked out. Lock states are
`release-locks.json`, written by `ablate.sh` before anything moved. Exactly one
install of each plugin: one version directory per plugin, one marketplace, and
three knowledge trees on the machine. Each installed version equals its tag.

An `evals` checkout existed outside `/home/user/src` when this run started, at
`/home/user/evals`: detached at `90164a8`, clean, carrying no local commits. It
was deleted before the workspace was prepared, because a checkout outside the
prepared tree is readable by a trial and would defeat the bundle-off arm.
`prepare_workspace.py` then certified the prepared tree, and `/home/user/src`
was deleted before the run. Nothing in the harness, the manifest, the cases, the
graders, the thresholds or the trial counts was modified, and the trial model
and judge model were the same in both arms and are recorded in the results files.

## Results, as the run produced them

| arm | passes | valid trials | errors (outages) | rate | Wilson 95% CI |
|---|---|---|---|---|---|
| ON | 0 | 16/20 | 4 | 0.00 | [0.0, 0.194] |
| OFF | 1 | 18/20 | 2 | 0.056 | [0.01, 0.258] |

Rendered delta, from `ablation.html`: **-0.056**, verdict FAIL, threshold 0.8.
Both arms fall below the threshold, so the case verdict is FAIL in both.

The headline of this experiment is the pooled risk difference across the seven
cases, per the registered decision rule. This shard is one case and does not
supply that headline. The registered rule also commits that a per-case breakdown
publishes alongside a null, which is what this file is.

Wall clock: 58m19s total (16:17:18Z to 17:15:37Z). ON arm 16:17:20 to 16:49:28
(~32m08s including its leak check); OFF arm 16:49:28 to 17:15:36 (~26m08s
including the second). Per trial: ON min 190s, median 280s, mean 321s, max 711s;
OFF min 175s, median 264s, mean 277s, max 522s. Concurrency 4.

## Outages

Six trials of forty never graded, all with the same signature, a 29 character
`empty or limit message` at `max_turns: 30`:

| arm | lost | trial ids |
|---|---|---|
| ON | 4/20 (0.20) | 9, 10, 14, 19 |
| OFF | 2/20 (0.10) | 15, 17 |

The arms did not lose trials at the same rate; the difference is +0.10 toward
the ON arm. `scoreboard.py` renders a standing explanation for an asymmetry in
this direction, that consulting the bundle costs turns so the arm holding the
knowledge exhausts its budget sooner. That text is generated for any such split
and is not a result computed from this shard, and 4 against 2 is thin. What the
shard does establish is that both rates are computed on a subset selected for
brevity. No quota message and no other error kind appeared.

## Both leak checks, verbatim from `run.log`

ON arm:

```
checked against the frozen fingerprints: no recorded answer to the 1 cases is readable under /; the cited concepts are readable, which is what this arm is
```

OFF arm:

```
checked against the frozen fingerprints: no copy of a cited concept and no recorded answer to the 1 cases is readable under /
```

Both were run against the whole filesystem. The case cites three concepts, two
of them files both named `ecco-heat-budget.md`, one in `nasa-daac-knowledge` and
one in `ocean-science`. `ablation_scope.py --check` reported that every cited
concept sits inside a tree the arm removes, and no gate refused at any point.

## The decisive check

`transcript_audit.py`, verbatim:

```
on arm: 20 transcripts, 1 reproduce concept prose, 68 path mentions
   trial20.txt
off arm: 20 transcripts, 0 reproduce concept prose, 60 path mentions
the bundle-off arm reproduced no concept prose in 20 transcripts; its 60 path mentions are names, not reads
```

The bundle-off arm was off. Its 60 path mentions are names produced by the
skills, which the registered design does not ablate. The one ON transcript that
reproduces concept prose is the expected case: in that arm the concepts are
readable, which is what that arm is.

## Why both arms sit on the floor

A trial passes only if every grader present agrees. Counting the two graders
separately across the 34 valid trials:

| arm | programmatic | rubric (authoritative) |
|---|---|---|
| ON | 0/16 | 16/16 PASS |
| OFF | 1/18 | 17/18 PASS |

The rubric judge, which the runner's own documentation calls the authoritative
grader, passed 33 of the 34 trials that graded. The programmatic predicate
passed 1. The published rates are the conjunction, so they are the programmatic
predicate's rates.

The predicate is `plan_includes_geothermal_term_and_ancillary_source`. It
requires the geothermal term, an inclusion phrasing and an ancillary source, and
before any of those it applies a veto:

```python
_GEO_DISMISSED = r"\bgeothermal\b[^.]{0,60}?(?:negligible|ignor\w+|omit\w+|not\s+needed|skip\w*|drop\w*)"
```

Replaying the predicate clause by clause over the kept transcripts places every
failure on that veto and nowhere else:

| arm | veto fired | failed another clause | passed the predicate |
|---|---|---|---|
| ON | 16 | 0 | 0 |
| OFF | 16 | 1 | 1 |

The 32 trials the veto rejected are, trial for trial, exactly the 32 the rubric
judge graded PASS. The single OFF trial that failed a different clause is the
single trial the rubric judge graded FAIL, and the single trial that passed the
predicate is the single published pass.

What the veto matched is the phrase the case is named after. The matches are
`geothermal omitted` and `geothermal-omitted`, written by trials that had
included the term and were naming the error they were avoiding, for example a
budget described as the `geothermal-omitted` one, or a statement that omitting
the term leaves a residual. The regular expression cannot tell a plan that
dismisses the term from a plan that includes it and names the dismissal as the
trap, because it looks only for the two words within sixty characters.

`graders.py` already carries this lesson, written above these patterns:

> The release probe demanded the literal "not mix" and so failed "must not be
> mixed", which is the wording of its own case notes; it scored 0 of 3 in both
> arms of the pilot because no correct answer could pass it.

That is the same defect in a different case, and the note sits eleven lines
above the veto that reproduces it.

## Consequence

The numbers in "Results" are reported exactly as the run produced them and
nothing was adjusted to accommodate this. They should not be read as this case's
knowledge-layer effect, for two reasons. The rates are a floor set by a grader
clause that rejects correct answers, not a measurement of the behaviour the case
describes. And the sign of the difference depends on which grader is read:
graded by the conjunction the delta is -0.056, and graded by the authoritative
rubric alone the same trials give ON 16/16 (1.00) against OFF 17/18 (0.944), a
delta of +0.056. A shard whose sign turns on that choice is not evidence in
either direction.

The second figure is written here for comparison only. It is not this shard's
result, it is not offered as a substitute for the registered metric, and the
graders were frozen before the bundle-off arm ran, so it is not a rule anything
should be regraded under now. The registered analysis is the conjunction.

This case's contribution to the pooled risk difference carries the same defect,
so the pooled figure should not absorb it silently while this clause stands.

Nothing was changed to make this run pass or to make it fail: no grader, no
threshold, no case, no manifest, no trial count and no line of the harness.
Nothing was deleted to satisfy a gate.

## Restoration

Every tree came back, and the counts match the sibling record:

| tree | files |
|---|---|
| `run/agent-evals/ecco/cases` | 17 |
| `run/ocean-science/knowledge` | 84 |
| `run/core/knowledge` | 12 |
| `run/nasa-daac-knowledge/knowledge` | 243 |
| cache `core/0.6.0/knowledge` | 12 |
| cache `ocean-science/0.9.0/knowledge` | 84 |
| cache `nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge` | 243 |
| `transcripts_on` | 60 |
| `transcripts_off` | 60 |

`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` is empty. The runner
reported `put back 8 directories` and `transcripts kept: 40 trial files`.

## Two notes on the record

The instruction for this run stated that six sibling shards had completed this
recipe. Five exist on the remote: `ecco-release-mixing`, `mht-basin-scope`,
`native-grid-refusal`, `swot-calval-window` and `swot-crossover-unapplied`. A
sixth may be unpushed. The count is recorded here rather than assumed.

`scoreboard/shard-opus-native-grid-refusal/SHARD.md` concludes that on the
pre-registered stopping rule the remaining shards must not start. That reading
was checked against the pre-registration before this run began rather than
accepted or ignored. Stop condition 1 fires on an ablation null or reversed
result, and what it directs is that the knowledge layer's scope claims stop
expanding and that Phase-3 work pivot to diagnosis; it does not suspend the
registered shards. The final amendment records that nothing registered changes
and that no powered arm has run, and four siblings ran after that note reached
the default branch. On that basis this run proceeded. The disagreement is real
and is left visible here rather than settled in passing.
