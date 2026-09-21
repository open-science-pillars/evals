# Shard probe: can one shard of the pre-registered ablation run end to end?

Branch `claude/ablation-probe`. Container: Claude Code on the web, Linux 6.18.44.
Probe date 2026-09-21. Model pinned to `claude-opus-5` throughout; no substitution
was made at any point.

**This file is written while the bundle-OFF arm is still running.** It is pushed
partial, on request, because the branch did not exist on the remote and nothing was
visible. The sections below say exactly what is complete and what is not.

## Bottom line

The harness works, but **the shard command as written cannot run**, and separately
**the bundle-OFF arm does not ablate the `grace-leakage` case**. Details in
"What breaks", which is the part of this document worth your time.

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

### 3.1 Output so far, verbatim

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
```

**The OFF arm's trial 2 was still running when this file was written.** The run had
not reached `ABLATION_DONE`, the delta scoreboard had not been rendered, and
`results_off.json` did not yet exist.

### 3.2 Per-trial elapsed seconds

| Arm | Trial | Outcome | Elapsed (s) | Transcript chars |
|---|---|---|---|---|
| on | 1 | PASS | 227 | 5290 |
| on | 2 | error: turn limit | 204 | 29 |
| off | 1 | PASS | 169 | 4302 |
| off | 2 | *(in flight at time of writing)* | — | — |

Three completed trials: 227 + 204 + 169 = 600 s, mean **200 s/trial**.

Wall clock is larger than the sum of trials, because each PASS also pays for a rubric
judge call that is not counted in `elapsed_s`. Measured: ON arm start to
`wrote results_on.json` was about 8 minutes for two trials, against 431 s of trial
time — roughly **90 s of judging per passing trial** on top.

**Estimate for the full experiment.** At ~200 s/trial plus ~90 s judging per
non-errored trial, one case-trial costs roughly 250-290 s end to end. The full
pre-registered suite is 7 cases x 2 arms x N trials, strictly sequential:

- N=2 (this shard's depth), all 7 cases: 28 trials, ~2.0-2.3 hours
- N=20 (the pre-registered sweep): 280 trials, **~19-22 hours of wall clock in one container**

That is a single-threaded estimate, and per 2.1 there is currently no way to make it
anything else within one run. Sharding across containers is the only parallelism
available, and per the standing rule two ablations must not share a container because
the arm change moves a directory in the shared plugin cache.

### 3.3 The ON arm outage, verbatim

You asked specifically whether the ON arm's lost trial was a turn limit, a quota
message, or something else. **It was the turn limit.** The complete transcript of
`transcripts_on/grace-leakage/trial2.txt`, all 29 bytes of it:

```
Error: Reached max turns (30)
```

`trial2.stderr` is **empty** — zero bytes. There is no quota message, no API error,
no partial answer. The grader detail recorded:

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
exhausts more readily, and the surviving trials are the atypically brief ones. That is
a treatment-correlated sampling bias, and this shard shows it is still live at 30
turns. One trial is far too little to put a number on, but at N=20 a ~50% ON-arm
outage rate would halve the ON arm's effective sample while leaving OFF nearly intact.

Turn exhaustion is correctly counted as an outage rather than a failure (`errors: 1`),
so it does not contaminate the rate: the ON arm reported 1/1 valid, rate 1.0. The
`trials` field in the results file is the *valid* count, not the requested count;
`trials_requested` carries the 2.

### 3.4 Arm change: stripped and restored

- **Stripped correctly.** Checked live during the OFF arm: the only entry matching
  `.../ocean-science/*/knowledge*` was `knowledge.ABLATION_OFF`. The real tree was
  gone for the duration of the OFF arm, which is the intended behaviour.
- **Restored correctly after the failed exact-command run.** `restored knowledge/`
  printed, the glob returned only `knowledge`, and the tree still held 45 markdown
  files.
- **Not yet restored for the in-flight run**, because that run is still in its OFF
  arm. See the warning below.

### 3.5 Transcripts

Transcripts were written, to
`<outdir>/transcripts_{on,off}/<case id>/trial<n>.{txt,stderr,json}`:

```
/home/user/probe/shard/transcripts_on/grace-leakage/trial1.txt
/home/user/probe/shard/transcripts_on/grace-leakage/trial1.stderr
/home/user/probe/shard/transcripts_on/grace-leakage/trial1.json
/home/user/probe/shard/transcripts_on/grace-leakage/trial2.txt
/home/user/probe/shard/transcripts_on/grace-leakage/trial2.stderr
/home/user/probe/shard/transcripts_on/grace-leakage/trial2.json
/home/user/probe/shard/transcripts_off/grace-leakage/trial1.*
```

`ablate.sh` passes `--transcripts` for both arms unconditionally, so this is not
something a caller can forget. The `.txt` holds the model's reply, `.stderr` its
standard error, `.json` the grader detail including the judge's one-sentence reason.

Committed under `scoreboard/probe/`. `.gitignore` matches `transcripts_on/` and
`transcripts_off/` at any depth, so these are tracked with `git add -f`; the directory
names are kept as the harness wrote them rather than renamed.

---

## 4. Warning about this container's state

At the time of writing, the knowledge tree is moved aside:

```
/root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge.ABLATION_OFF
```

**This is correct and expected — the bundle-OFF arm is still running.** It is not the
residue of a dead run. Confirmed with `ps`, not `pgrep`:

```
  983  10:59 bash /home/user/evals/runner/ablate.sh /home/user 2 /home/user/probe/shard claude-opus-5 --cases grace-leakage
 1862   3:40 python /home/user/evals/runner/run_evals.py --manifest .../ablation.yaml --workspace /home/user --trials 2 --model claude-opus-5 --bundle off --out .../results_off.json --transcripts .../transcripts_off --cases grace-leakage
```

Moving the tree back now would corrupt the live OFF arm mid-flight. It is left alone
deliberately; `ablate.sh`'s `trap restore EXIT INT TERM` restores it when the arm
finishes. The restoration is verified in the final version of this file.

**The run survived the agent turn ending.** A backgrounded `ablate.sh` keeps running
across turns in this container, which is the fact that decides whether the other
thirteen shards can be driven this way. They can.
