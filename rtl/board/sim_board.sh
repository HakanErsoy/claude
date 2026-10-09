#!/usr/bin/env bash
# xsim run of tb_board_top for one configuration, then check_sim.py.
#   usage: rtl/board/sim_board.sh <cfg> [workdir]
set -euo pipefail
cfg=$1
here=$(cd "$(dirname "$0")" && pwd)
rtl=$(cd "$here/.." && pwd)
bin=${VIVADO_BIN:-/d/Vivado/2026.1/Vivado/bin}
case $cfg in
  WS36_WM16) WS=36; WST=49; WM=16; TYPE=0 ;;
  WS48_WM25) WS=48; WST=61; WM=25; TYPE=2 ;;
  *) echo "unknown cfg $cfg"; exit 2 ;;
esac
work=${2:-$(mktemp -d)}
mkdir -p "$work"
cp "$rtl/build/$cfg/"{coef,upole,gain,stim}.mem "$work/"
cd "$work"
"$bin/xvlog.bat" "$rtl/vo_bank_core.v" "$here/board_top.v" "$here/tb_board_top.v" > xvlog.out 2>&1
# options through a file: cmd.exe splits "WS=48" at '=' when it is passed to a .bat
printf '%s\n' tb_board_top -generic_top WS=$WS -generic_top WST=$WST -generic_top WM=$WM \
    -generic_top LR_TYPE=$TYPE -s tbb > xelab.opt
"$bin/xelab.bat" -f xelab.opt > xelab.out 2>&1
"$bin/xsim.bat" tbb -R > xsim.out 2>&1
grep -h "TB DONE" xsim.out
python "$here/check_sim.py" "$cfg" "$work" "$TYPE"
