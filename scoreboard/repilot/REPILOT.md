# Ablation re-pilot on the fixed harness — 2026-09-22

## One claim below is corrected, and one finding goes further

This report is kept as the run produced it. Two notes from reading it after.

**The attribution in "The attribution is positive, not inferred" does not
hold.** It argues the workspace checkout is the source, because the frontmatter
and the numeric anchor occur only in knowledge files. They occur in the recorded
passing answers as well, under `agent-evals/ecco/results/2026-09-04-osp-installed/
transcripts/`, which are equally readable from where the trials ran. Both copies
carry the text the transcripts reproduce, so nothing here says which was read.
The conclusion that bundle-off is not off is unaffected and is what matters; the
step naming one copy over the other is not established. Checking it by hand very
nearly went the same way in reverse: a search for the quoted sentence appeared
to find it only in the recorded answers, because the concept wraps that sentence
across two lines and the search was line-oriented.

**The arm had not moved the trees out of reach either.** The report verifies
that all three sat at `knowledge.ABLATION_OFF` while the off trials ran, and
treats that as removal. It is not. A trial reading an absolute path reads the
tree under the new name as readily, so the concepts were available in the off
arm through a third route the report does not consider. Set-aside directories
are archived and deleted now rather than renamed.

Both are recorded in the pre-registration's amendments under 2026-09-22.


