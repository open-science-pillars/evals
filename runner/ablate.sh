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

# What a trial can read is not what the arm change controls. Setting the
# subprocess working directory does not confine it either: a headless run whose
# working directory was an empty temporary directory read an absolute path under
# the workspace without difficulty, checked on 2026-09-22. So the copies have to
# be absent, and absence is established by searching for the text rather than by
# predicting where copies live.
LEAK="$WS/evals/runner/leak_check.py"
CASE_ARG=""
case "$EXTRA" in *--cases*) CASE_ARG=$(echo "$EXTRA" | sed -n 's/.*--cases \([^ ]*\).*/--cases \1/p');; esac

mkdir -p "$OUT"

restore() {
  local back=0
  for k in "${KDIRS[@]}"; do
    [ -d "$k.ABLATION_OFF" ] && mv "$k.ABLATION_OFF" "$k" && back=$((back+1))
  done
  [ "$back" -gt 0 ] && echo "restored $back knowledge tree(s)"
  return 0
}
trap restore EXIT INT TERM

echo "== leak check, both arms: no recorded answer to a case may be readable =="
# shellcheck disable=SC2086
uv run --with pyyaml==6.0.2 "$LEAK" "$WS" "$MAN" --arm on $CASE_ARG || {
  echo "ERROR: an answer to a case in this run is readable from where the trials run."
  echo "It contaminates the rate in both arms, not only the difference between them."
  echo "Prepare a run workspace without those files and run again."
  exit 1
}

echo "== bundle-ON arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --model "$MODEL" --bundle on --out "$OUT/results_on.json" \
  --transcripts "$OUT/transcripts_on" $EXTRA || {
    echo "ERROR: the bundle-ON arm failed; not spending the bundle-OFF arm after it"
    exit 1
  }

echo "== stripping every cited knowledge tree for the bundle-OFF arm =="
for k in "${KDIRS[@]}"; do
  [ -d "$k" ] || { echo "ERROR: $k is not there to ablate"; exit 1; }
  echo "  ablating $k ($(find "$k" -name '*.md' | wc -l) concepts)"
  mv "$k" "$k.ABLATION_OFF"
done

echo "== leak check, bundle-OFF arm: no cited concept may be readable =="
# shellcheck disable=SC2086
uv run --with pyyaml==6.0.2 "$LEAK" "$WS" "$MAN" --arm off $CASE_ARG || {
  echo "ERROR: the arm moved its trees and the knowledge is still readable, so this"
  echo "arm is not off and would measure nothing. The trees are restored on exit."
  exit 1
}

echo "== bundle-OFF arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --model "$MODEL" --bundle off --out "$OUT/results_off.json" \
  --transcripts "$OUT/transcripts_off" $EXTRA || {
    echo "ERROR: the bundle-OFF arm failed"
    exit 1
  }

restore; trap - EXIT INT TERM

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
