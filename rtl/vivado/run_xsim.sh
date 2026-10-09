#!/usr/bin/env bash
# xsim parity for one configuration: runs tb_vo_bank on the ROMs and vectors in
# rtl/build/<cfg>/ inside a scratch directory and compares the produced out.txt
# with the committed rtl/build/<cfg>/out.txt byte for byte.
#   usage: rtl/vivado/run_xsim.sh <cfg> [workdir]
#   VIVADO_BIN defaults to D:/Vivado/2026.1/Vivado/bin
set -euo pipefail
cfg=$1
here=$(cd "$(dirname "$0")/.." && pwd)
bin=${VIVADO_BIN:-/d/Vivado/2026.1/Vivado/bin}
case $cfg in
  WS36_WM16) WS=36; WST=49; WM=16; N=31744 ;;
  WS48_WM25) WS=48; WST=61; WM=25; N=62464 ;;
  *) echo "unknown cfg $cfg"; exit 2 ;;
esac
work=${2:-$(mktemp -d)}
mkdir -p "$work"
cp "$here/build/$cfg/"{coef,upole,gain,stim}.mem "$work/"
cd "$work"
"$bin/xvlog.bat" "$here/vo_bank_core.v" "$here/tb_vo_bank.v" > xvlog.out 2>&1
# options go through a file: cmd.exe splits "K=32" at '=' when it is passed to a .bat
printf '%s\n' tb_vo_bank -generic_top K=32 -generic_top WS=$WS -generic_top WST=$WST \
    -generic_top WM=$WM -generic_top N=$N -s tb > xelab.opt
"$bin/xelab.bat" -f xelab.opt > xelab.out 2>&1
"$bin/xsim.bat" tb -R > xsim.out 2>&1
grep -h "SAMPLES" xsim.out || true
# compare with the committed bytes; xsim on Windows and a core.autocrlf
# checkout both write CRLF, so line ends are normalised on the xsim side
tr -d '\r' < out.txt > out_lf.txt
git -C "$here/.." show "HEAD:rtl/build/$cfg/out.txt" > expected.txt
if cmp -s out_lf.txt expected.txt; then
  echo "$cfg PARITY OK ($(wc -l < out.txt) lines identical)"
else
  echo "$cfg PARITY FAIL"; exit 1
fi
