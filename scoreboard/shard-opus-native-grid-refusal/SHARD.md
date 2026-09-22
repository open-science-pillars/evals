# Shard: native-grid-refusal, claude-opus-5, N=20 per arm

Canary attempt 4. Both arms completed; no gate refused. **The decisive check did
not come back empty, and on the pre-registered stopping rule the remaining
thirteen shards must not start.**

## Provenance

| repo | HEAD |
|---|---|
| evals | `03d42bae05a0abf24cc6b68958a8f06b8cec1a30` (#59 r7-quarantine-on-transcripts) |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` (#40 r7-fixture-leak) |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` (#89) |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` (#119 r7-prereg-leak) |

| plugin | ref served | checkout | lock | installed |
|---|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77` | current | 0.6.0 |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d` | current | 0.9.0 |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef00` | current | 2026.9.5-6b0ef007a964 |

`/home/user` was empty at start: no `evals` checkout outside `/home/user/src`.
Exactly one install of each plugin. `prepare_workspace.py` certified the
prepared tree, `/home/user/src` was deleted before the run, and both arms'
whole-filesystem leak checks passed. Model `claude-opus-5` for every trial and
every judge call; nothing in the harness, manifest, cases, graders, thresholds
or trial counts was modified.

## Results, as the run produced them

| arm | passes | valid trials | errors (outages) | rate | Wilson 95% CI |
|---|---|---|---|---|---|
| ON | 20 | 20/20 | 0 | 1.00 | [0.839, 1.000] |
| OFF | 17 | 20/20 | 0 | 0.85 | [0.640, 0.948] |

Rendered delta: **+0.15**, verdict PASS, threshold 0.8. Outages at
`max_turns: 30` were 0/20 in both arms — the previous attempt's clean ON arm is
confirmed, and the OFF arm matches it.

Wall clock: total 28m46s (04:58:06Z–05:26:52Z). ON arm 04:58:07–05:12:20
(~14m13s incl. a ~75s leak check); OFF arm 05:12:20–05:26:51 (~14m31s incl. the
second leak check). Per trial: ON min 91s / median 147s / mean 139s / max 173s;
OFF min 89s / median 140s / mean 149s / max 348s. Concurrency 4, so each arm's
~46–50 minutes of serial trial time compressed to ~14 minutes.

## The decisive check

```
$ grep -o "knowledge/podaac/[a-zA-Z0-9/_-]*\.md" transcripts_off/*/trial*.txt | sort -u
```

returned **27 citations across 16 of the 20 OFF transcripts** (trials 1, 2, 3,
5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 20), naming
`knowledge/podaac/gotchas/ecco-native-vs-regridded.md`,
`knowledge/podaac/gotchas/ecco-geothermal-flux.md` and
`knowledge/podaac/conventions/ecco-budget-formulation.md`. Trial 4 opens "I
checked the plugin's budget guidance before touching any data."

## Why: bundle-OFF does not remove this case's answer

The trials were not reading the concept files. Both leak checks passed, the
knowledge trees were demonstrably set aside (run.log), and the ON-transcript
quarantine added in #59 worked — `set aside .../transcripts_on` appears in the
OFF arm's preamble.

The answer survives **outside every knowledge tree**, in the skills tree, which
bundle-OFF does not touch. `ocean-science/0.9.0/skills/ocean-budget/SKILL.md`
carries a section headed "The native-grid rule (🔴, non-negotiable)":

> A budget request on regridded fields is REFUSED: no correct budget
> formulation exists there (gotcha ecco-native-vs-regridded, cited in the
> refusal), and the refusal always offers the native path with the exact
> collections.

The case's `concept_basis` is exactly
`knowledge/podaac/gotchas/ecco-native-vs-regridded.md`, and its pass condition
is "refusal WITH the gotcha concept cited and a constructive native-grid path
offered (collections named, snapshots for tendencies, geothermal ancillary)".
The surviving SKILL.md states the refusal, names the gotcha slug, and directs
that it be cited and the native path offered.
`skills/ecco/references/budget-formulation.md` supplies the rest: the three
gotcha paths with one-line summaries, and a procedure step naming
month-boundary snapshots for the tendency and the geometry collection for `rA`,
`drF`, `hFacC`. `agents/budget-auditor/agent.md` and
`skills/ecco/references/llc90-grid.md` cite the same path.

So the contrast this shard measured is **knowledge + skills vs. skills alone**,
not knowledge vs. no knowledge. The three OFF failures are the trials that were
scrupulous about not having read the concept: trial 15 states it has not
consulted the gotcha and defers the constructive path; trials 1 and 7 decline to
name collections they could not verify. That is the shape of a genuine
ablation — and it appeared in 3 of 20 trials rather than in all of them.

`ablation_scope.py --check` passed because every cited *concept file* is indeed
inside a removed tree; it does not look for restatements of a concept outside
one. `leak_check.py` passed because the skill text paraphrases rather than
reproduces enough verbatim concept text to match a frozen fingerprint.

This is the same class of defect as the 2026-09-21 finding recorded in
`ablate.sh`'s header, where the OFF arm had the cited knowledge in front of it
through a plugin the arm never touched. The mechanism is different — a
restatement in the skills tree rather than an untouched second plugin — but the
consequence is the same: an ON-minus-OFF number that compares knowledge against
knowledge.

## Consequence

The +0.15 delta above is reported exactly as the run produced it and should not
be read as the knowledge-layer effect for this case. Per the stopping rule, the
other thirteen shards must not start until the ablation scope question is
settled. No harness file, case, grader, threshold or trial count was edited to
accommodate this finding, and nothing was deleted to satisfy a gate.

## Restoration

All four workspace trees and all three installed knowledge trees came back, as
did `transcripts_on`:

| tree | files |
|---|---|
| `run/agent-evals/ecco/cases` | 17 |
| `run/ocean-science/knowledge` | 84 |
| `run/core/knowledge` | 12 |
| `run/nasa-daac-knowledge/knowledge` | 243 |
| cache `core/0.6.0/knowledge` | 12 |
| cache `nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge` | 243 |
| cache `ocean-science/0.9.0/knowledge` | 84 |
| `transcripts_on` | 60 |
| `transcripts_off` | 60 |

`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` is empty.
