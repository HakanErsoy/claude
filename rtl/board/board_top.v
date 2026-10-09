// board_top: AXI4-Lite wrapper around vo_bank_core for the PYNQ-Z1 board
// measurements. The core is instantiated unmodified.
//
// Two modes share the core input:
//   * single sample (parity): the PS writes x and {type, aidx}; the write to
//     CMD raises in_valid until the core accepts; out_y is latched.
//   * long run: an on-chip 32-bit Galois LFSR feeds the core with in_valid
//     held high, so samples follow back to back. Per block of 2^LB outputs
//     the wrapper stores max|y|, sum y^2, a CRC-32 of the outputs and the
//     number of outputs with |y| >= 2^(WS-2). The first CAP_N outputs are
//     also captured verbatim.
//
// Cycle counters: LAT = cycles from the accept cycle (in_valid & in_ready)
// to the out_valid cycle; PER = cycles between consecutive accepts.
//
// Register map (byte addresses, 32-bit words) is in rtl/board/README.md.

module board_top #(
    parameter K   = 32,
    parameter P   = 1024,
    parameter AW  = 10,
    parameter WS  = 48,
    parameter WST = 61,
    parameter WM  = 25,
    parameter SB  = 7,
    parameter CAP_LOG2 = 12            // captured outputs: 2^CAP_LOG2
) (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET aresetn" *)
    input  wire        aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input  wire        aresetn,

    input  wire [7:0]  s_axi_awaddr,
    input  wire [2:0]  s_axi_awprot,
    input  wire        s_axi_awvalid,
    output reg         s_axi_awready,
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output reg         s_axi_wready,
    output wire [1:0]  s_axi_bresp,
    output reg         s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [7:0]  s_axi_araddr,
    input  wire [2:0]  s_axi_arprot,
    input  wire        s_axi_arvalid,
    output reg         s_axi_arready,
    output reg  [31:0] s_axi_rdata,
    output wire [1:0]  s_axi_rresp,
    output reg         s_axi_rvalid,
    input  wire        s_axi_rready
);

    localparam [31:0] ID = 32'h564F4231;          // "VOB1"
    localparam CAP_N = 1 << CAP_LOG2;
    localparam [31:0] LFSR_MASK = 32'h80200003;    // x^32 + x^22 + x^2 + x + 1
    localparam LFSR_STEPS = 32;                    // Galois steps per sample

    assign s_axi_bresp = 2'b00;
    assign s_axi_rresp = 2'b00;

    // ------------------------------------------------------------ counters
    reg [63:0] cyc;
    always @(posedge aclk)
        if (!aresetn) cyc <= 0; else cyc <= cyc + 1'b1;

    // ------------------------------------------------------------ registers
    reg  [3:0]  rst_cnt;
    wire        core_rst = !aresetn || (rst_cnt != 0);
    reg  [63:0] x_reg;
    reg  [15:0] s_aidx;
    reg  [1:0]  s_type;
    reg         s_valid;
    reg  [63:0] y_reg;
    reg         y_valid;
    reg  [31:0] nsamp;
    reg  [31:0] lat_last, lat_min, lat_max, per_last, per_min, per_max;
    reg  [63:0] t_acc, t_prev;
    reg         have_prev;
    reg  [31:0] cyc_hi_shadow;

    reg  [15:0] lr_aidx;
    reg  [1:0]  lr_type;
    reg  [4:0]  lr_lgn, lr_lgb;
    reg  [31:0] lr_seed;
    reg         lr_running, lr_done;
    reg  [31:0] lfsr;
    reg  [5:0]  gen_cnt;
    reg         x_rdy;
    reg  [31:0] issued, ocount, bcount;
    reg  [8:0]  nblk;
    reg  [63:0] lr_t0, lr_cyc;
    reg  [8:0]  blk_addr;
    reg  [CAP_LOG2-1:0] cap_addr;

    wire [31:0] lr_n    = 32'd1 << lr_lgn;
    wire [31:0] lr_bm1  = (32'd1 << lr_lgb) - 1'b1;

    // write-side pulses
    reg ctrl_rst_p, ctrl_start_p, cmd_p;

    // ------------------------------------------------------------ core
    wire                 in_ready, out_valid;
    wire signed [WS-1:0] out_y;
    wire signed [31:0]   lfsr_s = lfsr;
    wire signed [31:0]   lr_x32 = lfsr_s >>> 10;     // |x| <= 2^21 = 0.25 at F = 23
    wire signed [WS-1:0] lr_x   = lr_x32;            // sign extension
    wire                 lr_in_valid = lr_running && x_rdy && (issued < lr_n);
    wire                 c_in_valid  = lr_running ? lr_in_valid : s_valid;
    wire [1:0]           c_type      = lr_running ? lr_type : s_type;
    wire [AW-1:0]        c_aidx      = lr_running ? lr_aidx[AW-1:0] : s_aidx[AW-1:0];
    wire signed [WS-1:0] c_x         = lr_running ? lr_x : x_reg[WS-1:0];
    wire                 accept      = c_in_valid && in_ready;

    vo_bank_core #(.K(K), .P(P), .AW(AW), .WS(WS), .WST(WST), .WM(WM), .SB(SB)) core (
        .clk(aclk), .rst(core_rst),
        .in_valid(c_in_valid), .in_ready(in_ready),
        .in_type(c_type), .in_aidx(c_aidx), .in_x(c_x),
        .out_valid(out_valid), .out_y(out_y));

    // ------------------------------------------------------------ helpers
    function [31:0] crc32_64;                 // reflected CRC-32, LSB first
        input [31:0] c;
        input [63:0] d;
        integer i;
        reg [31:0] r;
        begin
            r = c;
            for (i = 0; i < 64; i = i + 1)
                r = (r[0] ^ d[i]) ? ((r >> 1) ^ 32'hEDB88320) : (r >> 1);
            crc32_64 = r;
        end
    endfunction

    function [31:0] lfsr_step;
        input [31:0] s;
        begin
            lfsr_step = s[0] ? ((s >> 1) ^ LFSR_MASK) : (s >> 1);
        end
    endfunction

    // ------------------------------------------------------------ block memories
    localparam RECW = 64 + 128 + 32 + 32;
    reg [RECW-1:0] blkmem [0:255];
    reg [RECW-1:0] blk_q;
    reg [WS-1:0]   capmem [0:CAP_N-1];
    reg [WS-1:0]   cap_q;
    always @(posedge aclk) begin
        blk_q <= blkmem[blk_addr];
        cap_q <= capmem[cap_addr];
    end

    // output-side pipeline of the long run (outputs are >= 4K+7 cycles apart)
    reg  [1:0]          ph;
    reg  signed [WS-1:0] y_r;
    reg  [2*WS-1:0]     sq_r;
    reg  [WS-1:0]       abs_r;
    reg  [31:0]         crc_n, crc;
    reg  [127:0]        sumsq;
    reg  [63:0]         maxabs;
    reg  [31:0]         ghits;
    wire [WS-1:0]       abs_y = y_r[WS-1] ? (~y_r + 1'b1) : y_r;
    wire [63:0]         y_r64 = {{(64-WS){y_r[WS-1]}}, y_r};
    wire [WS-1:0]       GUARD = {2'b01, {(WS-2){1'b0}}};

    always @(posedge aclk) begin
        if (core_rst || ctrl_start_p) begin
            ph <= 0; crc <= 32'hFFFFFFFF; sumsq <= 0; maxabs <= 0; ghits <= 0;
            ocount <= 0; bcount <= 0; nblk <= 0;
        end else begin
            case (ph)
                2'd0: if (out_valid && lr_running) begin
                    y_r <= out_y;
                    if (ocount < CAP_N) capmem[ocount[CAP_LOG2-1:0]] <= out_y;
                    ph <= 2'd1;
                end
                2'd1: begin
                    sq_r  <= y_r * y_r;
                    abs_r <= abs_y;
                    crc_n <= crc32_64(crc, y_r64);
                    ph <= 2'd2;
                end
                2'd2: begin
                    sumsq  <= sumsq + {{(128-2*WS){1'b0}}, sq_r};
                    if ({{(64-WS){1'b0}}, abs_r} > maxabs) maxabs <= {{(64-WS){1'b0}}, abs_r};
                    crc    <= crc_n;
                    if (abs_r >= GUARD) ghits <= ghits + 1'b1;
                    ocount <= ocount + 1'b1;
                    if (bcount == lr_bm1) begin
                        bcount <= 0;
                        ph <= 2'd3;
                    end else begin
                        bcount <= bcount + 1'b1;
                        ph <= 2'd0;
                    end
                end
                2'd3: begin
                    blkmem[nblk[7:0]] <= {ghits, ~crc, sumsq, maxabs};
                    nblk   <= nblk + 1'b1;
                    crc    <= 32'hFFFFFFFF; sumsq <= 0; maxabs <= 0; ghits <= 0;
                    ph <= 2'd0;
                end
            endcase
        end
    end

    // ------------------------------------------------------------ control
    always @(posedge aclk) begin
        if (!aresetn) begin
            rst_cnt <= 4'd8;
        end else if (ctrl_rst_p) begin
            rst_cnt <= 4'd8;
        end else if (rst_cnt != 0) begin
            rst_cnt <= rst_cnt - 1'b1;
        end
    end

    always @(posedge aclk) begin
        if (core_rst) begin
            s_valid <= 0; y_valid <= 0; y_reg <= 0; nsamp <= 0;
            lat_last <= 0; lat_min <= 32'hFFFFFFFF; lat_max <= 0;
            per_last <= 0; per_min <= 32'hFFFFFFFF; per_max <= 0;
            have_prev <= 0; t_acc <= 0; t_prev <= 0;
            lr_running <= 0; lr_done <= 0; x_rdy <= 0; gen_cnt <= 0; issued <= 0;
            lr_cyc <= 0; lr_t0 <= 0;
        end else begin
            // single-sample command
            if (cmd_p && !lr_running) begin
                s_valid <= 1'b1;
                y_valid <= 1'b0;
            end
            // long-run start
            if (ctrl_start_p && !lr_running) begin
                lr_running <= 1'b1; lr_done <= 1'b0;
                lfsr <= lr_seed; gen_cnt <= LFSR_STEPS; x_rdy <= 1'b0; issued <= 0;
                lat_min <= 32'hFFFFFFFF; lat_max <= 0; per_min <= 32'hFFFFFFFF; per_max <= 0;
                have_prev <= 1'b0;
                lr_t0 <= cyc;
            end
            // LFSR: LFSR_STEPS Galois steps per sample, then x is ready
            if (gen_cnt != 0) begin
                lfsr <= lfsr_step(lfsr);
                gen_cnt <= gen_cnt - 1'b1;
                if (gen_cnt == 1) x_rdy <= 1'b1;
            end
            // accept
            if (accept) begin
                t_acc <= cyc;
                if (have_prev) begin
                    per_last <= cyc - t_prev;
                    if (cyc - t_prev < per_min) per_min <= cyc - t_prev;
                    if (cyc - t_prev > per_max) per_max <= cyc - t_prev;
                end
                t_prev <= cyc;
                have_prev <= 1'b1;
                if (lr_running) begin
                    issued <= issued + 1'b1;
                    x_rdy <= 1'b0;
                    gen_cnt <= LFSR_STEPS;
                end else begin
                    s_valid <= 1'b0;
                end
            end
            // output
            if (out_valid) begin
                y_reg <= {{(64-WS){out_y[WS-1]}}, out_y};
                y_valid <= 1'b1;
                nsamp <= nsamp + 1'b1;
                lat_last <= cyc - t_acc;
                if (cyc - t_acc < lat_min) lat_min <= cyc - t_acc;
                if (cyc - t_acc > lat_max) lat_max <= cyc - t_acc;
            end
            // long-run end: last block record written
            if (lr_running && ph == 2'd3 && ocount == lr_n) begin
                lr_running <= 1'b0;
                lr_done <= 1'b1;
                lr_cyc <= cyc - lr_t0;
            end
        end
    end

    // ------------------------------------------------------------ AXI4-Lite write
    always @(posedge aclk) begin
        if (!aresetn) begin
            s_axi_awready <= 0; s_axi_wready <= 0; s_axi_bvalid <= 0;
            ctrl_rst_p <= 0; ctrl_start_p <= 0; cmd_p <= 0;
            x_reg <= 0; s_aidx <= 0; s_type <= 0;
            lr_aidx <= 0; lr_type <= 0; lr_lgn <= 5'd24; lr_lgb <= 5'd16; lr_seed <= 32'h1;
            blk_addr <= 0; cap_addr <= 0;
        end else begin
            ctrl_rst_p <= 0; ctrl_start_p <= 0; cmd_p <= 0;
            s_axi_awready <= 0; s_axi_wready <= 0;
            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
            if (s_axi_awvalid && s_axi_wvalid && !s_axi_awready && !s_axi_bvalid) begin
                s_axi_awready <= 1; s_axi_wready <= 1; s_axi_bvalid <= 1;
                case (s_axi_awaddr[7:2])
                    6'h00: begin ctrl_rst_p <= s_axi_wdata[0]; ctrl_start_p <= s_axi_wdata[1]; end
                    6'h02: x_reg[31:0]  <= s_axi_wdata;
                    6'h03: x_reg[63:32] <= s_axi_wdata;
                    6'h04: begin s_aidx <= s_axi_wdata[15:0]; s_type <= s_axi_wdata[17:16]; cmd_p <= 1; end
                    6'h10: begin lr_aidx <= s_axi_wdata[15:0]; lr_type <= s_axi_wdata[17:16];
                                 lr_lgn <= s_axi_wdata[28:24]; end
                    6'h11: lr_lgb  <= s_axi_wdata[4:0];
                    6'h12: lr_seed <= s_axi_wdata;
                    6'h16: blk_addr <= s_axi_wdata[8:0];
                    6'h1F: cap_addr <= s_axi_wdata[CAP_LOG2-1:0];
                    default: ;
                endcase
            end
        end
    end

    // ------------------------------------------------------------ AXI4-Lite read
    always @(posedge aclk) begin
        if (!aresetn) begin
            s_axi_arready <= 0; s_axi_rvalid <= 0; s_axi_rdata <= 0; cyc_hi_shadow <= 0;
        end else begin
            s_axi_arready <= 0;
            if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
            if (s_axi_arvalid && !s_axi_arready && !s_axi_rvalid) begin
                s_axi_arready <= 1; s_axi_rvalid <= 1;
                case (s_axi_araddr[7:2])
                    6'h01: s_axi_rdata <= {26'd0, (rst_cnt != 0), in_ready, lr_done, lr_running, y_valid, s_valid};
                    6'h02: s_axi_rdata <= x_reg[31:0];
                    6'h03: s_axi_rdata <= x_reg[63:32];
                    6'h05: s_axi_rdata <= y_reg[31:0];
                    6'h06: s_axi_rdata <= y_reg[63:32];
                    6'h07: s_axi_rdata <= nsamp;
                    6'h08: s_axi_rdata <= lat_last;
                    6'h09: s_axi_rdata <= lat_min;
                    6'h0A: s_axi_rdata <= lat_max;
                    6'h0B: s_axi_rdata <= per_last;
                    6'h0C: s_axi_rdata <= per_min;
                    6'h0D: s_axi_rdata <= per_max;
                    6'h0E: begin s_axi_rdata <= cyc[31:0]; cyc_hi_shadow <= cyc[63:32]; end
                    6'h0F: s_axi_rdata <= cyc_hi_shadow;
                    6'h10: s_axi_rdata <= {3'd0, lr_lgn, 6'd0, lr_type, lr_aidx};
                    6'h11: s_axi_rdata <= {27'd0, lr_lgb};
                    6'h12: s_axi_rdata <= lr_seed;
                    6'h13: s_axi_rdata <= {23'd0, nblk};
                    6'h14: s_axi_rdata <= lr_cyc[31:0];
                    6'h15: s_axi_rdata <= lr_cyc[63:32];
                    6'h16: s_axi_rdata <= {23'd0, blk_addr};
                    6'h17: s_axi_rdata <= blk_q[31:0];        // max|y| low
                    6'h18: s_axi_rdata <= blk_q[63:32];       // max|y| high
                    6'h19: s_axi_rdata <= blk_q[95:64];       // sum y^2, word 0
                    6'h1A: s_axi_rdata <= blk_q[127:96];
                    6'h1B: s_axi_rdata <= blk_q[159:128];
                    6'h1C: s_axi_rdata <= blk_q[191:160];     // sum y^2, word 3
                    6'h1D: s_axi_rdata <= blk_q[223:192];     // CRC-32
                    6'h1E: s_axi_rdata <= blk_q[255:224];     // outputs with |y| >= 2^(WS-2)
                    6'h1F: s_axi_rdata <= {{(32-CAP_LOG2){1'b0}}, cap_addr};
                    6'h20: s_axi_rdata <= cap_q[31:0];
                    6'h21: s_axi_rdata <= {{(64-WS){cap_q[WS-1]}}, cap_q[WS-1:32]};
                    6'h22: s_axi_rdata <= {WM[7:0], WST[7:0], WS[7:0], K[7:0]};
                    6'h23: s_axi_rdata <= ID;
                    6'h24: s_axi_rdata <= issued;
                    6'h25: s_axi_rdata <= ocount;
                    default: s_axi_rdata <= 32'hDEADBEEF;
                endcase
            end
        end
    end

endmodule
