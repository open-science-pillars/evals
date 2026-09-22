# Shard: `swot-calval-window` — claude-opus-5, N=20 per arm

Pre-registered ablation shard, run 2026-09-22. Harness, manifest, case, grader,
threshold and trial count unmodified; every trial and every judge call ran on
`claude-opus-5`.

## Container state at start

`/home/user` was empty. No `evals` checkout existed anywhere outside
`/home/user/src`, and no `ablate.sh` / `run_evals` process was running.

## HEADs (all four repos at `origin/main`)

| repo | HEAD | subject |
| --- | --- | --- |
| evals | `cc868082d11a66aa06ef569e4513608d2b77e67f` | Merge pull request #60 from open-science-pillars/r7-transcript-audit |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` | Merge pull request #40 from open-science-pillars/r7-fixture-leak |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` | Merge pull request #89 from open-science-pillars/claude/whats-new-xpj969 |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` | Merge pull request #119 from open-science-pillars/r7-prereg-leak |

All five required runner files were present in `evals`: `runner/leak_check.py`,
`runner/prepare_workspace.py`, `runner/released_refs.py`,
`runner/transcript_audit.py`, `runner/concept-fingerprints.json`.

## Capability refs and lock checks

Refs resolved by `runner/released_refs.py` against the marketplace (not `main`);
its printed clone commands were run verbatim.

| capability | released ref | commit | `osp lock --check` |
| --- | --- | --- | --- |
| core | `core--v0.6.0` | `dfd4e77a6adaf1617d9a62f562c5b8c8e13f5f30` | release lock current — PASSED (0 stale) |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d23ca11db8b17d1f8cf40c2e16567010a6` | release lock current — PASSED (0 stale) |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef007a964f3cce7d7a1d0b6f8cfe61df41143` | release lock current — PASSED (0 stale) |

`ablate.sh` independently re-checked all three locks at run time
(`release-locks.json`: all `current`).

## Installed plugin versions match the tags

`claude plugin install ocean-science@open-science-pillars` pulled two
dependencies. Exactly one install of each plugin:

| plugin | installed version | tag |
| --- | --- | --- |
| core | `0.6.0` | `core--v0.6.0` |
| ocean-science | `0.9.0` | `ocean-science--v0.9.0` |
| nasa-daac-knowledge | `2026.9.5-6b0ef007a964` | `nasa-daac-knowledge--v2026.9.5` @ `6b0ef007a964` |

Three knowledge trees in the plugin cache, one per plugin.

## Workspace preparation

`runner/prepare_workspace.py /home/user/src /home/user/run` excluded 11
directories (the six `.git` dirs, `agent-evals/ecco/results`,
`agent-evals/ecco/fixtures/grader-calibration`, `evals/scoreboard`,
`evals/runner/fixtures/transcripts`) and certified:

> checked against the frozen fingerprints: no copy of a cited concept and no recorded answer to the 7 cases is readable under /home/user/run

`/home/user/src` was then deleted and confirmed gone before the run started.

## Results

Threshold 0.8. Rates are over valid trials; lost trials are excluded from the
rates. `max_turns` 30 in both arms; timeout 1200s; judge `claude-opus-5`.

| arm | passes | valid | errors | rate | Wilson 95% CI | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| bundle ON | 6 | 17 | 3 | 0.353 | [0.173, 0.587] | FAIL |
| bundle OFF | 3 | 15 | 5 | 0.200 | [0.070, 0.452] | FAIL |

**Delta: +0.153** (as produced by `scoreboard.py`).

### Outages at `max_turns` 30

| arm | lost | trials |
| --- | --- | --- |
| ON | 3/20 (0.15) | 7, 16, 20 |
| OFF | 5/20 (0.25) | 4, 5, 14, 19, 20 |

Every lost trial is an `empty or limit message` record of 29 chars.
Difference -0.1. The scoreboard flags this itself:

> The arms did not lose trials at the same rate. A pooled risk difference across arms whose samples were thinned unequally is not read as a treatment effect without saying so.

Note the direction: the scoreboard's stated rationale for unequal attrition is
that "consulting the bundle costs turns, so the arm holding the knowledge
exhausts its budget more readily." Here the **off** arm lost more trials than
the on arm (5 vs 3), which is the opposite of that prediction. Recorded as
observed; nothing was adjusted.

### Wall clock

| arm | start | end | elapsed |
| --- | --- | --- | --- |
| ON | 14:13:03Z | 14:28:05Z | ~15m 02s |
| OFF | 14:28:05Z | 14:44:33Z | ~16m 28s |
| total | ~14:12:55Z | 14:44:33Z | ~31m 40s |

Both arms ran substantially faster than the ~1h/arm the recipe anticipated.
Trial elapsed times (117–232s, concurrency 4, 20 trials) account for this; no
step was skipped and both whole-filesystem leak checks ran.

## Transcript audit (the decisive check)

```
on arm: 20 transcripts, 0 reproduce concept prose, 46 path mentions
off arm: 20 transcripts, 0 reproduce concept prose, 44 path mentions
the bundle-off arm reproduced no concept prose in 20 transcripts; its 44 path mentions are names, not reads
```

The off arm was genuinely off: zero reproduced concept prose. The 44 path
mentions are expected — the skills cite concept paths and are not ablated.

Worth flagging for the analysis, not acted on here: the **on** arm also
reproduced zero concept prose. Its six passes do surface concept-specific
detail (cycles 475–578, restart at 001, the `..._D` collection family), so the
knowledge was reachable; but several on-arm rubric failures read as the agent
deferring to knowledge it never opened. Whether that is paraphrase escaping the
audit's prose detector or genuine under-consultation is a question for the
analysis, and it bears directly on how small the +0.153 delta is.

## Set-aside restoration

`ablate.sh` reported `put back 4 directories` (ON) and `put back 8 directories`
(OFF). Confirmed clean:

```
find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE' 2>/dev/null
```

returned nothing.

## Artifacts in this commit

`results_on.json`, `results_off.json`, `release-locks.json`, `ablation.html`,
`transcripts_on/` and `transcripts_off/` (20 trials x `.json`/`.txt`/`.stderr`
each), `run.log`, and this file. The transcript trees are force-added past
`.gitignore` because the analysis commitments require them.
