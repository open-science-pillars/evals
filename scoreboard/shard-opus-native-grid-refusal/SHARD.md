# Shard: opus / native-grid-refusal — ABORTED BY A GATE (canary outcome)

Model `claude-opus-5`, case `native-grid-refusal`, N=20 per arm, concurrency 4.
Date 2026-09-22.

**Outcome: the bundle-OFF arm refused to start. No OFF trial ran. There is no
delta. The other thirteen shards must not start until this is fixed.**

## 1. Container and setup

`/home/user` was empty before setup; no `evals` checkout existed anywhere.

Harness HEADs (default branch, after `git fetch origin main && git reset --hard origin/main`):

| repo | HEAD | commit |
|---|---|---|
| evals | f0083d740f9896818c9e1381abac2b7e40237bfb | Merge PR #58 r7-released-refs |
| agent-evals | 4f5bad808c21bbd41cf7233365d33bdd466b2f8a | Merge PR #40 r7-fixture-leak |
| build-kit | b0866fd1ab1c21c58fb04c4087db85728ac16300 | Merge PR #89 claude/whats-new-xpj969 |
| marketplace | 46eba25fc4d5fdd07dc54b4ac8f2f6dbef3bc6ac | Merge PR #119 r7-prereg-leak |

All four required runner files present (`leak_check.py`, `prepare_workspace.py`,
`released_refs.py`, `concept-fingerprints.json`).

Released refs, and the checkouts confirmed sitting on them (detached HEAD at the
tag; `git describe --tags --exact-match` agrees; no branch substituted):

| plugin | ref | HEAD sha |
|---|---|---|
| core | core--v0.6.0 | dfd4e77a6adaf1617d9a62f562c5b8c8e13f5f30 |
| ocean-science | ocean-science--v0.9.0 | b923b1d23ca11db8b17d1f8cf40c2e16567010a6 |
| nasa-daac-knowledge | nasa-daac-knowledge--v2026.9.5 | 6b0ef007a964f3cce7d7a1d0b6f8cfe61df41143 |

Lock checks before install — all three `release lock current`, `PASSED (0 stale)`.

Install: one install of each plugin, marketplace directory `open-science-pillars`.
Installed versions equal the checked-out tags:

