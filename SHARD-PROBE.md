# Shard probe: can one shard of the pre-registered ablation run end to end?

Branch `claude/ablation-probe`. Container: Claude Code on the web, Linux 6.18.44.
Probe date 2026-09-21. Model pinned to `claude-opus-5` throughout; no substitution
was made at any point.

The run is **complete**: `ABLATION_DONE`, exit 0, 12 m 55.9 s wall clock for four
trials. An earlier commit on this branch pushed this file partial, mid-OFF-arm, on
request; this is the final version. Two numbers from that partial version were wrong
and are corrected here — see "Corrections" at the end.

## Bottom line

A shard runs end to end: setup, both arms, the arm change, transcripts, the outage
guard and the delta scoreboard all work, and a backgrounded run survives the agent's
turn ending. Two things break.

1. **The shard command as written cannot run.** `--concurrency` does not exist.
2. **The bundle-OFF arm does not ablate `grace-leakage`.** The case's ground truth
   lives in a bundle neither arm touches, so the shard's headline result — a delta of
   **+0.0**, 1.00 against 1.00 — is not a null. It is a measurement of nothing.

"What breaks" is the part of this document worth your time.

---

## 1. Setup, step by step

| # | Step | Result |
|---|---|---|
| 1 | Workspace with six repos side by side | worked |
| 2a | `claude plugin marketplace add open-science-pillars/marketplace` | worked |
| 2b | `claude plugin install ocean-science@open-science-pillars` | worked |
| 2c | `claude plugin list` | worked |
| 2d | knowledge tree present, ~45 concepts | worked, exactly 45 |
| 3 | headless `claude -p` on `claude-opus-5` | worked, 5.4 s |

No setup step failed, so there is no setup error to report.

### 1.1 Workspace

Workspace root is `/home/user`, the parent of the pre-existing `evals` checkout.
All six repositories cloned over HTTPS without error (`--depth 50`):

| Repo | HEAD |
|---|---|
| evals | 5533f05 |
| agent-evals | 248394d |
| ocean-science | 4326f3f |
| core | c2cbe0f |
| nasa-daac-knowledge | c04ae2e |
| build-kit | b0866fd |

### 1.2 The installed capability

`claude plugin install` pulled the capability and its two declared dependencies:

```
Installed plugins:

  > core@open-science-pillars
    Version: 0.6.0
    Scope: user
    Status: enabled

  > nasa-daac-knowledge@open-science-pillars
    Version: 2026.9.5-6b0ef007a964
    Scope: user
    Status: enabled

  > ocean-science@open-science-pillars
    Version: 0.9.0
    Scope: user
    Status: enabled
```

- **ocean-science version installed: `0.9.0`**
- **Marketplace directory name it landed under: `open-science-pillars`**

Full path of the knowledge tree, which is what `ablate.sh` globs for:

```
/root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
```

Exactly one match, so `ablate.sh`'s more-than-one-marketplace guard was not
triggered. The tree holds **45 markdown concepts**, matching the expected count.

Note the marketplace directory is `open-science-pillars` — the same name the script's
own comment says it used to pin and then abandoned. The current find-don't-pin glob
resolved correctly here, but be aware a release-candidate install under a different
marketplace name would land elsewhere and this probe does not exercise that path.

### 1.3 Headless call

```
$ claude -p "Reply with exactly: OK" --model claude-opus-5 --max-turns 2
OK

real	0m5.433s
```

Exit code 0.

---

## 2. What breaks

### 2.1 The shard command fails immediately: `--concurrency` does not exist

The command as specified:

```
bash <workspace>/evals/runner/ablate.sh <workspace> 2 <outdir> claude-opus-5 --cases grace-leakage --concurrency 2
```

fails in **0.115 seconds**, both arms, with exit 1. Verbatim:

```
== bundle-ON arm ==
usage: run_evals.py [-h] --manifest MANIFEST --workspace WORKSPACE
                    [--trials TRIALS] [--model MODEL] [--cases CASES]
                    [--out OUT] [--timeout TIMEOUT]
                    [--transcripts TRANSCRIPTS] [--bundle {on,off}]
                    [--no-judge] [--claude-arg CLAUDE_ARG]
                    [--runtime {claude-code,claude-cowork,claude-science,gemini-cli,goose,openai-codex}]
                    [--runtime-version RUNTIME_VERSION]
                    [--judge-model JUDGE_MODEL] [--no-lock-check]
run_evals.py: error: unrecognized arguments: --concurrency 2
== stripping knowledge/ for the bundle-OFF arm ==
ablating /root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
== bundle-OFF arm ==
usage: run_evals.py [-h] --manifest MANIFEST --workspace WORKSPACE
                    [--trials TRIALS] [--model MODEL] [--cases CASES]
                    [--out OUT] [--timeout TIMEOUT]
                    [--transcripts TRANSCRIPTS] [--bundle {on,off}]
                    [--no-judge] [--claude-arg CLAUDE_ARG]
                    [--runtime {claude-code,claude-cowork,claude-science,gemini-cli,goose,openai-codex}]
                    [--runtime-version RUNTIME_VERSION]
                    [--judge-model JUDGE_MODEL] [--no-lock-check]
run_evals.py: error: unrecognized arguments: --concurrency 2
restored knowledge/
ERROR: the on arm kept no transcripts under /home/user/probe/exact/transcripts_on; the analysis commitments require them
```

(kept at `scoreboard/probe/run-exact-command.log`)

There is no concurrency support anywhere in the runner:

```
$ grep -rn "concurrency\|ThreadPool\|concurrent.futures\|max_workers" runner/
(no matches)
```

`run_evals.py` runs trials in a plain sequential `for n in range(1, args.trials + 1)`
loop. **Trials cannot be parallelised today, and the 14-shard plan should not assume
they can.** `ablate.sh` forwards its trailing arguments to `run_evals.py` verbatim
via `EXTRA`, so any unknown flag dies the same way.

### 2.2 `ablate.sh` does not stop when an arm fails

`ablate.sh` line 22 is `set -uo pipefail` — **without `-e`**. The failed ON arm above
did not stop the script. It went on to move the knowledge tree aside, run the OFF arm
(which failed identically), and only caught the problem at the transcripts guard at
the very end.

The `trap restore EXIT INT TERM` did fire correctly — `restored knowledge/` is in the
output and no `knowledge.ABLATION_OFF` was left behind. So the failure is contained.
But a run whose ON arm dies still performs the arm change and still consumes the OFF
arm, which for a real shard means burning the full OFF budget for nothing. Worth an
`|| exit 1` on both `run_evals.py` calls.

### 2.3 The bundle-OFF arm does not ablate this case — this is the serious one

`grace-leakage` declares:

```yaml
targets: []  # no ocean-science skill; the case rests on the concepts alone
concept_basis:  # nasa-daac-knowledge @ 9224fe5a83e4
  - knowledge/podaac/gotchas/grace-coastal-leakage.md
  - knowledge/podaac/datasets/grace-fo-mascons.md
```

Both of those files live in the **nasa-daac-knowledge** plugin, not in ocean-science:

```
knowledge/podaac/gotchas/grace-coastal-leakage.md
  -> /root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/
knowledge/podaac/datasets/grace-fo-mascons.md
  -> /root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/
```

`ablate.sh` moves aside only `.../ocean-science/*/knowledge`. The ocean-science tree
contains **no grace, podaac or mascon file at all** (checked by name across all 45).
The nasa-daac-knowledge cache — 252 markdown files, including both concepts above —
is never touched by either arm.

This is not a prediction. The bundle-OFF transcript for trial 1 cites both files by
path and passes:

```
$ grep -o "knowledge/podaac/[a-z/-]*\.md" transcripts_off/grace-leakage/trial1.txt | sort -u
knowledge/podaac/datasets/grace-fo-mascons.md
knowledge/podaac/gotchas/grace-coastal-leakage.md
```

Opening line of that OFF-arm transcript: *"I read the bundle concepts before touching
data, and they stop this computation as specified."*

