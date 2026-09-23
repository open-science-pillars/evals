#!/usr/bin/env bash
# Ablation harness: run the gotcha-avoidance suite bundle-ON, then bundle-OFF
# (every knowledge tree the cases cite stripped from the installed plugin
# cache), then render the delta. The trees are ALWAYS restored, on error or
# interrupt as well as on success.
#
# What bundle-OFF removes is derived, not assumed. Until 2026-09-21 this moved
# one tree, the capability's own, and called that off. Thirteen of the suite's
# fourteen concept citations name files in nasa-daac-knowledge, a separate
# plugin with a separate cache the arm never touched, so the bundle-OFF arm had
# the cited knowledge in front of it the whole time. One of its transcripts
# opens "I read the bundle concepts before touching data" and cites both files
# by path. Every ON minus OFF number this harness has produced, the pilot null
# in the pre-registration included, compared knowledge against knowledge.
# ablation_scope.py now derives the plugins from the manifest and their declared
# dependencies, and refuses to run when a cited concept sits outside them.
#
# Both arms keep their transcripts, under <out_dir>/transcripts_{on,off}. This
# is not optional here and is not left to the caller. The pre-registration's
# analysis commitments require raw transcripts for every trial, and run_evals.py
# writes them only when asked; the pilot was run without asking, so its results
# hold rates and nothing else and its null can no longer be read. Diagnosing the
# release-mixing case on 2026-09-21 meant reconstructing what a reply must have
# said from the grader's source, because the three that failed were not kept.
# A rate is not a diagnosis.
#
# The model is required and is passed to both arms. run_evals.py defaults to
# one, and this script used to pass none, so the run silently took that default:
# on 2026-09-21 a pilot here ran the model the pre-registration had moved away
# from that same day, and every trial errored on its quota. A default is how an
# ablation measures something other than what it registered, so there is none.
#
# Usage: ablate.sh <workspace> <trials> <out_dir> <model> [--no-judge]
set -uo pipefail
WS="$1"; TRIALS="$2"; OUT="$3"; MODEL="${4:-}"; shift 3
[ -n "$MODEL" ] || { echo "ERROR: a model is required: ablate.sh <workspace> <trials> <out_dir> <model> [extra]"; exit 1; }
shift
EXTRA="${*:-}"
MAN="$WS/evals/manifests/ablation.yaml"
# The trees to move: derived from the manifest and the dependencies its plugins
# declare, checked so that every cited concept is inside one of them.
SCOPE="$WS/evals/runner/ablation_scope.py"
uv run --with pyyaml==6.0.2 "$SCOPE" "$WS" "$MAN" --check || {
  echo "ERROR: the bundle-OFF arm would not remove the knowledge these cases cite; not running"
  exit 1
}
mapfile -t KDIRS < <(uv run --with pyyaml==6.0.2 "$SCOPE" "$WS" "$MAN")
[ "${#KDIRS[@]}" -gt 0 ] || { echo "ERROR: no installed knowledge tree to ablate"; exit 1; }
# The workspace carries the same trees as ordinary files. They move aside for
# both arms, not for the off arm alone: with them present the bundle-ON arm is
# not reading the installed bundle either, and the thing the experiment
# manipulates has to be the only copy on the machine. The record and the release
# lock are built before they move, so nothing in the record is affected.
mapfile -t WDIRS < <(uv run --with pyyaml==6.0.2 "$SCOPE" "$WS" "$MAN" --workspace-trees)

# The release lock digests the content tree, knowledge included, so it can only
# be checked while the knowledge is still in place. It is checked here, before
# anything moves, and the arms then run with --no-lock-check so that a tree this
# script moved on purpose is not recorded as a stale lock. The verdict is written
# beside the results rather than left in a log.
mapfile -t PLUGINS < <(uv run --with pyyaml==6.0.2 "$SCOPE" "$WS" "$MAN" --plugins)

# What a trial can read is not what the arm change controls. Setting the
# subprocess working directory does not confine it either: a headless run whose
# working directory was an empty temporary directory read an absolute path under
# the workspace without difficulty, checked on 2026-09-22. So the copies have to
# be absent, and absence is established by searching for the text rather than by
# predicting where copies live.
MARKS="$WS/evals/runner/concept-fingerprints.json"
[ -f "$MARKS" ] || { echo "ERROR: $MARKS is missing; freeze it with --freeze where the concepts are readable"; exit 1; }
# The runner sets these aside once it has loaded what it needs from them, runs
# the leak check in that state, and puts them back when the trials are done. The
# case directories go too and it finds those itself.
# The bundle-ON arm sets aside the workspace copies only, so the installed
# bundle is the one thing a trial can consult, which is what bundle-ON means.
# The bundle-OFF arm sets aside the installed trees as well.
QUAR_ON=()
for w in "${WDIRS[@]}"; do QUAR_ON+=(--quarantine "$w"); done
QUAR_OFF=("${QUAR_ON[@]}")
for k in "${KDIRS[@]}"; do QUAR_OFF+=(--quarantine "$k"); done
# And the bundle-ON arm's own transcripts. They are answers to the very cases
# the bundle-OFF arm is about to be asked, written by this script into a
# directory the off trials can read, so they contaminate the rate rather than
# the difference. The first shard to reach the off arm was stopped here: three
# of twenty on-arm transcripts had quoted enough of the cited concept for the
# leak check to match it, which is the check doing its job on a leak this
# script created. The runner puts them back when the off arm is done.
QUAR_OFF+=(--quarantine "$OUT/transcripts_on")
# The on arm's results file is the same kind of thing and was left readable.
# It carries every trial's verdict and the grader's reasoning about what the
# response said, case by case, which is an answer sheet in a plainer form than
# the transcripts are. It went unnoticed because the check that looks for
# recorded answers matched directory names and this is a file, and because a
# run had never yet shared a machine with its own earlier arm in a way that
# made it visible.
QUAR_OFF+=(--quarantine "$OUT/results_on.json")

