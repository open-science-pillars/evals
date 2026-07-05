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
└── scoreboard/        # results.json + index.html (published)
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
python runner/run_evals.py --manifest manifests/ocean-science.yaml \
    --workspace /path/to/osp-workspace --trials 20 --model claude-fable-5 \
    --out scoreboard/results.json
python runner/scoreboard.py scoreboard/results.json --out scoreboard/index.html

# Quick check (a subset at low N, for local reproduction of seed grades)
python runner/run_evals.py --manifest manifests/ocean-science.yaml \
    --workspace /path/to/osp-workspace --trials 3 \
    --cases geothermal-omission,grace-leakage --out /tmp/demo.json
```

The plugins must be installed in the workspace Claude Code runs from. The full
N=20 sweep across all suites is a continuous-integration / cloud job, not a
laptop run.

## The ablation (Session 19)

The headline experiment runs the gotcha-avoidance suite with the knowledge
bundle installed (`--bundle on`) and with `knowledge/` removed
(`--bundle off`), same model and N, and publishes the per-case rate delta with
its interval. `scoreboard.py results_on.json results_off.json` renders the
delta. Protocol and go/stop conditions are pre-registered in
`marketplace/docs/phase2-preregistration.md`; the grader code is frozen before
the bundle-off arm runs.

License: Apache-2.0.
