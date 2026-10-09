# Bitstream for the board measurements on PYNQ-Z1 (xc7z020clg400-1).
#
#   vivado -mode batch -source rtl/board/build_board.tcl -tclargs <cfg> <fclk_mhz> <outdir>
#
# Block design: processing_system7 (M_AXI_GP0, FCLK_CLK0 = <fclk_mhz>) ->
# AXI interconnect -> board_top (module reference) at 0x43C0_0000. board_top,
# its AXI port and the core all run on FCLK_CLK0. The ROMs come from
# rtl/build/<cfg>/ and are added to the project so that $readmemh finds them;
# the block design is synthesised globally (no per-IP out-of-context run).
# Outputs in <outdir>: vob_<cfg>.bit, vob_<cfg>.hwh, utilization.rpt,
# timing_summary.rpt, summary.txt.

set PART xc7z020clg400-1
set cfg    [lindex $argv 0]
set fclk   [lindex $argv 1]
set outdir [file normalize [lindex $argv 2]]
set here [file normalize [file dirname [info script]]]
set rtl  [file normalize $here/..]
switch $cfg {
    WS36_WM16 { set WS 36; set WST 49; set WM 16 }
    WS48_WM25 { set WS 48; set WST 61; set WM 25 }
    default   { error "unknown cfg $cfg" }
}

file mkdir $outdir
set prj $outdir/prj
create_project -force vob $prj -part $PART

foreach m {coef upole gain} { file copy -force $rtl/build/$cfg/$m.mem $outdir/$m.mem }
add_files -norecurse [list $rtl/vo_bank_core.v $here/board_top.v \
    $outdir/coef.mem $outdir/upole.mem $outdir/gain.mem]
update_compile_order -fileset sources_1

create_bd_design vob
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7 ps7
set_property -dict [list \
    CONFIG.PCW_CRYSTAL_PERIPHERAL_FREQMHZ {50} \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ $fclk \
] [get_bd_cells ps7]
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "0" Master "Disable" Slave "Disable"} [get_bd_cells ps7]

create_bd_cell -type module -reference board_top bt
set_property -dict [list CONFIG.WS $WS CONFIG.WST $WST CONFIG.WM $WM] [get_bd_cells bt]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master {/ps7/M_AXI_GP0} Slave {/bt/s_axi} Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
             ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} \
    [get_bd_intf_pins bt/s_axi]
set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces ps7/Data] -filter {NAME =~ *bt*}]
if {[llength $seg] != 1} { error "address segment of bt not found: $seg" }
set_property range 4K $seg
set_property offset 0x43C00000 $seg
validate_bd_design
save_bd_design

set bd [get_files vob.bd]
set_property synth_checkpoint_mode None $bd
generate_target all $bd
set wrapper [make_wrapper -files $bd -top]
add_files -norecurse $wrapper
set_property top vob_wrapper [current_fileset]
update_compile_order -fileset sources_1

launch_runs synth_1 -jobs 8
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] != "100%"} { error "synthesis failed" }
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] != "100%"} { error "implementation failed" }

open_run impl_1
report_utilization    -file $outdir/utilization.rpt
report_utilization    -hierarchical -file $outdir/utilization_hier.rpt
report_timing_summary -file $outdir/timing_summary.rpt -max_paths 10
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set whs [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -hold]]
set clk_period [get_property PERIOD [get_clocks clk_fpga_0]]

set impl_dir [get_property DIRECTORY [get_runs impl_1]]
file copy -force $impl_dir/vob_wrapper.bit $outdir/vob_$cfg.bit
set hwh [lindex [glob -nocomplain $prj/vob.gen/sources_1/bd/vob/hw_handoff/vob.hwh] 0]
file copy -force $hwh $outdir/vob_$cfg.hwh

set fh [open $outdir/summary.txt w]
puts $fh "cfg $cfg"
puts $fh "part $PART"
puts $fh "vivado [version -short]"
puts $fh "fclk_requested_mhz $fclk"
puts $fh "clk_fpga_0_period_ns $clk_period"
puts $fh "wns_ns $wns"
puts $fh "whs_ns $whs"
close $fh
puts "BOARD $cfg FCLK=$fclk period=$clk_period WNS=$wns WHS=$whs"
