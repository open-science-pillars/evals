# evals

The Open Science Pillars eval runner: headless, N-trial execution of the
plugins' eval cases against a runtime (Claude Code by default), with
programmatic and rubric-judge grading, binomial confidence intervals, a
scoreboard, and a record on every result that says which capability
release ran on which runtime.

Evals test the assistant's **scientific judgment** with a capability installed
(golden notebooks test code; the runtime harness tests packaging). A case
lives with the capability it tests (`<plugin>/evals/*.yaml`) or, where the
capability declares an eval repository as its cases' home, in that
repository's product subtree (the ocean cases are `agent-evals/ecco/cases/`);
this repo runs them. Every results file records capability, capability
version, release lock, runtime, model, suite, trial count, score, interval
and date (the cross-runtime record below), so identical cases compare
across runtimes without changing the capability contract: the cases and
the graders are the same on every runtime, and the record is the
dimension that differs.

## Layout

```
evals/
├── runner/
│   ├── run_evals.py   # loads a manifest, runs N trials per case, grades, aggregates
│   ├── graders.py     # programmatic transcript predicates (fast, deterministic gate)
│   ├── judge.py       # rubric judge (LLM-as-judge; authoritative)
│   ├── stats.py       # Wilson binomial CI + pass verdict
│   ├── record.py      # the cross-runtime record: capability, release lock, runtime, model, date
│   ├── drivers.py     # the headless command per runtime (Claude Code; Codex, unexercised)
│   └── scoreboard.py  # renders results.json to a static HTML scoreboard; compares runtimes
├── manifests/         # per-plugin case lists with allowed_tools and max_turns
└── scoreboard/        # results.json + index.html (published); transcripts/ when kept
```

## Grading

A trial passes only if **every grader present agrees**: the programmatic
predicate (a conservative gate) AND the rubric judge (authoritative, skeptical:
partial compliance fails). A case's `notes` field is the default rubric; a
dedicated `rubric:` file overrides it when a case needs more detail. A case
passes when its point-estimate pass rate meets its threshold (default 0.8); the
Wilson 95% interval is reported for transparency and drives the ablation.

## Run it

```bash
# Full sweep (a CI job: hundreds of agentic invocations)
uv run runner/run_evals.py --manifest manifests/ocean-science.yaml \
    --workspace /path/to/osp-workspace --trials 20 --model claude-fable-5 \
    --out scoreboard/results.json --transcripts scoreboard/transcripts
uv run runner/scoreboard.py scoreboard/results.json --out scoreboard/index.html

# Quick check (a subset at low N, for local reproduction of seed grades)
uv run runner/run_evals.py --manifest manifests/ocean-science.yaml \
    --workspace /path/to/osp-workspace --trials 3 \
    --cases geothermal-omission,grace-leakage --out /tmp/demo.json
```

The plugins must be loaded in the Claude Code session each trial runs in:
installed, or handed in from a checkout with `--claude-arg=--plugin-dir
--claude-arg=/path/to/checkout` (repeatable; every value is passed to
`claude` verbatim and recorded in the results file). An installed plugin of
the same name wins over a checkout, so a checkout under test is loaded with
that plugin disabled for the trial only: `--claude-arg=--settings
--claude-arg='{"enabledPlugins":{"hydrology@open-science-pillars":false}}'`,
which changes nothing on disk. Launch the runner from a directory that
carries no project instructions or memory of its own, so a trial reads only
what the plugins give it. The full
N=20 sweep across all suites is a continuous-integration / cloud job, not a
laptop run. The runner's dependencies are declared in its script header, so
`uv run` needs no environment of its own.

### Reading a failure

A pass rate is not a diagnosis. The results file records every trial
(elapsed seconds, the error kind for a trial that never graded, each grader's
outcome and the judge's one-sentence reason), and `--transcripts DIR` keeps
the transcript, stderr and grader detail of every trial under
`DIR/<case id>/trial<n>.*`, so a failed case is read from disk rather than
rerun. Keep transcripts on any run whose numbers you intend to cite.

Two limits shape a trial and both are recorded: the manifest's `max_turns`
(a trial cut short by the turn allowance grades as whatever it managed to
say, usually a FAIL) and the runner's `--timeout` (default 1200 s; a trial
past it is an error, not a failure, and its partial output is kept). When a
case fails, check the elapsed times and turn allowance before reading the
rubric verdicts: a 30-turn multi-granule case has been measured above 600 s
before judging.

## The cross-runtime record

Every results file carries, at the top level and echoed on each case:

| Field | Where it comes from |
|---|---|
| `capabilities.<name>.version` | the capability's `.osp/package.yaml` (or its Claude manifest) in the workspace |
| `capabilities.<name>.release_lock` | sha256 of the capability's `.osp/release-lock.json` as a value; `release_lock_current` says whether the lock still matches the tree, asked of build-kit's `osp.py lock --check` when build-kit is in the workspace, `null` when it is not |
| `runtime` | `--runtime` (default `claude-code`), its projection (`claude` for the Claude family, `agent-plugins` for every other client) and the runtime's own version string (`--runtime-version` when its CLI cannot be asked) |
| `model`, `judge_model` | the trial model and the rubric judge's model; the judge is a Claude Code call on every runtime, so grading is held constant across runtimes |
| `suite`, `trials`, `date` | the manifest name, trials requested per case, the UTC date of the run |
| per case: `rate`, `ci95`, `passes`, `trials` | the score, its Wilson 95% interval and the counts, as before |

Two results files for the same capability release on different runtimes
compare with `scoreboard.py results_claude.json results_codex.json`: the
header states what each recorded and the delta column is the runtime's,
not the science's. A result whose lock is stale, or whose capability
version differs between the two files, is not a runtime comparison and
the header says so.

Claude Code is the runtime the runner drives headlessly. `--runtime
openai-codex` launches `codex exec` with the prompt on standard input;
that command is written from the Codex CLI's documented headless form and
is unexercised until the reference capability's Codex leg runs it. Claude
Cowork has no headless interface: a Cowork result is produced by the
qualification checklist and written with the same record fields. A
runtime with no driver here is refused rather than guessed.

## The ablation

The headline experiment runs the gotcha-avoidance suite with the knowledge
bundle installed (`--bundle on`) and with `knowledge/` removed
(`--bundle off`), same model and N, and publishes the per-case rate delta with
its interval. `scoreboard.py results_on.json results_off.json` renders the
delta. Protocol and go/stop conditions are pre-registered in
`marketplace/docs/phase2-preregistration.md`; the grader code is frozen before
the bundle-off arm runs.

License: Apache-2.0.
