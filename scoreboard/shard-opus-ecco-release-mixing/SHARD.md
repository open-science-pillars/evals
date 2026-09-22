# Shard: ecco-release-mixing (claude-opus-5, N=20 per arm)

Pre-registered ablation shard, `ablation-gotcha-avoidance` manifest, run 2026-09-22.
No harness file, manifest, case, grader, threshold or trial count was modified.
Every trial and every judge call ran on `claude-opus-5`.

## Headline

| arm | passes | valid | errors | rate | Wilson 95% CI | threshold | verdict |
|---|---|---|---|---|---|---|---|
| bundle ON  | 6 | 12 | 8 | 0.500 | [0.254, 0.746] | 0.8 | FAIL |
| bundle OFF | 8 | 13 | 7 | 0.615 | [0.355, 0.823] | 0.8 | FAIL |

**Delta (on − off): −0.115.** The ablated arm scored *higher* than the arm holding
the knowledge bundle. This is counter-directional to the ablation's hypothesis and is
reported exactly as produced; nothing was adjusted.

Read it with the intervals in view: [0.254, 0.746] and [0.355, 0.823] overlap across
almost their whole length, and the two arms rest on 12 and 13 valid trials rather than
20. The point estimate is negative; the data do not separate the arms in either
direction. Treat −0.115 as "no resolvable effect at this N", not as evidence that the
bundle hurts.

## Outages

All 15 lost trials are the same failure, verbatim: `Error: Reached max turns (30)`.
No quota messages, no empty completions from any other cause.

| arm | lost | rate | trial ids |
|---|---|---|---|
| ON  | 8/20 | 0.40 | 2, 3, 6, 8, 12, 13, 14, 18 |
| OFF | 7/20 | 0.35 | 2, 5, 6, 9, 16, 18, 19 |

Difference +0.05 (ON loses more). `scoreboard.py` renders a standing explanation for
this asymmetry — that consulting the bundle costs turns, so the ON arm exhausts its
budget sooner and its survivors are the atypically brief trials. That text is generated
boilerplate, not a result computed from this shard, and a 0.40/0.35 split is thin
support for it. What this shard does establish is that both arms lost 35–40% of trials
to the turn limit, so both rates are computed on a subset selected for brevity. That
selection is the largest single caveat on the delta above.

## The decisive check

```
on arm: 20 transcripts, 2 reproduce concept prose, 24 path mentions
   trial16.txt, trial4.txt
off arm: 20 transcripts, 0 reproduce concept prose, 38 path mentions
the bundle-off arm reproduced no concept prose in 20 transcripts; its 38 path mentions are names, not reads
```

The OFF arm was genuinely off. Its 38 concept-path mentions are the skills citing paths
(the skills are not ablated) and are not a leak; zero reproduced concept prose is the
measure that matters.

## Provenance

Repository HEADs, all `main` after `fetch origin main && reset --hard origin/main`:

| repo | HEAD |
|---|---|
| evals | `cc868082d11a66aa06ef569e4513608d2b77e67f` |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` |

Capabilities at the refs the marketplace serves (not `main`), all locks current
(`osp lock --check`: PASSED, 0 stale), installed plugin versions equal to the tags,
exactly one install of each:

| capability | tag | commit | installed | lock |
|---|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77a6ada` | 0.6.0 | current |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d23ca1` | 0.9.0 | current |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef007a964` | 2026.9.5-6b0ef007a964 | current |

Runtime `claude-code` 2.1.278; judge model `claude-opus-5`; `max_turns` 30;
per-trial timeout 1200 s; concurrency 4;
ocean-science release lock `sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04`.

## Workspace hygiene

`prepare_workspace.py` held out 11 directories and certified:

> checked against the frozen fingerprints: no copy of a cited concept and no recorded
> answer to the 7 cases is readable under /home/user/run

`/home/user/src` was deleted before any trial ran, and confirmed gone.

The OFF arm extended quarantine past the workspace to the three plugin-cache
`knowledge` trees and to `transcripts_on`, and re-certified across the whole filesystem
before starting.

Every set-aside directory came back: ON put back 4, OFF put back 8. Restored concept
counts — ocean-science 45, core 12, nasa-daac-knowledge 243 — in both the plugin cache
and the run workspace; `agent-evals/ecco/cases` back to 17 entries.
`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` returns empty.

## Wall clock

| phase | start | end | elapsed |
|---|---|---|---|
| ON arm | 14:13:49Z | 14:36:42Z | ~22m53s |
| OFF arm | 14:36:42Z | 14:59:46Z | ~23m04s |
| total | 14:13:49Z | 14:59:46Z | ~45m57s |

## Note on the July pilot

This case scored 0/3 in both arms of the withdrawn July pilot, later traced to an
inverted grader. That is not what is happening here. Spot-checking the rubric output,
the grader is oriented correctly — e.g. ON trial 1, graded PASS: *"The response
identifies both V4R4 and V4R4B SSH collections, explicitly refuses to mix them because
the baseline correction would enter the trend as a step/drift, and cites the
ecco-release-mixing gotcha concept."* The rates here are real measurements.

## Files

`results_on.json`, `results_off.json`, `release-locks.json`, `ablation.html`,
`transcripts_on/` (20 trials), `transcripts_off/` (20 trials), `run.log`.