**For `grace-leakage`, bundle-OFF is not off.** The arm removes a tree the case does
not depend on and leaves the tree it does depend on in place. Any ON-vs-OFF delta this
case produces measures nothing about the knowledge bundle. Since the manifest's seven
cases all carry `plugin: ocean-science`, the same question should be asked of each
before the full experiment runs: how many of them have a `concept_basis` that is
actually inside the ocean-science tree?

I have not changed the harness, the manifest or the case. Reporting only.

### 2.4 The named rubric file does not exist; the judge silently falls back

The case asks for `rubric: leakage-handling.md`. `run_evals.py` resolves that at
`<workspace>/<plugin>/evals/<spec>`, i.e.
`/home/user/ocean-science/evals/leakage-handling.md`.

There is no `evals/` directory in the ocean-science checkout, and no file named
`leakage-handling*` anywhere in the workspace. The lookup misses and the code falls
through to the documented default — the case's own `notes` field becomes the rubric.

That fallback is intentional and `notes` here is substantive, so grading still
happened and the judge produced a detailed verdict. But a case that names a dedicated
rubric and silently gets the fallback is not obviously the pre-registered grader. No
warning is printed and nothing in the results file records which rubric was used.

### 2.5 Dead code worth knowing about

`read_dirs_for()` in `run_evals.py` (lines 69-87) is defined and never called:

```
$ grep -n "read_dirs_for" runner/*.py
runner/run_evals.py:69:def read_dirs_for(ws, plugin: str):
```

Its docstring describes opening a plugin's dependency bundles to its trials, which is
precisely the concern in 2.3. It does nothing. Trials read the installed plugin cache,
which is why the cache-level arm change works at all — but also why the untouched
nasa-daac-knowledge cache stays readable in the OFF arm.

(It also would not work as written: it reads `.claude-plugin/plugin.json`, but the
ocean-science checkout carries `plugin.json` at its root, and it calls `dep.get(...)`
on a dependency list whose first entry is the bare string `"core"`.)

---

## 3. The run

Because the specified command cannot execute, the shard was run again with **only the
unsupported `--concurrency 2` removed**. Model, trial count, case and output paths are
unchanged; no number and no eval case was altered.

```
bash /home/user/evals/runner/ablate.sh /home/user 2 /home/user/probe/shard claude-opus-5 --cases grace-leakage
```

### 3.1 Output, verbatim

Complete run log, exactly as written:

```
== bundle-ON arm ==
ocean-science 0.9.0: sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04 (current) on claude-code (2.1.278 (Claude Code))
  grace-leakage trial 1: PASS (227s, 5290 chars)
  grace-leakage trial 2: empty or limit message (204s, 29 chars)
grace-leakage: 1/1 valid (rate 1.0, 1 errors) CI [0.207, 1.0] -> PASS
wrote /home/user/probe/shard/results_on.json
== stripping knowledge/ for the bundle-OFF arm ==
ablating /root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
== bundle-OFF arm ==
ocean-science 0.9.0: sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04 (current) on claude-code (2.1.278 (Claude Code))
  grace-leakage trial 1: PASS (169s, 4302 chars)
  grace-leakage trial 2: PASS (148s, 4668 chars)
grace-leakage: 2/2 valid (rate 1.0, 0 errors) CI [0.342, 1.0] -> PASS
wrote /home/user/probe/shard/results_off.json
restored knowledge/
transcripts kept: 4 trial files
== delta scoreboard ==
wrote /home/user/probe/shard/ablation.html
ABLATION_DONE

real	12m55.905s
user	0m41.130s
sys	0m6.455s
EXIT=0
```

The rendered delta table:

| case | type | bundle on: rate (95% CI) | bundle off: rate | delta | verdict |
|---|---|---|---|---|---|
| grace-leakage | gotcha-avoidance | 1.00 [0.21, 1.00] | 1.00 | +0.0 | PASS |

Read 2.3 before reading anything into that delta.

### 3.2 Per-trial elapsed seconds

