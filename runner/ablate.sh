#!/usr/bin/env bash
# Ablation harness: run the gotcha-avoidance suite bundle-ON, then bundle-OFF
# (knowledge/ stripped from the installed plugin cache), then render the delta.
# The knowledge/ directory is ALWAYS restored, even on error or interrupt.
#
# Usage: ablate.sh <workspace> <trials> <out_dir> [--no-judge]
set -uo pipefail
WS="$1"; TRIALS="$2"; OUT="$3"; shift 3; EXTRA="${*:-}"
MAN="$WS/evals/manifests/ablation.yaml"
KDIR="$HOME/.claude/plugins/cache/open-science-pillars/ocean-science/0.3.0/knowledge"
KOFF="${KDIR}.ABLATION_OFF"
mkdir -p "$OUT"

restore() { [ -d "$KOFF" ] && mv "$KOFF" "$KDIR" && echo "restored knowledge/"; }
trap restore EXIT INT TERM

echo "== bundle-ON arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --bundle on --out "$OUT/results_on.json" $EXTRA

echo "== stripping knowledge/ for the bundle-OFF arm =="
[ -d "$KDIR" ] || { echo "ERROR: knowledge dir not found at $KDIR"; exit 1; }
mv "$KDIR" "$KOFF"

echo "== bundle-OFF arm =="
python "$WS/evals/runner/run_evals.py" --manifest "$MAN" --workspace "$WS" \
  --trials "$TRIALS" --bundle off --out "$OUT/results_off.json" $EXTRA

restore; trap - EXIT INT TERM

echo "== delta scoreboard =="
python "$WS/evals/runner/scoreboard.py" "$OUT/results_on.json" "$OUT/results_off.json" \
  --out "$OUT/ablation.html"
echo "ABLATION_DONE"
