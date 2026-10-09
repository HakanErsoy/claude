#!/usr/bin/env bash
# Fmax search for one configuration (BOARD_SESSION.md step 4.3): first run
# with a tight 5 ns constraint, then set the constraint to T - WNS of the
# previous run, until a run meets timing (WNS >= 0) or MAX_TRIALS is reached.
# Fmax = 1 / (T - WNS) of the last run that meets timing. Every trial is
# appended to rtl/build/<cfg>/vivado/fmax_search.txt; the reports of the final
# trial are copied to rtl/build/<cfg>/vivado/.
#   usage: rtl/vivado/fmax_search.sh <cfg> <workdir> [first_period_ns]
set -euo pipefail
cfg=$1
work=$2
T=${3:-5.0}
MAX_TRIALS=${MAX_TRIALS:-5}
here=$(cd "$(dirname "$0")" && pwd)
dest="$here/../build/$cfg/vivado"
vivado=${VIVADO_BAT:-/d/Vivado/2026.1/Vivado/bin/vivado.bat}
mkdir -p "$dest" "$work"
log="$dest/fmax_search.txt"
[ -f "$log" ] || echo "# trial period_ns wns_ns whs_ns fmax_mhz (OOC, default directives)" > "$log"
n=$(grep -vc '^#' "$log" || true)
while [ "$n" -lt "$MAX_TRIALS" ]; do
  n=$((n + 1))
  out="$work/${cfg}_T$T"
  if [ ! -f "$out/summary.txt" ]; then
    mkdir -p "$out"
    (cd "$out" && "$vivado" -mode batch -nojournal -log vivado.log -source "$here/ooc_$cfg.tcl" \
        -tclargs "$T" "$(cygpath -m "$out")" > stdout.txt 2>&1)
  fi
  wns=$(awk '/^wns_ns/{print $2}' "$out/summary.txt")
  whs=$(awk '/^whs_ns/{print $2}' "$out/summary.txt")
  fmax=$(awk '/^fmax_mhz/{print $2}' "$out/summary.txt")
  echo "$n $T $wns $whs $fmax" >> "$log"
  echo "trial $n: T=$T WNS=$wns Fmax=$fmax"
  if awk -v w="$wns" 'BEGIN{exit !(w >= 0)}'; then
    cp "$out/utilization.rpt" "$out/timing_summary.rpt" "$out/summary.txt" "$dest/"
    echo "met: $cfg Fmax=$fmax MHz at T=$T"
    exit 0
  fi
  # next constraint: the achieved period, rounded up to 0.01 ns
  T=$(awk -v t="$T" -v w="$wns" 'BEGIN{p=t-w; printf "%.2f", int(p*100+0.999)/100}')
done
echo "no trial met timing after $MAX_TRIALS trials"; exit 1
