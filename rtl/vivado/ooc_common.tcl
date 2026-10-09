# Out-of-context synthesis + implementation of vo_bank_core for one
# configuration. Sourced by ooc_<cfg>.tcl, which sets CFG, WS, WST and WM.
#
#   vivado -mode batch -source rtl/vivado/ooc_<cfg>.tcl -tclargs <period_ns> <outdir>
#
# Non-project flow, default synthesis and implementation directives. The ROMs
# are read from rtl/build/<cfg>/ (coef.mem, upole.mem, gain.mem). Only the
# register-to-register paths of the core are constrained: in OOC mode the
# ports have no I/O buffers and no I/O delays are set.

set PART xc7z020clg400-1
set here [file normalize [file dirname [info script]]]
set rtl  [file normalize $here/..]
set bdir $rtl/build/$CFG

set period [lindex $argv 0]
set outdir [file normalize [lindex $argv 1]]
file mkdir $outdir
cd $outdir

foreach m {coef upole gain} {
    file copy -force $bdir/$m.mem $outdir/$m.mem
}

set xdc $outdir/clk.xdc
set fh [open $xdc w]
puts $fh "create_clock -period $period -name clk \[get_ports clk\]"
close $fh

read_verilog $rtl/vo_bank_core.v
read_mem [list $outdir/coef.mem $outdir/upole.mem $outdir/gain.mem]
read_xdc -mode out_of_context $xdc

synth_design -top vo_bank_core -part $PART -mode out_of_context \
    -generic K=32 -generic P=1024 -generic AW=10 \
    -generic WS=$WS -generic WST=$WST -generic WM=$WM -generic SB=7
opt_design
place_design
route_design

report_utilization    -file $outdir/utilization.rpt
report_timing_summary -file $outdir/timing_summary.rpt -max_paths 10

set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set whs [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -hold]]
set fh [open $outdir/summary.txt w]
puts $fh "cfg $CFG"
puts $fh "part $PART"
puts $fh "vivado [version -short]"
puts $fh "period_ns $period"
puts $fh "wns_ns $wns"
puts $fh "whs_ns $whs"
puts $fh "fmax_mhz [expr {1000.0 / ($period - $wns)}]"
close $fh
puts "OOC $CFG T=$period WNS=$wns WHS=$whs Fmax=[expr {1000.0 / ($period - $wns)}] MHz"
