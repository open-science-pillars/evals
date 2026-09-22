# Shard: opus / swot-crossover-unapplied

Pre-registered ablation shard. Model `claude-opus-5` (trials and judge), case
`swot-crossover-unapplied`, N=20 per arm, `--concurrency 4`.

No harness file, manifest, case, grader, threshold or trial count was changed.
No model was substituted. All numbers below are reported as produced.

## Headline

| arm | passes | valid | errors | rate | Wilson 95% CI | threshold | verdict |
|---|---|---|---|---|---|---|---|
| bundle ON  | 6 | 19 | 1 | 0.316 | [0.154, 0.540] | 0.8 | FAIL |
| bundle OFF | 2 | 17 | 3 | 0.118 | [0.033, 0.343] | 0.8 | FAIL |

Rendered delta (`ablation.html`): **+0.198**.

Both arms fall below the 0.8 threshold, so the case verdict is FAIL in both.
The delta is the ablation signal; the verdict is not.

## Outage caveat (from the harness's own rendering)

    on lost 1 of 20 (0.05); off lost 3 of 20 (0.15); difference -0.1.
    The arms did not lose trials at the same rate. A pooled risk difference
    across arms whose samples were thinned unequally is not read as a
    treatment effect without saying so.

All four outages were `empty or limit message` (29-char transcripts) at
`max_turns 30`: ON trial 9; OFF trials 9, 11, 19. Lost trials are excluded from
both rates.

## The decisive check

`transcript_audit.py`, verbatim:

    on arm: 20 transcripts, 0 reproduce concept prose, 31 path mentions
    off arm: 20 transcripts, 0 reproduce concept prose, 29 path mentions
    the bundle-off arm reproduced no concept prose in 20 transcripts; its 29 path mentions are names, not reads

The OFF arm reproduced no concept prose. Path mentions are expected — the
skills cite concept paths and are not ablated — and are not a leak.

## Provenance

Repository HEADs at run time (all reset to `origin/main`):

| repo | HEAD |
|---|---|
| evals | `cc868082d11a66aa06ef569e4513608d2b77e67f` (Merge PR #60, r7-transcript-audit) |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` (Merge PR #40, r7-fixture-leak) |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` (Merge PR #89) |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` (Merge PR #119, r7-prereg-leak) |

This branch is based on evals `9247c0252a0bb9e7e71b3fb0887ddf9831ddd89a`
(Merge PR #61), which landed on main after this run started. The run itself was
executed at `cc868082`.

Capabilities at the refs the marketplace serves (not main), with lock checks:

| capability | tag | commit | lock |
|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77a6ada` | current, PASSED (0 stale) |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d23ca1` | current, PASSED (0 stale) |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef007a964` | current, PASSED (0 stale) |

Installed plugin versions equal the tags: core `0.6.0`, ocean-science `0.9.0`,
nasa-daac-knowledge `2026.9.5-6b0ef007a964`. Exactly one install of each.

Runtime: claude-code 2.1.278. Judge: `claude-opus-5`.
ocean-science release lock `sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04`.

`prepare_workspace.py` certified the prepared tree:

    checked against the frozen fingerprints: no copy of a cited concept and no
    recorded answer to the 7 cases is readable under /home/user/run

`/home/user/src` was then deleted and confirmed gone. Both arms' whole-filesystem
leak checks passed (`...is readable under /`).

## Wall clock

| arm | start | end | elapsed |
|---|---|---|---|
| bundle ON  | 15:07:42Z | 15:24:20Z | 16m 38s |
| bundle OFF | 15:24:20Z | 15:41:24Z | 17m 04s |

Total 33m 44s. Sum of per-trial elapsed: ON 3352 s, OFF 3363 s.

## Set-aside directories

The ON arm sets aside 4 trees; the OFF arm sets aside 8 (adding the three
installed plugin-cache knowledge trees and `transcripts_on`). The final log line
reads `put back 8 directories`, and all were verified present afterwards:

| tree | concepts |
|---|---|
| `run/ocean-science/knowledge` | 45 |
| `run/core/knowledge` | 12 |
| `run/nasa-daac-knowledge/knowledge` | 243 |
| `run/agent-evals/ecco/cases` | 17 files |
| plugin cache `ocean-science/0.9.0/knowledge` | 45 |
| plugin cache `core/0.6.0/knowledge` | 12 |
| plugin cache `nasa-daac-knowledge/2026.9.5-.../knowledge` | 243 |

`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` is empty.

**That find is not a sufficient check for this harness.** `run_evals.py` no longer
renames trees to marker-suffixed paths; it tars each one into a `mkdtemp`
holding directory and deletes the original. A run killed by a signal therefore
leaves the workspace with trees missing and the marker find still empty. The
direct per-tree counts above are the check that actually discriminates.

## Two lost runs before this one

This shard was launched three times. The first two died when the session
container was reclaimed while the run was detached and the session was idle:

| run | launched | died | reached |
|---|---|---|---|
| 1 | 14:13:56Z | 14:19:47Z | ON trial 6 of 20 |
| 2 | 14:51:48Z | 14:58:13Z | ON trial 7 of 20 |
| 3 | 15:07:41Z | completed | both arms |

Cause, from `/tmp/env-manager.log`:

    {"message":"Sending SIGTERM to Claude Code for graceful shutdown","time":"2026-09-22T14:19:48.796585160Z"}
    {"message":"Sending SIGTERM to Claude Code for graceful shutdown","time":"2026-09-22T14:58:18.935849106Z"}

Measured idle window between a turn ending and reclamation: **3.7 to 5.3
minutes**. A 10-minute keepalive poll cannot bridge it; run 3 used a 2-minute
poll and survived. `setsid nohup` does not protect against this — the whole
microVM goes away, PIDs reset, and neither `atexit` nor the `EXIT`/`INT`/`TERM`
traps run.

After each death the quarantined trees were restored from the run's holding
directory and verified before relaunch (18/95/16/281 archive members;
45/12/243 concepts). No trials were carried across runs — each relaunch began
with an empty scoreboard directory. An arm here is twenty trials from one run.

## Disclosures

1. **Dead-run transcripts remained on disk during the successful run.** The two
   dead runs' partial outputs were moved to `/home/user/dead-run-1419/` and
   `/home/user/dead-run-1458/` rather than deleted, because `rm -rf` was refused
   by the environment's permission classifier (`Irreversible Local Destruction`).
   Those directories hold ON-arm transcripts and sat outside the OFF arm's
   quarantine set. The OFF arm's whole-filesystem leak check passed with them
   present, and the transcript audit found zero reproduced concept prose, so
   there is no evidence of contamination — but the containment was weaker than
   the harness intends, and the audit rather than the quarantine is what
   establishes the OFF arm was off. The stale holding directories
   `/tmp/osp-quarantine-8yftk6bg` and `/tmp/osp-quarantine-iushgicm` also remain
   for the same reason; run 3's own holding directory was cleaned up normally.

2. **ON trial 20's judge reply was truncated** and its grade carries
   `[salvaged from a truncated judge reply]` with `salvaged: true`. It was
   counted as a FAIL. Not adjusted.

3. **ON trials 2 and 10 received rubric `PASS` but scored `pass: False`**,
   because the programmatic grader returned False and the graders conjoin.
   Reported as produced.
