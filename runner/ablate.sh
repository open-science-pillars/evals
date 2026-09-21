#!/usr/bin/env bash
# Ablation harness: run the gotcha-avoidance suite bundle-ON, then bundle-OFF
# (knowledge/ stripped from the installed plugin cache), then render the delta.
# The knowledge/ directory is ALWAYS restored, even on error or interrupt.
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
# Usage: ablate.sh <workspace> <trials> <out_dir> [--no-judge]
set -uo pipefail
WS="$1"; TRIALS="$2"; OUT="$3"; shift 3; EXTRA="${*:-}"
MAN="$WS/evals/manifests/ablation.yaml"
# The installed knowledge tree, found rather than pinned, in the marketplace
# as well as the version. This read open-science-pillars/ocean-science/0.3.0
# until 2026-09-21: four releases behind, and under a marketplace name that a
# candidate or release-candidate install does not use, so it matched nothing on
# the machine the qualification runs installed. Ablating the wrong tree would be
# worse than matching none, so more than one match is an error rather than a
# choice the script makes quietly.
KDIRS=$(ls -d "$HOME"/.claude/plugins/cache/*/ocean-science/*/knowledge 2>/dev/null | sort -V)
KCOUNT=$(printf '%s\n' "$KDIRS" | grep -c . || true)
if [ "$KCOUNT" -gt 1 ]; then
  echo "ERROR: ocean-science knowledge trees are installed from more than one marketplace;"
  echo "the ablation would not know which one the trials read. Found:"
  printf '  %s\n' $KDIRS
  echo "Leave exactly one installed and run again."
  exit 1
fi
KDIR=$(printf '%s\n' "$KDIRS" | tail -1)
KOFF="${KDIR:-/nonexistent}.ABLATION_OFF"
mkdir -p "$OUT"

restore() { [ -d "$KOFF" ] && mv "$KOFF" "$KDIR" && echo "restored knowledge/"; }
trap restore EXIT INT TERM

echo "== bundle-ON arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --bundle on --out "$OUT/results_on.json" \
  --transcripts "$OUT/transcripts_on" $EXTRA

echo "== stripping knowledge/ for the bundle-OFF arm =="
[ -n "$KDIR" ] && [ -d "$KDIR" ] || { echo "ERROR: no installed ocean-science knowledge tree under $HOME/.claude/plugins/cache/*/ocean-science/*/knowledge; install the capability before the ablation"; exit 1; }
echo "ablating $KDIR"
mv "$KDIR" "$KOFF"

echo "== bundle-OFF arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --bundle off --out "$OUT/results_off.json" \
  --transcripts "$OUT/transcripts_off" $EXTRA

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

echo "== delta scoreboard =="
python "$WS/evals/runner/scoreboard.py" "$OUT/results_on.json" "$OUT/results_off.json" \
  --out "$OUT/ablation.html"
echo "ABLATION_DONE"
