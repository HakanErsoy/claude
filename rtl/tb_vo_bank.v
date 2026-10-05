// Testbench: streams {type, aidx, x} words from STIM_FILE through
// vo_bank_core and writes each out_y (hex, two's complement) to OUT_FILE.
`timescale 1ns/1ps
module tb_vo_bank;
    parameter K   = 32;
    parameter P   = 1024;
    parameter AW  = 10;
    parameter WS  = 36;
    parameter WST = 49;
    parameter WM  = 18;
    parameter SB  = 7;
    parameter N   = 1000;
    parameter COEF_FILE  = "coef.mem";
    parameter UPOLE_FILE = "upole.mem";
    parameter GAIN_FILE  = "gain.mem";
    parameter STIM_FILE  = "stim.mem";
    parameter OUT_FILE   = "out.txt";

    localparam SW = 2 + AW + WS;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg in_valid = 1'b0;
    reg [1:0] in_type = 2'd0;
    reg [AW-1:0] in_aidx = 0;
    reg signed [WS-1:0] in_x = 0;
    wire in_ready, out_valid;
    wire signed [WS-1:0] out_y;

    always #2.5 clk = ~clk;      // 200 MHz

    vo_bank_core #(.K(K), .P(P), .AW(AW), .WS(WS), .WST(WST), .WM(WM), .SB(SB),
                   .COEF_FILE(COEF_FILE), .UPOLE_FILE(UPOLE_FILE), .GAIN_FILE(GAIN_FILE))
        dut (.clk(clk), .rst(rst), .in_valid(in_valid), .in_ready(in_ready), .in_type(in_type),
             .in_aidx(in_aidx), .in_x(in_x), .out_valid(out_valid), .out_y(out_y));

    reg [SW-1:0] stim [0:N-1];
    integer i, fo;
    integer t_start, t_end;

    initial begin
        $readmemh(STIM_FILE, stim);
        fo = $fopen(OUT_FILE, "w");
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        @(posedge clk);
        t_start = $time;
        for (i = 0; i < N; i = i + 1) begin
            while (!in_ready) @(posedge clk);
            in_type  <= stim[i][SW-1:SW-2];
            in_aidx  <= stim[i][SW-3:WS];
            in_x     <= stim[i][WS-1:0];
            in_valid <= 1'b1;
            @(posedge clk);
            in_valid <= 1'b0;
            while (!out_valid) @(posedge clk);
            $fwrite(fo, "%h\n", out_y);
        end
        t_end = $time;
        $fclose(fo);
        $display("SAMPLES %0d CYCLES_PER_SAMPLE %0d", N, (t_end - t_start) / 5 / N);
        $finish;
    end
endmodule
