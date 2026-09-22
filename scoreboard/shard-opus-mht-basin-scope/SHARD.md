# Shard: mht-basin-scope, claude-opus-5, N=20 per arm

Both arms completed; no gate refused. The decisive check came back empty: the
bundle-OFF arm reproduced **no** concept prose in any of its twenty
transcripts. Its 41 path mentions are names, not reads, which the case's skills
produce whether or not the knowledge is present.

This shard was run twice. The first attempt died mid-ON-arm when the container
was reclaimed; its partial data was discarded and nothing from it appears here.
See "First attempt" below.

## Provenance

| repo | HEAD |
|---|---|
| evals | `cc868082d11a66aa06ef569e4513608d2b77e67f` (#60 r7-transcript-audit) |
| agent-evals | `4f5bad808c21bbd41cf7233365d33bdd466b2f8a` (#40 r7-fixture-leak) |
| build-kit | `b0866fd1ab1c21c58fb04c4087db85728ac16300` (#89) |
| marketplace | `46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac` (#119 r7-prereg-leak) |

`main` advanced to `9247c02` (#61, shard-opus-native-grid-refusal) while this
shard was in flight. `git diff cc86808 9247c02 -- runner/ manifests/` is empty,
so this run used the same harness as current main; the only difference between
the two HEADs is that sibling's scoreboard artifacts.

| plugin | ref served | checkout | lock | installed |
|---|---|---|---|---|
| core | `core--v0.6.0` | `dfd4e77` | current | 0.6.0 |
| ocean-science | `ocean-science--v0.9.0` | `b923b1d` | current | 0.9.0 |
| nasa-daac-knowledge | `nasa-daac-knowledge--v2026.9.5` | `6b0ef00` | current | 2026.9.5-6b0ef007a964 |

`/home/user` was empty at start: no `evals` checkout outside `/home/user/src`.
Exactly one install of each plugin, each version equal to the tag the
marketplace serves. `prepare_workspace.py` certified the prepared tree ("no
copy of a cited concept and no recorded answer to the 7 cases is readable under
/home/user/run"), `/home/user/src` was deleted before the run, and both arms'
whole-filesystem leak checks passed. Model `claude-opus-5` for every trial and
every judge call; nothing in the harness, manifest, cases, graders, thresholds
or trial counts was modified.

## Results, as the run produced them

| arm | passes | valid trials | errors (outages) | rate | Wilson 95% CI |
|---|---|---|---|---|---|
| ON | 8 | 19/20 | 1 | 0.421 | [0.231, 0.637] |
| OFF | 0 | 20/20 | 0 | 0.0 | [0.0, 0.161] |

Rendered delta: **+0.421**. Both arms are scored FAIL against the threshold —
the ON arm's point estimate does not reach it — so the delta is large while the
capability itself does not clear the bar on this case.

Outages at `max_turns: 30`: ON 1/20 (0.05), OFF 0/20 (0.0), difference +0.05.
The single lost trial is ON trial 9, whose transcript is exactly
`Error: Reached max turns (30)` (29 chars). It is not counted as a failure and
is in no rate above. This is the direction the scoreboard's outage note
predicts: the arm holding the knowledge spends turns consulting it.

Wall clock: total 42m40s (14:49:44Z–15:32:24Z). ON arm 14:49:47–15:12:00
(~22m14s incl. a ~75s leak check); OFF arm 15:12:00–15:32:24 (~20m24s incl. the
second leak check). Per trial: ON min 109s / median 223s / mean 233s / max 620s
over the 19 scored; OFF min 96s / median 162s / mean 219s / max 394s.
Concurrency 4, so each arm's ~73–74 minutes of serial trial time compressed to
~20 minutes.

## The decisive check

```
$ uv run --with pyyaml==6.0.2 runner/transcript_audit.py \
    scoreboard/shard-opus-mht-basin-scope --case mht-basin-scope
on arm: 20 transcripts, 0 reproduce concept prose, 45 path mentions
off arm: 20 transcripts, 0 reproduce concept prose, 41 path mentions
the bundle-off arm reproduced no concept prose in 20 transcripts; its 41 path
mentions are names, not reads
```

Zero reproduced prose in the off arm: the arm was off. Path mentions in the off
arm are expected and are not a leak — the skills cite concept paths and are not
ablated — so the 41 mentions do not qualify this result. Contrast the
native-grid-refusal shard, where the off arm's transcripts carried the cited
concepts' substance and the ablation was not actually off.

## First attempt (discarded)

Launched 14:13:59Z. The ON arm completed four trials, then at 14:17:36Z the
container was stopped:

```
14:17:36.681  "Sending SIGTERM to Claude Code for graceful shutdown"  grace_period_seconds=5
14:17:36.894  "Claude Code stopped due to context cancellation"       process_err="exit status 143"
14:40:33.021  "Set session mode for environment"  session_mode="resume"
```

That is ~3.4 minutes after the driving session ended its turn, as the recipe
directs. The VM was suspended with it, so `run_evals.py`'s SIGTERM handler never
ran and `put_back()` never restored the trees: the workspace was left with its
cases and all three knowledge trees set aside — the state `ablate.sh` calls
"worse than a failed run".

The runner's holding directory survived at `/tmp/osp-quarantine-s4rf6toy` with
all four archives intact. They were restored by replicating `put_back()`
exactly (`tarfile.extractall(path.parent, filter="data")`), and the restored
trees verified **byte-identical** (`diff -rq`, no differences) to the released
installed trees: 45 / 12 / 243 concepts and 17 case files. The four partial
trials and the stale holding directory were then deleted, and the shard was
restarted clean. No trial from the first attempt is stitched into the arms
above; an arm here is twenty trials.

**Operational finding for the remaining shards:** a detached run does not
survive container idle on this host. The reclaim was measured at ~3.4 minutes,
so a 10-minute check-back is not sufficient either; this run was kept alive with
a 2-minute poll for its full 43 minutes.
