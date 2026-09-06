# evals

The Open Science Pillars eval runner: headless, N-trial execution of the
plugins' eval cases against Claude Code, with programmatic and rubric-judge
grading, binomial confidence intervals, and a scoreboard.

Evals test the assistant's **scientific judgment** with a plugin installed
(golden notebooks test code; the surface harness tests packaging). Each case
lives with the plugin it tests (`<plugin>/evals/*.yaml`); this repo runs them.

## Layout

```
evals/
├── runner/
│   ├── run_evals.py   # loads a manifest, runs N trials per case, grades, aggregates
│   ├── graders.py     # programmatic transcript predicates (fast, deterministic gate)
│   ├── judge.py       # rubric judge (LLM-as-judge; authoritative)
│   ├── stats.py       # Wilson binomial CI + pass verdict
│   └── scoreboard.py  # renders results.json to a static HTML scoreboard
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

## The ablation

The headline experiment runs the gotcha-avoidance suite with the knowledge
bundle installed (`--bundle on`) and with `knowledge/` removed
(`--bundle off`), same model and N, and publishes the per-case rate delta with
its interval. `scoreboard.py results_on.json results_off.json` renders the
delta. Protocol and go/stop conditions are pre-registered in
`marketplace/docs/phase2-preregistration.md`; the grader code is frozen before
the bundle-off arm runs.

License: Apache-2.0.
