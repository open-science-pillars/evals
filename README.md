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
repository's product subtree (the ocean cases are `ecco/cases/` in
[agent-evals](https://github.com/open-science-pillars/agent-evals));
this repo runs them. How cases are written and graded (fields, grader
kinds, seed discipline) is documented once, in the marketplace's
[testing guide](https://github.com/open-science-pillars/marketplace/blob/main/docs/testing.md). Every results file records capability, capability
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

A manifest lists the cases of one suite with the tools each trial may use
and its turn allowance: `manifests/ocean-science.yaml` drives the ECCO cases
from agent-evals and is the suite the organization's own ocean runs use,
`core.yaml` and `hydrology.yaml` run those capabilities' own cases,
`ablation.yaml` is the pre-registered bundle-on versus bundle-off suite (the
ocean gotcha-avoidance cases, same prompts and model in both arms), and
`poc-mht.yaml` is the small proof-of-concept pair (the heat-transport
basin-scope case plus the native-grid refusal as its control) that measured
whether a slimmed skill finds its concepts through discovery tools.

## Grading

A trial passes only if **every grader present agrees**: the programmatic
predicate (a conservative gate) AND the rubric judge (authoritative, skeptical:
partial compliance fails). A case's `rubric:` grader names the text
that judges it: the word `notes` for the case's own notes, the rubric written
out inline, or a path under the plugin's `evals/` directory. A path that does
not exist stops the run. Until 2026-09-22 it fell through to the notes in
silence, and thirteen cases across two repositories named rubric documents
that have never existed, so the grader in force was never the one the case
named. Each results file now records per case which text graded it, the
scoreboard refuses a delta between two arms graded differently, and
`merge_shards.py` refuses to add shards of a case that were graded
differently. A case
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
bundle installed (`--bundle on`) and with it removed (`--bundle off`), same
model and N, and publishes the per-case rate delta with its interval.
`scoreboard.py results_on.json results_off.json` renders the delta. Protocol
and go/stop conditions are pre-registered in
`marketplace/docs/phase2-preregistration.md`; the grader code is frozen before
the bundle-off arm runs.

What the off arm removes is derived, not assumed. Until 2026-09-21 it moved
one tree aside, the capability's own, and thirteen of the suite's fourteen
`concept_basis` citations name concepts in a dependency the arm never touched,
so every delta it produced compared an arm holding the cited knowledge against
an arm holding the cited knowledge. `ablation_scope.py` now walks the plugins
the manifest's cases name plus every dependency those plugins declare, moves
the installed knowledge tree of each, and refuses the run when a case cites
knowledge outside that scope. A suite the arm cannot ablate stops rather than
returning a number. The pilot that defect invalidated is withdrawn in place at
`scoreboard/pilot/`.

Deriving the scope was still a better guess about where copies live, and a
re-pilot on 2026-09-22 showed the arm is not off even with three trees moved:
the same knowledge sits in the workspace as ordinary checked-out files, and
recorded passing answers to these exact cases sit beside them under `results/`
and `fixtures/` directories. Setting the trial's working directory does not
close this. A headless run whose working directory was an empty temporary
directory read an absolute path under the workspace without difficulty, so
confinement is not available through the launcher.

`leak_check.py` is therefore not a guess. It takes text out of the concepts the
cases cite and looks for that text on disk, so a copy is found because it is a
copy. It collapses whitespace first, because a concept wraps its prose and a
transcript quoting it does not, and a line-oriented search reports such a copy
as absent. It gates both arms: the bundle-off arm may have no cited concept
readable anywhere, and neither arm may have a recorded answer to a case in the
run readable, because an answer contaminates the rate itself and not only the
difference between the arms. Only the exact fixture files a case declares are
allowed beside it.

A run workspace is therefore prepared rather than cloned whole, and the check is
what says it is prepared.

License: Apache-2.0.