mkdir -p "$OUT"

# The runner sets every tree aside and puts it back, on its own exit and on a
# signal, so there is nothing for this script to restore. What it does check is
# that the runner kept its word, because a missing tree is worse than a failed
# run and should not be found later by someone else.
check_restored() {
  local missing=0
  for k in "${KDIRS[@]}" "${WDIRS[@]}"; do
    [ -d "$k" ] || { echo "ERROR: $k was not put back"; missing=$((missing+1)); }
  done
  [ "$missing" -eq 0 ] || echo "$missing knowledge tree(s) are missing; the runner's holding directory is under the system temp directory"
  return 0
}
trap check_restored EXIT INT TERM

echo "== release locks, checked before anything moves =="
LOCKS="$OUT/release-locks.json"
{
  echo "{"
  sep=""
  for pl in "${PLUGINS[@]}"; do
    if [ -f "$WS/$pl/.osp/release-lock.json" ]; then
      if uv run --quiet "$WS/build-kit/scripts/osp.py" lock "$WS/$pl" --check >/dev/null 2>&1; then
        v="current"
      else
        v="STALE"
      fi
    else
      v="no release lock"
    fi
    echo "  $sep\"$pl\": \"$v\""
    sep=","
    echo "  $pl: $v" >&2
    [ "$v" != "STALE" ] || { echo "ERROR: $pl has a stale release lock; the run would not describe a released tree" >&2; exit 1; }
  done
  echo "}"
} > "$LOCKS" || exit 1
echo "wrote $LOCKS"

echo "== bundle-ON arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --model "$MODEL" --bundle on --no-lock-check --leak-check "$MARKS" "${QUAR_ON[@]}" --out "$OUT/results_on.json" \
  --transcripts "$OUT/transcripts_on" $EXTRA || {
    echo "ERROR: the bundle-ON arm failed; not spending the bundle-OFF arm after it"
    exit 1
  }

echo "== bundle-OFF arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --model "$MODEL" --bundle off --no-lock-check --leak-check "$MARKS" "${QUAR_OFF[@]}" --out "$OUT/results_off.json" \
  --transcripts "$OUT/transcripts_off" $EXTRA || {
    echo "ERROR: the bundle-OFF arm failed"
    exit 1
  }

check_restored; trap - EXIT INT TERM

# A run that kept no transcript is not the pre-registered run, so say so
# rather than let it pass quietly into the scoreboard.
for arm in on off; do
  [ -d "$OUT/transcripts_$arm" ] && [ -n "$(ls -A "$OUT/transcripts_$arm" 2>/dev/null)" ] || {
    echo "ERROR: the $arm arm kept no transcripts under $OUT/transcripts_$arm; the analysis commitments require them"
    exit 1
  }
done
echo "transcripts kept: $(find "$OUT/transcripts_on" "$OUT/transcripts_off" -name 'trial*.txt' | wc -l) trial files"

# An arm in which a case produced no valid trial measured nothing, and both
# arms failing that way render as a clean symmetric null: rate 0.0 against rate
# 0.0, which is the shape of the result the go and stop conditions turn on. An
# outage must not be publishable as a finding, so it stops here.
python - "$OUT/results_on.json" "$OUT/results_off.json" <<'GUARD' || exit 1
import json, sys
bad = []
for path in sys.argv[1:]:
    d = json.load(open(path))
    for c in d.get("cases", []):
        if not c.get("trials"):
            bad.append(f"{d.get('bundle')} arm, {c['id']}: 0 valid trials, {c.get('errors', 0)} errored")
if bad:
    print("ERROR: a case measured nothing, so this run is an outage and not a result:")
    for b in bad:
        print("  " + b)
    print("Read the transcripts before rerunning; a rate of 0.0 in both arms is not a null.")
    sys.exit(1)
GUARD

echo "== delta scoreboard =="
python "$WS/evals/runner/scoreboard.py" "$OUT/results_on.json" "$OUT/results_off.json" \
  --out "$OUT/ablation.html"
echo "ABLATION_DONE"
