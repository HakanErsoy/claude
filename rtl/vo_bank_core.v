// vo_bank_core: fixed-pole variable-order fractional operator, types A/B/D/E.
//
// Bit-exact with vofrac/fixedpoint.py (FixedPointBank.run). Sample units
// (Ts = 1, g0 = 1): D and E are exact algebraic inverses, v = x - hist,
// so no divider is needed. The order is a grid index read with every
// sample, so the order can change at every sample; the type can change too.
//
// Per sample, with p = in_aidx for A/B and P-1-in_aidx for D/E:
//   output schedule (A, D):
//     hist = mulsh(dl, C[p][K]) + sum_k mulsh(s_k, M_k, S_k + Go_k)
//     s_k += (v <<< Go_k) - mulsh(s_k, U_k);   dl = v
//   input schedule (B, E):
//     hist = dl + sum_k mulsh(s_k, 1, Gi_k)
//     s_k += mulsh(v, M_k, S_k - Gi_k) - mulsh(s_k, U_k);   dl = mulsh(v, C[p][K])
//   A, B: v = x, y = x + hist.   D, E: v = x - hist, y = v.
//   mulsh(a, M, S) = (a*M + 2^(S-1)) >>> S for S > 0, (a*M) <<< -S otherwise.
//
// Time-multiplexed: one mode per two cycles in each pass, 4K + 8 cycles per
// sample. ROMs are synchronous-read (block RAM).