| Arm | Trial | Outcome | Elapsed (s) | Transcript chars |
|---|---|---|---|---|
| on | 1 | PASS | 227 | 5290 |
| on | 2 | error: turn limit | 204 | 29 |
| off | 1 | PASS | 169 | 4302 |
| off | 2 | PASS | 148 | 4668 |

Sum of trial time: **748 s**. Total wall clock: **775.9 s**. Everything that is not a
trial — building the record, three rubric-judge calls, the arm change, the guard and
the scoreboard render — cost **27.9 s combined**, so judging is cheap (order 7-9 s per
graded trial) and trial time dominates almost completely.

Mean **194 s of wall clock per trial**, which is the number to plan with.

**Estimate for the full experiment.** Trials are strictly sequential (2.1). The
pre-registered suite is 7 cases x 2 arms x N trials:

| Scope | Trials | Estimated wall clock |
|---|---|---|
| This shard (1 case, N=2) | 4 | 12 m 56 s (measured) |
| All 7 cases, N=2 | 28 | ~1.5 h |
| All 7 cases, N=20 (pre-registered) | 280 | **~15 h in one container** |

Caveats on that 15 h. It assumes grace-leakage's trial cost is representative; the
runner's own note warns a 30-turn multi-granule case has been measured above 600 s,
which is three times this case's mean, so a suite-wide figure could be materially
higher. It also assumes the outage rate stays near this shard's, and an errored trial
costs nearly as much as a good one (the turn-limit trial burned 204 s to produce 29
bytes) without contributing to N. Sharding across containers is the only parallelism
available, and two ablations must not share a container because the arm change moves a
directory in the shared plugin cache.

### 3.3 The ON arm outage, verbatim

You asked specifically whether the ON arm's lost trial was a turn limit, a quota
message, or something else. **It was the turn limit.** The complete transcript of
`transcripts_on/grace-leakage/trial2.txt`, all 29 bytes of it:

```
Error: Reached max turns (30)
```

`trial2.stderr` is **empty** — zero bytes. There is no quota message, no API error and
no partial answer; the runner classified it from the transcript text alone. The
recorded grader detail:

```json
{
  "trial": 2,
  "elapsed_s": 204,
  "chars": 29,
  "error": "empty or limit message"
}
```

Elapsed: **204 seconds**.

This matters more than one lost trial. `max_turns` was raised 12 -> 30 on 2026-09-21
precisely because seven of eight pilot trials exhausted at 12. At 30, **one of two ON
trials still exhausted** — and the manifest's own comment explains why that is not a
neutral loss: consulting the bundle costs turns, so the arm with the knowledge present
exhausts more readily, and the trials that survive are the atypically brief ones. That
is a treatment-correlated sampling bias, and this shard shows it is still live at 30
turns.

The shard is consistent with that bias, though far too small to establish it: the ON
arm lost one of two trials to exhaustion, the OFF arm lost none, and the two OFF trials
(169 s, 148 s) were both faster than the one surviving ON trial (227 s). At N=20 an
ON-arm outage rate anywhere near this would halve the ON arm's effective sample while
leaving OFF intact, and the ON arm's survivors would be skewed short. Worth watching
the per-arm `errors` counts across the other shards.

Turn exhaustion is correctly counted as an outage rather than a failure, so it does not
contaminate the rate: the ON arm reported 1/1 valid, rate 1.0, errors 1. The `trials`
field in a results file is the *valid* count, not the requested count; `trials_requested`
carries the 2. The consequence for the ablation is that the two arms are reported at
different effective N — ON at n=1, CI [0.21, 1.00]; OFF at n=2, CI [0.34, 1.00] — and
the delta column prints a bare `+0.0` with no interval at all.

### 3.4 Arm change: stripped and restored correctly

Verified at all three points:

- **Stripped.** Checked live during the OFF arm: the only entry matching
  `.../ocean-science/*/knowledge*` was `knowledge.ABLATION_OFF`. The real tree was
  absent for the whole OFF arm, which is the intended behaviour.
- **Restored.** `restored knowledge/` printed before the guard ran. After completion:

```
$ ls -d /root/.claude/plugins/cache/*/ocean-science/*/knowledge*
/root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge

$ find /root/.claude/plugins/cache -name '*.ABLATION_OFF'
(no output)

$ find .../ocean-science/0.9.0/knowledge -name '*.md' | wc -l
45
```

**No leftover `knowledge.ABLATION_OFF`.** The tree is back with all 45 concepts and the
container is clean for the next run.

- **Restored on failure too.** The failed exact-command run (2.1) also left no
  residue: the `trap restore EXIT INT TERM` fired and the glob returned only
  `knowledge`. The restore path is exercised on both the success and the error route.

### 3.5 Transcripts

Transcripts were written, for both arms, to
`<outdir>/transcripts_{on,off}/<case id>/trial<n>.{txt,stderr,json}` — four trials,
twelve files:

```
/home/user/probe/shard/transcripts_on/grace-leakage/trial1.{txt,stderr,json}
/home/user/probe/shard/transcripts_on/grace-leakage/trial2.{txt,stderr,json}
/home/user/probe/shard/transcripts_off/grace-leakage/trial1.{txt,stderr,json}
/home/user/probe/shard/transcripts_off/grace-leakage/trial2.{txt,stderr,json}
```

`ablate.sh` passes `--transcripts` for both arms unconditionally, so a caller cannot
forget it, and the end-of-run guard confirmed `transcripts kept: 4 trial files`. The
`.txt` holds the model's reply, `.stderr` its standard error, `.json` the grader detail
including the judge's one-sentence reason.

Committed under `scoreboard/probe/`, alongside `results_on.json`, `results_off.json`,
the full `run.log`, the rendered `ablation.html` and the failed exact-command log.
`.gitignore` matches `transcripts_on/` and `transcripts_off/` at any depth, so these
are tracked with `git add -f`; the directory names are kept as the harness wrote them
rather than renamed, so they line up with the run log.

---

## 4. Container state after the run

Clean. The knowledge tree is restored with all 45 concepts, no `*.ABLATION_OFF` exists
anywhere under the plugin cache, and no `ablate.sh` or `run_evals.py` process is left
running (checked with `ps -eo pid,etime,cmd`, not `pgrep`).

**A backgrounded run survives the agent's turn ending.** This was checked directly
while the OFF arm was in flight: `ps` showed both `ablate.sh` (pid 983) and
`run_evals.py --bundle off` (pid 1862) alive across several turns, and the run went on
to complete normally with exit 0. **The other thirteen shards can be driven this way.**

One caution learned here. While a run is live, the tree is *supposed* to be sitting as
`knowledge.ABLATION_OFF`, and that state is indistinguishable at a glance from the
residue of a dead run. Moving it back on sight would corrupt a live OFF arm mid-flight.
Check liveness with `ps` first and only restore if nothing is running — which during
this probe is exactly what the state check found, so the tree was deliberately left
alone and `ablate.sh` restored it itself.

---

## 5. Corrections to the partial version of this file

The mid-run commit on this branch carried two numbers that the completed run disproved:

- It estimated **~90 s of judging per passing trial**, inferred from a partial reading
  of elapsed timestamps. The real figure is **7-9 s**: total non-trial overhead for the
  whole run was 27.9 s across three judged trials.
- On that inflated overhead it put the N=20 sweep at **~19-22 h**. Corrected to
  **~15 h**, from a measured 194 s of wall clock per trial.

Nothing else changed. The findings in section 2 stand as written.

---

## 6. What I did not do

- I did not change the harness, the manifest, any case, any threshold or any trial
  count, and I did not fix any of the defects in section 2.
- I did not substitute a model. `claude-opus-5` ran every trial and every judge call,
  recorded in both results files as `"model": "claude-opus-5"` and
  `"judge_model": "claude-opus-5"`.
- I did not run two ablations at once. The two runs on this container were strictly
  sequential, and the first had already restored the tree before the second started.
- I did not re-run the ON arm, and I started no new run after the check-in.
- The one deviation from the instructions: I dropped `--concurrency 2` for the real
  run, after first running the command exactly as given and capturing its failure
  (2.1). Nothing else about the command changed. Had I not dropped it, there would be
  no run to report.