- core 0.6.0
- ocean-science 0.9.0
- nasa-daac-knowledge 2026.9.5-6b0ef007a964  (suffix = the tag's HEAD sha)

Knowledge trees:

```
/root/.claude/plugins/cache/open-science-pillars/core/0.6.0/knowledge
/root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge
/root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
```

## 2. prepare_workspace.py (verbatim)

```
prepared /home/user/run from /home/user/src, without 11 directories:
  build-kit/.git
  ocean-science/.git
  nasa-daac-knowledge/.git
  marketplace/.git
  agent-evals/.git
  agent-evals/ecco/results
  agent-evals/ecco/fixtures/grader-calibration
  evals/.git
  evals/scoreboard
  evals/runner/fixtures/transcripts
  core/.git

certifying the prepared tree:
checked against the frozen fingerprints: no copy of a cited concept and no recorded answer to the 7 cases is readable under /home/user/run
```

It certified. `/home/user/src` was then deleted and confirmed gone.

## 3. Result per arm

| arm | passes | valid trials | errors | rate | CI95 | outages (`Reached max turns (30)`) |
|---|---|---|---|---|---|---|
| bundle-ON | 20 | 20 | 0 | 1.0 | [0.839, 1.0] | 0 |
| bundle-OFF | — | **0 — arm never started** | — | — | — | n/a |

Threshold 0.8; ON arm verdict PASS. **Rendered delta: none — `ablation.html` was
never produced, and `results_off.json` does not exist.**

No transcript in the ON arm contains `Reached max turns`; the ON arm lost nothing
to outage. The OFF arm's outage count is not "zero", it is undefined: no trial ran.

## 4. Why the OFF arm refused

Verbatim from the run log:

```
ERROR: the bundle-off arm can still read the knowledge it is supposed to have removed:
  native-grid-refusal: nasa-daac-knowledge/knowledge/podaac/gotchas/ecco-native-vs-regridded.md is readable at .../transcripts_on/native-grid-refusal/trial1.txt
  native-grid-refusal: nasa-daac-knowledge/knowledge/podaac/gotchas/ecco-native-vs-regridded.md is readable at .../transcripts_on/native-grid-refusal/trial18.txt
  native-grid-refusal: nasa-daac-knowledge/knowledge/podaac/gotchas/ecco-native-vs-regridded.md is readable at .../transcripts_on/native-grid-refusal/trial7.txt
the trials would read what this run is supposed to have taken away, so no trial is run
put back 7 directories
ERROR: the bundle-OFF arm failed
```

The gate is correct and the leak is real. The mechanism:

1. `ablate.sh` runs the ON arm first and is required by the pre-registration to
   keep its transcripts, under `<out_dir>/transcripts_on`.
2. `<out_dir>` for this shard is `/home/user/run/evals/scoreboard/...`, i.e.
   **inside the workspace the leak check scans**.
3. ON-arm trials read the concept and some of them quote it. Three of twenty
   reproduced >=14 consecutive words of `ecco-native-vs-regridded.md` verbatim.
4. `leak_check.py` matches salted 14-word blake2b shingles over whitespace-
   normalised text, so those three transcripts are literally a readable copy of
   the concept.
5. The OFF arm's pre-flight therefore finds cited-concept text on disk and,
   correctly, refuses to run.

This was verified independently rather than assumed: recomputing
`blake2b(salt + 14-word window, digest_size=16)` over all twenty ON transcripts
reproduces the harness's finding exactly — trials 1, 7 and 18 and no others
(trial1 2/3 fingerprints, trial7 2/3, trial18 1/3).

Note that 20/20 ON transcripts cite the concept *by path*; only 3 trip the gate,
because the gate matches prose, not paths. Path citation is not the trigger.

### Why this is a harness defect and not a setup error

The collision is structural and order-dependent, not specific to this shard:

- ON always runs before OFF.
- ON transcripts must be kept (`ablate.sh` fails the run if they are not).
- The transcripts land inside the tree the OFF leak check scans.
- Whether the gate fires is left to chance: it depends on whether any ON trial
  happened to quote >=14 consecutive words of a cited concept. Here 3 of 20 did.

So on any given shard this either aborts the OFF arm (visible, what happened
here) or does not fire (invisible). **It cannot produce a wrong number silently
— the gate is sound — but it makes completion of any shard a coin flip.** All
fourteen shards are exposed.

The fix belongs upstream and is a design decision I did not make: the output
directory must sit outside the scanned roots, or the leak check must exclude the
current run's own `transcripts_on`, or the ON arm's transcripts must be held
outside the workspace until both arms are done. I did not implement any of
these, and I did not delete or edit anything to satisfy the gate.

## 5. The decisive check (item 6)

```
$ grep -o "knowledge/podaac/[a-zA-Z0-9/_-]*\.md" transcripts_off/*/trial*.txt | sort -u
grep: transcripts_off/*/trial*.txt: No such file or directory
```

`transcripts_off/` does not exist. No OFF trial ran, so there is no OFF
transcript to quote an opening line from, and the question of whether an OFF
trial consulted the knowledge is **unanswered, not answered negatively**.

## 6. Wall clock

ON arm, 20 trials at concurrency 4:

- min 125 s, median 154.5 s, mean 175.2 s, max 333 s
- sum of trial time (serial-equivalent) 3505 s = 58.4 min
- ON arm wall clock ~17.5 min (04:18:00 -> 04:35:28), speedup ~3.3x on 4 workers

Projection for a full two-arm shard: ~35 min wall clock, ~2 h of model time.
Fourteen shards: ~8 h wall clock at this concurrency. `--concurrency 4` ran
cleanly — no errors, no interleaved or corrupted log lines, trials completed
out of order as expected for a worker pool. It did not need to be re-run
serially.

## 7. Restore

All seven set-aside directories are back:

| directory | files |
|---|---|
| /home/user/run/ocean-science/knowledge | 84 |
| /home/user/run/core/knowledge | 12 |
| /home/user/run/nasa-daac-knowledge/knowledge | 243 |
| .../cache/open-science-pillars/ocean-science/0.9.0/knowledge | 84 |
| .../cache/open-science-pillars/core/0.6.0/knowledge | 12 |
| .../cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge | 243 |
| /home/user/run/agent-evals/ecco/cases | 17 |

`find / -name '*.ABLATION_OFF' -o -name '*.QUARANTINE'` returns nothing, and no
holding directory is left under the system temp directory.

## 8. Status

Canary failed in the way a canary is supposed to fail: a gate caught a real leak
and refused rather than publishing a contaminated delta. Nothing was edited or
deleted to get past it. The remaining thirteen shards should not start.