module vo_bank_core #(
    parameter K   = 32,          // geometric modes (plus the delay mode)
    parameter P   = 1024,        // order grid size
    parameter AW  = 10,          // order index width
    parameter WS  = 36,          // signal word (x, v, y, hist)
    parameter WST = 49,          // state word
    parameter WM  = 18,          // coefficient mantissa
    parameter SB  = 7,           // shift field
    parameter COEF_FILE  = "coef.mem",
    parameter UPOLE_FILE = "upole.mem",
    parameter GAIN_FILE  = "gain.mem"
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire [1:0]            in_type,     // 0 A, 1 B, 2 D, 3 E
    input  wire [AW-1:0]         in_aidx,
    input  wire signed [WS-1:0]  in_x,
    output reg                   out_valid,
    output reg  signed [WS-1:0]  out_y
);

    localparam ROWS = K + 1;
    localparam CW   = WM + SB;
    localparam KW   = $clog2(ROWS + 1);
    localparam CAW  = $clog2(P * ROWS);
    localparam PW   = WST + WM + 2;          // product / shift width
    localparam AccW = WS + 8;

    // ---------------------------------------------------------------- ROMs
    reg [CW-1:0]     coef_rom  [0:P*ROWS-1];
    reg [CW-1:0]     upole_rom [0:K-1];
    reg [2*SB-1:0]   gain_rom  [0:K-1];
    initial begin
        $readmemh(COEF_FILE, coef_rom);
        $readmemh(UPOLE_FILE, upole_rom);
        $readmemh(GAIN_FILE, gain_rom);
    end

    reg signed [WST-1:0] st [0:K-1];

    // ---------------------------------------------------------- arithmetic
    function signed [PW-1:0] mulsh;
        input signed [PW-1:0] a;
        input signed [WM:0]   m;               // one extra bit so that m = 1 is exact
        input signed [9:0]    sh;
        reg   signed [PW-1:0] p;
        reg   signed [PW:0]   r;
        begin
            p = a * m;
            if (sh <= 0)
                mulsh = p <<< (-sh);
            else if (sh >= PW)
                mulsh = {PW{1'b0}};
            else begin
                r = $signed({p[PW-1], p}) + $signed({{PW{1'b0}}, 1'b1} << (sh - 1));
                mulsh = r >>> sh;
            end
        end
    endfunction

    // -------------------------------------------------------------- control
    localparam S_IDLE = 3'd0, S_HIST = 3'd1, S_CALC = 3'd2, S_UPD = 3'd3, S_OUT = 3'd4;
    reg [2:0]            phase;
    reg                  sub;                  // 0: fetch, 1: execute
    reg [KW-1:0]         k;
    reg [1:0]            typ;
    reg [CAW-1:0]        rowbase;
    reg signed [WS-1:0]  x_r, v_r, y_r;
    reg signed [WS-1:0]  dl;
    reg signed [AccW-1:0] acc;

    wire out_sched = (typ == 2'd0) || (typ == 2'd2);   // A, D
    wire inv       = typ[1];                           // D, E

    assign in_ready = (phase == S_IDLE);

    // synchronous ROM / state reads at the current mode index
    wire [CAW-1:0] caddr = rowbase + k;
    wire [KW-1:0]  kk    = (k < K) ? k : {KW{1'b0}};
    reg  [CW-1:0]     coef_q, u_q;
    reg  [2*SB-1:0]   g_q;
    reg  signed [WST-1:0] st_q;
    always @(posedge clk) begin
        coef_q <= coef_rom[caddr];
        u_q    <= upole_rom[kk];
        g_q    <= gain_rom[kk];
        st_q   <= st[kk];
    end

    wire signed [WM:0]  cM = {coef_q[CW-1], coef_q[CW-1:SB]};
    wire signed [9:0]   cS = {3'b000, coef_q[SB-1:0]};
    wire signed [WM:0]  uM = {u_q[CW-1], u_q[CW-1:SB]};
    wire signed [9:0]   uS = {3'b000, u_q[SB-1:0]};
    wire signed [9:0]   Go = {3'b000, g_q[2*SB-1:SB]};
    wire signed [9:0]   Gi = {3'b000, g_q[SB-1:0]};

    wire signed [PW-1:0] st_x = {{(PW-WST){st_q[WST-1]}}, st_q};
    wire signed [PW-1:0] dl_x = {{(PW-WS){dl[WS-1]}}, dl};
    wire signed [PW-1:0] v_x  = {{(PW-WS){v_r[WS-1]}}, v_r};
    wire signed [WM:0]   ONE  = {{WM{1'b0}}, 1'b1};

    // history term of mode k (k = K is the delay mode)
    wire signed [PW-1:0] hterm =
        (k == K) ? (out_sched ? mulsh(dl_x, cM, cS) : dl_x)
                 : (out_sched ? mulsh(st_x, cM, cS + Go) : mulsh(st_x, ONE, Gi));

    // state update of mode k
    wire signed [PW-1:0] decay = mulsh(st_x, uM, uS);
    wire signed [PW-1:0] drive = out_sched ? (v_x <<< Go) : mulsh(v_x, cM, cS - Gi);
    wire signed [PW-1:0] s_new = st_x + drive - decay;
    wire signed [PW-1:0] dl_in = mulsh(v_x, cM, cS);

    integer i;
    always @(posedge clk) begin
        if (rst) begin
            phase <= S_IDLE; sub <= 1'b0; k <= 0; out_valid <= 1'b0; dl <= 0; acc <= 0;
            for (i = 0; i < K; i = i + 1) st[i] <= 0;
        end else begin
            out_valid <= 1'b0;
            case (phase)
                S_IDLE: if (in_valid) begin
                    typ     <= in_type;
                    x_r     <= in_x;
                    rowbase <= (in_type[1] ? (P - 1 - in_aidx) : in_aidx) * ROWS;
                    k <= 0; sub <= 1'b0; acc <= 0;
                    phase <= S_HIST;
                end
                S_HIST: begin
                    if (!sub) sub <= 1'b1;
                    else begin
                        acc <= acc + hterm[AccW-1:0];
                        sub <= 1'b0;
                        if (k == K) phase <= S_CALC;
                        else k <= k + 1'b1;
                    end
                end
                S_CALC: begin
                    if (inv) begin
                        v_r <= x_r - acc[WS-1:0];
                        y_r <= x_r - acc[WS-1:0];
                    end else begin
                        v_r <= x_r;
                        y_r <= x_r + acc[WS-1:0];
                    end
                    k <= 0; sub <= 1'b0;
                    phase <= S_UPD;
                end
                S_UPD: begin
                    if (!sub) sub <= 1'b1;
                    else begin
                        sub <= 1'b0;
                        if (k == K) begin
                            dl <= out_sched ? v_r : dl_in[WS-1:0];
                            phase <= S_OUT;
                        end else begin
                            st[k] <= s_new[WST-1:0];
                            k <= k + 1'b1;
                        end
                    end
                end
                S_OUT: begin
                    out_valid <= 1'b1;
                    out_y     <= y_r;
                    phase     <= S_IDLE;
                end
                default: phase <= S_IDLE;
            endcase
        end
    end

endmodule
