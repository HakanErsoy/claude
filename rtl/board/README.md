# Kart ölçümleri (E5, `vo_bank_core`)

`rtl/BOARD_SESSION.md` talimatıyla yapılan ölçümler. Sonuçlar `results/e5_board.json`; ham ölçüm dosyaları `rtl/build/<cfg>/vivado/` (OOC) ve `rtl/build/<cfg>/board/` (kart).

## Ölçüm düzeni

| | |
|---|---|
| Kart | Digilent PYNQ-Z1, PYNQ 3.0.1 imajı |
| FPGA | `xc7z020clg400-1` (Zynq-7020) |
| Vivado | 2026.1 (Windows) |
| Saat kaynağı | PS `FCLK_CLK0` (IO PLL 1000 MHz / tam sayı bölücüler). Frekans `.hwh`'den PYNQ tarafından ayarlanır, ayrıca kartta çevrim sayacıyla ölçülür. Çekirdek, AXI arayüzü ve sayaçlar aynı saatte. |
| Bilgisayar bağlantısı | Gigabit Ethernet (PC 192.168.2.1 ↔ kart 192.168.2.99), SSH/scp. |
| Çekirdek erişimi | AXI4-Lite, `M_AXI_GP0` → AXI Interconnect → `board_top` @ `0x43C0_0000`. Vektörleri kartın ARM'ında çalışan `board_runner.py` (PYNQ `MMIO`) sürer. |
| Pin eşlemesi | Dış pin yok: tüm trafik PS–PL AXI üzerinden. UART kullanılmadı: kartın USB-UART'ı PS'ye (MIO) bağlı, PL'den erişilemiyor; PL UART ek Pmod adaptörü gerektiriyordu (kullanıcıyla kararlaştırıldı). |

`rtl/vo_bank_core.v` ve `vofrac/fixedpoint.py` değiştirilmedi. Çekirdek `board_top` içinde olduğu gibi örnekleniyor.

## Dosyalar ve kaynakları

Bu klasördeki her dosya bu oturumda sıfırdan yazıldı. Önceki (TCAS-I / AEÜ, sabit dereceli) FPGA çalışmasından hiçbir dosya, ölçüm ya da betik kullanılmadı.