Re-pilot of the gotcha-avoidance ablation after `runner/ablation_scope.py`
landed (`d83337a`, "Make bundle-OFF actually remove the knowledge the cases
cite"). Every earlier pilot result is void and none is used as a baseline here.

Two cases (`grace-leakage`, `native-grid-refusal`), two trials per arm, model
pinned to `claude-opus-5` on both arms and as the judge.

## Headline: bundle-OFF is still not off

**All four bundle-OFF trials cite their case's `concept_basis` files by path,
and say they consulted the knowledge.** The behaviour the old harness showed is
unchanged.

The fix itself is not at fault, and it does what it claims — see "What the fix
did fix" below. The arm is defeated by a second copy of the same knowledge that
the arm never had in its scope: the workspace checkouts.

## Setup

Six repos cloned side by side at `/home/user` (the workspace root), default
branch of each:

| repo | branch | commit |
|---|---|---|
| `evals` | main | `5de305e` |
| `agent-evals` | main | `248394d` |
| `ocean-science` | main | `4326f3f` |
| `core` | main | `c2cbe0f` |
| `nasa-daac-knowledge` | main | `c04ae2e` |
| `build-kit` | main | `b0866fd` |

One marketplace, one install. `claude plugin install ocean-science@open-science-pillars`
pulled `core` and `nasa-daac-knowledge` as declared dependencies:

```
Installed plugins:
  > core@open-science-pillars                Version: 0.6.0                    enabled
  > nasa-daac-knowledge@open-science-pillars Version: 2026.9.5-6b0ef007a964    enabled
  > ocean-science@open-science-pillars       Version: 0.9.0                    enabled

Configured marketplaces:
  > open-science-pillars   Source: GitHub (open-science-pillars/marketplace)
```

Exactly one knowledge tree per plugin in the cache, so the scope check's
more-than-one-marketplace refusal was not triggered.

### One setup note worth recording

The pre-existing `evals` checkout in this container had a **stale `origin/main`**
from container start, pointing at `5533f05` — which predates the fix. Branching
off it silently reverted `runner/ablate.sh` to the old single-tree version and
removed `ablation_scope.py`. A `git fetch origin main` advanced `origin/main` to
`5de305e` and the branch was reset onto that. Everything below ran on the fixed
harness; `runner/ablation_scope.py` is present and `ablate.sh` calls it.

## Scope check (verbatim)

```
$ uv run --with pyyaml==6.0.2 /home/user/evals/runner/ablation_scope.py \
      /home/user /home/user/evals/manifests/ablation.yaml --check
plugins in scope: ocean-science, core, nasa-daac-knowledge
  ocean-science: 45 concepts  /root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
  core: 12 concepts  /root/.claude/plugins/cache/open-science-pillars/core/0.6.0/knowledge
  nasa-daac-knowledge: 243 concepts  /root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge
every cited concept is inside a tree this arm removes
```

Exit status 0.

### Concept count per plugin

| plugin | concepts | expected | note |
|---|---|---|---|
| ocean-science | 45 | ~45 | matches |
| core | 12 | "a few dozen" | **under** expectation |
| nasa-daac-knowledge | 243 | ~267 | **under** expectation by 24 |

The counts were cross-checked against the repo checkouts and agree exactly
(`ocean-science` 45, `core` 12, `nasa-daac-knowledge` 243 `.md` files), so these
are the real contents of the installed versions rather than a partial install.
Flagged, not treated as a stop: the check's own assertion passed.

## Run (verbatim)

```
bash /home/user/evals/runner/ablate.sh /home/user 2 \
     /home/user/evals/scoreboard/repilot claude-opus-5 \
     --cases grace-leakage,native-grid-refusal
```

```
plugins in scope: ocean-science, core, nasa-daac-knowledge
  ocean-science: 45 concepts  /root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
  core: 12 concepts  /root/.claude/plugins/cache/open-science-pillars/core/0.6.0/knowledge
  nasa-daac-knowledge: 243 concepts  /root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge
every cited concept is inside a tree this arm removes
== bundle-ON arm ==
ocean-science 0.9.0: sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04 (current) on claude-code (2.1.278 (Claude Code))
  native-grid-refusal trial 1: PASS (95s, 3841 chars)
  native-grid-refusal trial 2: PASS (85s, 3911 chars)
native-grid-refusal: 2/2 valid (rate 1.0, 0 errors) CI [0.342, 1.0] -> PASS
  grace-leakage trial 1: PASS (172s, 4571 chars)
  grace-leakage trial 2: empty or limit message (143s, 29 chars)
grace-leakage: 1/1 valid (rate 1.0, 1 errors) CI [0.207, 1.0] -> PASS
wrote /home/user/evals/scoreboard/repilot/results_on.json
== stripping every cited knowledge tree for the bundle-OFF arm ==
  ablating /root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge (45 concepts)
  ablating /root/.claude/plugins/cache/open-science-pillars/core/0.6.0/knowledge (12 concepts)
  ablating /root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge (243 concepts)
== bundle-OFF arm ==
ocean-science 0.9.0: sha256:de135f0aa0f840d4b8615d91983cfaf61ac9da10bedf11a7e0756478d2607f04 (current) on claude-code (2.1.278 (Claude Code))
  native-grid-refusal trial 1: PASS (107s, 4447 chars)
  native-grid-refusal trial 2: PASS (80s, 3548 chars)
native-grid-refusal: 2/2 valid (rate 1.0, 0 errors) CI [0.342, 1.0] -> PASS
  grace-leakage trial 1: PASS (207s, 4522 chars)
  grace-leakage trial 2: PASS (118s, 4117 chars)
grace-leakage: 2/2 valid (rate 1.0, 0 errors) CI [0.342, 1.0] -> PASS
wrote /home/user/evals/scoreboard/repilot/results_off.json
restored 3 knowledge tree(s)
transcripts kept: 8 trial files
== delta scoreboard ==
wrote /home/user/evals/scoreboard/repilot/ablation.html
ABLATION_DONE
```

### Per-trial elapsed seconds

| arm | case | trial 1 | trial 2 |
|---|---|---|---|
| ON | native-grid-refusal | 95 s | 85 s |
| ON | grace-leakage | 172 s | 143 s (errored) |
| OFF | native-grid-refusal | 107 s | 80 s |
| OFF | grace-leakage | 207 s | 118 s |

## Pass counts per case

| case | ON | OFF |
|---|---|---|
| native-grid-refusal | 2/2 valid, rate 1.0, 0 errors | 2/2 valid, rate 1.0, 0 errors |
| grace-leakage | 1/1 valid, rate 1.0, **1 error** | 2/2 valid, rate 1.0, 0 errors |

Seven of eight trials passed; the eighth errored rather than failed. No
conclusion is drawn here about whether the knowledge bundle helps. Two trials
per arm is a small sample, the point of this run was the harness, and — per the
headline — the arms were not contrasting what they are supposed to contrast.

## The bundle-OFF citation check

Grepping the OFF transcripts for `knowledge/podaac/` paths:

| arm | case | trial | `knowledge/podaac/` paths cited |
|---|---|---|---|
| OFF | native-grid-refusal | 1 | `gotchas/ecco-native-vs-regridded.md` |
| OFF | native-grid-refusal | 2 | `gotchas/ecco-native-vs-regridded.md` |
| OFF | grace-leakage | 1 | `datasets/grace-fo-mascons.md`, `gotchas/grace-coastal-leakage.md`, `gotchas/grace-gia-correction.md`, `gotchas/grace-intermission-gap.md`, `recipes/grace-mass-to-sea-level.md` |
| OFF | grace-leakage | 2 | `datasets/grace-fo-mascons.md`, `gotchas/grace-coastal-leakage.md` |

**Every OFF trial cites its case's full `concept_basis`.** `native-grid-refusal`
cites `ecco-native-vs-regridded.md` in both trials; `grace-leakage` cites both
`grace-coastal-leakage.md` and `grace-fo-mascons.md` in both trials.

They also state they consulted the knowledge. Opening lines, bundle-OFF:

- `native-grid-refusal` trial 1: "I consulted the knowledge bundle first, and this request stops at the gate."
- `grace-leakage` trial 1: "I stopped before computing, because the installed knowledge concepts say this particular quantity isn't recoverable from this product"
- `grace-leakage` trial 2: "there's a finding from the knowledge b[undle]"

OFF `native-grid-refusal` trial 1 goes further and quotes concept frontmatter:

> Per `knowledge/podaac/gotchas/ecco-native-vs-regridded.md` (severity high,
> status stable, human-verified 2026-09-04)

and quotes `1.24e-12`, the geothermal-omission residual from
`knowledge/computations/ecco-regional-heat-budget.md`.

## What the fix did fix

The scope derivation works and should not be reverted.

- Three trees were moved, not one: `ocean-science` (45), `core` (12) and
  `nasa-daac-knowledge` (243). The old harness moved only the first.
- Verified on disk mid-arm that all three sat at `knowledge.ABLATION_OFF` while
  the OFF trials ran.
- The check correctly refuses ambiguity and correctly resolved the dependency
  closure `ocean-science -> core, nasa-daac-knowledge` from
  `ocean-science/.osp/package.yaml`.

## Why bundle-OFF is still not off

The plugin cache is not the only copy of the knowledge on the machine. Three of
the six workspace repos carry the same trees as ordinary checked-out files:

```
/home/user/nasa-daac-knowledge/knowledge/podaac/gotchas/ecco-native-vs-regridded.md
/home/user/nasa-daac-knowledge/knowledge/podaac/gotchas/grace-coastal-leakage.md
/home/user/nasa-daac-knowledge/knowledge/podaac/datasets/grace-fo-mascons.md
/home/user/ocean-science/knowledge/computations/ecco-regional-heat-budget.md
```

`run_evals.py` calls `subprocess.run(cmd, ...)` with no `cwd`, so each trial
inherits the launcher's directory — the workspace root — and `Read` is in
`allowed_tools`. The OFF transcripts confirm they browsed it:

> My sandbox is scoped to `/home/user`, so if it's elsewhere, point me at it.

> Searching `/home/user` turned up no `05DEG` granules and no native tree at
> `~/ECCO_V4r4` — only a stub fixture at
> `agent-evals/ecco/fixtures/native-grid/ecco_05deg_stub.nc`.

### The attribution is positive, not inferred

`1.24e-12` and the `verified: { by: human:PaulMRamirez, ... }` frontmatter occur
**only** in knowledge files. Grepping the plugin content that the ablation never
touches — `skills/`, `agents/`, `briefings/` across all three installed plugins
— returns zero hits for either string. The cache copies were renamed away before
the OFF arm started. The workspace checkout is therefore the source.

This distinguishes the leak from the skills confound recorded in
`scoreboard/pilot/README.md`. That confound is also real and unaddressed — the
skills do cite the concept by its exact path, e.g.
`skills/ecco/references/llc90-grid.md:23` and
`skills/ecco/references/budget-formulation.md:26` — but the skills do not carry
the frontmatter or the numeric anchors that these OFF transcripts reproduce.

### Two further leak channels in the same sandbox

Independent of the knowledge trees, and not closed by removing them:

- `/home/user/agent-evals/ecco/results/2026-09-04-osp-installed/transcripts/`
  holds recorded **passing answers to these exact cases**, including
  `native-grid-refusal.md` and `grace-leakage.md`.
- `/home/user/evals/runner/fixtures/transcripts/native-grid-refusal.off-trial1.pass.txt`
  is a recorded OFF pass, inside the `evals` repo itself.

No choice of launch directory under the workspace closes all of this: the
workspace root exposes the knowledge trees, and `evals/` exposes the recorded
pass fixtures. Closing it is a harness change, not a launch-flag change, and is
left to you. Nothing in the harness, the cases, the graders or the numbers was
modified for this run.

## Errored trial

One trial errored. Bundle-ON, `grace-leakage`, trial 2, **143 s elapsed**.

Transcript verbatim, in full (29 characters, the whole file):

```
Error: Reached max turns (30)
```

`trial2.stderr` is empty. `trial2.json`:

```json
{
  "trial": 2,
  "elapsed_s": 143,
  "chars": 29,
  "error": "empty or limit message"
}
```

Turn exhaustion at the raised budget of 30, classified by `is_error_transcript`
as an infrastructure error rather than a substantive failure — the intended
handling. It is why ON `grace-leakage` reports 1/1 valid rather than 2/2.

## Tree strip and restore

Stripped — all three, as logged above. Restored — `restored 3 knowledge tree(s)`,
confirmed on disk after the run:

```
/root/.claude/plugins/cache/open-science-pillars/core/0.6.0/knowledge
/root/.claude/plugins/cache/open-science-pillars/nasa-daac-knowledge/2026.9.5-6b0ef007a964/knowledge
/root/.claude/plugins/cache/open-science-pillars/ocean-science/0.9.0/knowledge
```

Concept counts after restore match the pre-run counts exactly: 45, 12, 243.

**No leftover `.ABLATION_OFF`.** `find / -name '*.ABLATION_OFF'` returns nothing.

## Files

- `results_on.json`, `results_off.json` — per-trial verdicts, elapsed, grader detail
- `ablation.html` — rendered delta
- `transcripts_on/`, `transcripts_off/` — all 8 trials (`.txt`, `.stderr`, `.json`),
  committed with `git add -f` past `.gitignore`
