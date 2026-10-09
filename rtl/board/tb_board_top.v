// Simulation of board_top through its AXI4-Lite port, before the bitstream:
//   1. single-sample mode on the first NS vectors of stim.mem (out: sim_single.txt)
//   2. a short long run (2^LGN samples, blocks of 2^LGB) (out: sim_long.txt)
// rtl/board/sim_board.sh runs it and check_sim.py compares with the golden model.
`timescale 1ns/1ps
module tb_board_top;
    parameter K   = 32;
    parameter P   = 1024;
    parameter AW  = 10;
    parameter WS  = 48;
    parameter WST = 61;
    parameter WM  = 25;
    parameter NS  = 600;
    parameter LGN = 11;
    parameter LGB = 8;
    parameter LR_AIDX = 51;
    parameter LR_TYPE = 2;
    parameter LR_SEED = 32'h9E3779B9;

    localparam SW = 2 + AW + WS;

    reg clk = 0, aresetn = 0;
    always #5 clk = ~clk;

    reg  [7:0]  awaddr = 0, araddr = 0;
    reg         awvalid = 0, wvalid = 0, arvalid = 0;
    reg  [31:0] wdata = 0;
    wire        awready, wready, bvalid, arready, rvalid;
    wire [31:0] rdata;
    wire [1:0]  bresp, rresp;

    board_top #(.K(K), .P(P), .AW(AW), .WS(WS), .WST(WST), .WM(WM)) dut (
        .aclk(clk), .aresetn(aresetn),
        .s_axi_awaddr(awaddr), .s_axi_awprot(3'b0), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(4'hF), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(1'b1),
        .s_axi_araddr(araddr), .s_axi_arprot(3'b0), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(1'b1));

    task wr(input [7:0] a, input [31:0] d);
        begin
            awaddr <= a; wdata <= d; awvalid <= 1; wvalid <= 1;
            @(posedge clk);
            while (!awready) @(posedge clk);
            awvalid <= 0; wvalid <= 0;
            @(posedge clk);
        end
    endtask

    task rd(input [7:0] a, output [31:0] d);
        begin
            araddr <= a; arvalid <= 1;
            @(posedge clk);
            while (!arready) @(posedge clk);
            arvalid <= 0;
            d = rdata;
            @(posedge clk);
        end
    endtask

    reg [SW-1:0] stim [0:NS-1];
    reg [31:0] r, r2, w [0:7];
    integer i, j, fo;
    reg [WS-1:0] xv;

    initial begin
        $readmemh("stim.mem", stim);
        repeat (10) @(posedge clk);
        aresetn <= 1;
        repeat (20) @(posedge clk);
        rd(8'h8C, r); $display("ID %h", r);
        rd(8'h88, r); $display("PARAMS %h", r);

        // ---- single-sample mode
        fo = $fopen("sim_single.txt", "w");
        wr(8'h00, 32'h1);
        repeat (20) @(posedge clk);
        for (i = 0; i < NS; i = i + 1) begin
            xv = stim[i][WS-1:0];
            wr(8'h08, xv[31:0]);
            wr(8'h0C, {{(64-WS){1'b0}}, xv[WS-1:32]});
            wr(8'h10, {14'd0, stim[i][SW-1:SW-2], 6'd0, stim[i][SW-3:WS]});
            r = 0;
            while (!r[1]) rd(8'h04, r);
            rd(8'h14, r); rd(8'h18, r2);
            $fwrite(fo, "%h%h\n", r2, r);
        end
        rd(8'h1C, r); $fwrite(fo, "NSAMP %0d\n", r);
        rd(8'h20, r); $fwrite(fo, "LAT_LAST %0d\n", r);
        rd(8'h24, r); $fwrite(fo, "LAT_MIN %0d\n", r);
        rd(8'h28, r); $fwrite(fo, "LAT_MAX %0d\n", r);
        $fclose(fo);

        // ---- long run
        fo = $fopen("sim_long.txt", "w");
        wr(8'h00, 32'h1);
        repeat (20) @(posedge clk);
        wr(8'h40, (LGN << 24) | (LR_TYPE << 16) | LR_AIDX);
        wr(8'h44, LGB);
        wr(8'h48, LR_SEED);
        wr(8'h00, 32'h2);
        r = 0;
        while (!r[3]) begin
            repeat (200) @(posedge clk);
            rd(8'h04, r);
        end
        rd(8'h4C, r); $fwrite(fo, "NBLK %0d\n", r);
        rd(8'h50, r); rd(8'h54, r2); $fwrite(fo, "LR_CYC %0d\n", {r2, r});
        rd(8'h90, r); $fwrite(fo, "ISSUED %0d\n", r);
        rd(8'h94, r); $fwrite(fo, "OCOUNT %0d\n", r);
        rd(8'h1C, r); $fwrite(fo, "NSAMP %0d\n", r);
        rd(8'h24, r); $fwrite(fo, "LAT_MIN %0d\n", r);
        rd(8'h28, r); $fwrite(fo, "LAT_MAX %0d\n", r);
        rd(8'h30, r); $fwrite(fo, "PER_MIN %0d\n", r);
        rd(8'h34, r); $fwrite(fo, "PER_MAX %0d\n", r);
        for (i = 0; i < (1 << (LGN - LGB)); i = i + 1) begin
            wr(8'h58, i);
            for (j = 0; j < 8; j = j + 1) rd(8'h5C + 4 * j, w[j]);
            $fwrite(fo, "BLK %0d %h%h %h%h%h%h %h %0d\n", i, w[1], w[0], w[5], w[4], w[3], w[2], w[6], w[7]);
        end
        for (i = 0; i < (1 << LGN) && i < 4096; i = i + 1) begin
            wr(8'h7C, i);
            rd(8'h80, r); rd(8'h84, r2);
            $fwrite(fo, "CAP %0d %h%h\n", i, r2, r);
        end
        $fclose(fo);
        $display("TB DONE");
        $finish;
    end
endmodule