| Dosya | İçerik |
|---|---|
| `board_top.v` | AXI4-Lite sarmalayıcı: tek-örnek modu, uzun koşu motoru (LFSR, blok istatistikleri, CRC-32, yakalama tamponu), çevrim sayaçları |
| `tb_board_top.v`, `sim_board.sh`, `check_sim.py` | Bitstream öncesi xsim doğrulaması: 600 vektör tek-örnek + 2¹¹ örneklik uzun koşu, golden modelle karşılaştırma |
| `build_board.tcl` | Blok tasarım (PS7 + interconnect + `board_top`), sentez, yerleştirme, bitstream, `.hwh` |
| `board_runner.py` | Kart tarafı (ARM, root, PYNQ venv): overlay yükler, saati ölçer, pariteyi / uzun koşuyu sürer |
| `host_parity.py` | PC tarafı: dosyaları karta kopyalar, pariteyi çalıştırır, çıktıyı `rtl/build/<cfg>/out.txt` ile karşılaştırır |
| `host_longrun.py` | PC tarafı: uzun koşuyu çalıştırır, golden önekle karşılaştırır |
| `golden.py` | Golden yardımcıları: `FixedPointBank`'ı `e5_rtl_parity.py` ile aynı biçimde kurar ve ROM'ların `rtl/build/<cfg>/` ile bayt bayt aynı olduğunu denetler; LFSR dizisi; blok kayıtları |
| `make_results.py` | `results/e5_board.json`'u ham dosyalardan üretir |
| `../vivado/run_xsim.sh` | xsim paritesi (çekirdek testbench'i) |
| `../vivado/ooc_common.tcl`, `ooc_<cfg>.tcl`, `fmax_search.sh` | OOC sentez+uygulama ve Fmax araması |

## Yeniden üretim

```bash
# 3. xsim paritesi
rtl/vivado/run_xsim.sh WS36_WM16
rtl/vivado/run_xsim.sh WS48_WM25
# 4. OOC Fmax ve kaynaklar (5 ns ile başlar, sonra kısıt = T - WNS)
rtl/vivado/fmax_search.sh WS36_WM16 <workdir>
rtl/vivado/fmax_search.sh WS48_WM25 <workdir>
# 5a. sarmalayıcının simülasyonu
rtl/board/sim_board.sh WS48_WM25
# 5b. bitstream (FCLK MHz değeri rtl/build/<cfg>/board/summary.txt'te)
vivado -mode batch -source rtl/board/build_board.tcl -tclargs <cfg> <fclk_mhz> <bitdir>
#     <bitdir>/{utilization.rpt,timing_summary.rpt,summary.txt} -> rtl/build/<cfg>/board/
# 5c. kartta parite
python rtl/board/host_parity.py <cfg> <bitdir>
# 7. uzun koşu
python rtl/board/host_longrun.py <bitdir_WS48_WM25>
# 8. sonuç dosyası
python rtl/board/make_results.py
```

Kart tarafında `root` için SSH anahtarı gerekli; betikler `ssh -o BatchMode=yes` kullanır, parola sormaz.

## Protokol: AXI4-Lite yazmaç haritası

Tüm yazmaçlar 32 bit, bayt adresi `0x43C0_0000` tabanına göre.

| Adres | Ad | Y/O | İçerik |
|---|---|---|---|
| 0x00 | CTRL | Y | bit0: çekirdeği 8 çevrim resetle (sayaçları da sıfırlar); bit1: uzun koşuyu başlat |
| 0x04 | STATUS | O | bit0 tek örnek bekliyor, bit1 `y` hazır, bit2 uzun koşu sürüyor, bit3 uzun koşu bitti, bit4 `in_ready`, bit5 reset sürüyor |
| 0x08 / 0x0C | X0 / X1 | Y/O | `x` (WS bit, ikiye tümleyen), alt / üst 32 bit |
| 0x10 | CMD | Y | `[9:0]` aidx, `[17:16]` tip (0 A, 1 B, 2 D, 3 E). Yazınca örnek başlar: `in_valid`, çekirdek kabul edene kadar yüksek kalır |
| 0x14 / 0x18 | Y0 / Y1 | O | son `out_y`, 64 bite işaret genişletilmiş |
| 0x1C | NSAMP | O | resetten beri çıkış sayısı |
| 0x20 / 0x24 / 0x28 | LAT_LAST / MIN / MAX | O | kabul çevriminden `out_valid` çevrimine çevrim sayısı |
| 0x2C / 0x30 / 0x34 | PER_LAST / MIN / MAX | O | ardışık iki kabul arasındaki çevrim (uzun koşu başında sıfırlanır) |
| 0x38 / 0x3C | CYC0 / CYC1 | O | serbest 64-bit çevrim sayacı (CYC0 okuması üst yarıyı kilitler) |
| 0x40 | LR_CFG | Y/O | `[9:0]` aidx, `[17:16]` tip, `[28:24]` log2 örnek sayısı |
| 0x44 | LR_LGB | Y/O | log2 blok uzunluğu |
| 0x48 | LR_SEED | Y/O | LFSR tohumu |
| 0x4C | LR_NBLK | O | tamamlanan blok sayısı (en çok 256) |
| 0x50 / 0x54 | LR_CYC0 / 1 | O | uzun koşunun başlangıçtan bitişe toplam çevrimi |
| 0x58 | BLK_ADDR | Y/O | okunacak blok |
| 0x5C–0x78 | BLK0–7 | O | max\|y\| (64 bit), Σy² (128 bit), CRC-32, \|y\| ≥ 2^(WS−2) sayısı |
| 0x7C | CAP_ADDR | Y/O | yakalama tamponu adresi (0…4095) |
| 0x80 / 0x84 | CAP0 / CAP1 | O | uzun koşunun ilk 4096 çıkışından biri, işaret genişletilmiş |
| 0x88 | PARAMS | O | `{WM, WST, WS, K}`, birer bayt |
| 0x8C | ID | O | `0x564F4231` ("VOB1") |
| 0x90 / 0x94 | ISSUED / OCOUNT | O | uzun koşuda verilen / alınan örnek sayısı |

**Parite akışı.** Önce bir kez CTRL bit0 (reset) yazılır. Sonra her vektör için şu adımlar izlenir:
1. X0, X1 ve CMD yazılır.
2. STATUS bit1 beklenir.
3. Y0 ve Y1 okunur.

Bu, testbench'teki gibi tek reset ve kesintisiz bir akış demek: örnekler arasında çekirdek durumu korunur.

**Uzun koşu girişi.** 32-bit Galois LFSR kullanılır.
- Maske `0x80200003`, yani x³² + x²² + x² + x + 1 (maksimal uzunluk).
- Örnek başına 32 adım ilerletilir.
- `x = (işaretli 32-bit durum) >> 10` alınır. Bu, `|x| ≤ 2²¹` LSB demek; F = 23'te `|x| ≤ 0.25`.
- Tohum ve tanım `golden.lfsr_inputs` ile aynıdır.

Örnekler arka arkaya verilir: `in_valid` sürekli yüksek, LFSR hesabı çekirdeğin 4K+7 çevrimlik hesabıyla örtüşür.

**Blok kaydı.** Her 2^LB çıkış için şunlar saklanır:
- max|y|,
- Σy², 128 bit akümülatörde,
- CRC-32: IEEE 802.3, yansıtılmış; Python'daki `zlib.crc32` ile aynı. Her çıkış, 64 bite işaret genişletilip küçük-endian 8 bayt olarak işlenir.
- |y| ≥ 2^(WS−2) olan çıkış sayısı.

**Taşma bayrağı hakkında.** Çekirdek doyurmuyor; taşarsa sarar ve iç durumu dışarı açmıyor. Çekirdeğe dokunulmadığı için bayrak ancak çıkış üzerinden tanımlanabildi: |y|, tam ölçeğin yarısına (2^(WS−2)) ulaşırsa işaretlenir. Golden önek koşusu ise (`FixedPointBank.run(check=True)`) iç durum ve sinyal taşmasını doğrudan denetliyor.
