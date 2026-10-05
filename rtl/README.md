# vo_bank_core: RTL ve kart test paketi (E5)

Sabit kutuplu değişken dereceli kesirli operatör çekirdeği. Dört tipi (A/B/D/E) destekliyor; derece ve tip **her örnekte** değişebiliyor. Golden model `vofrac/fixedpoint.py` (`FixedPointBank.run`) ile bit-tam.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `vo_bank_core.v` | Sentezlenebilir çekirdek (parametrik: K, P, AW, WS, WST, WM, SB) |
| `tb_vo_bank.v` | Testbench: `stim.mem` okur, her `out_y`'yi `out.txt`'ye yazar |
| `build/<cfg>/coef.mem` | Katsayı ROM'u: P × (K+1) satır, her satır `{M (WM bit), S (7 bit)}` |
| `build/<cfg>/upole.mem` | Kutup adımları u'_k = 1 − θ_k (K satır, aynı biçim) |
| `build/<cfg>/gain.mem` | Mod başına durum kazançları `{Go (7 bit), Gi (7 bit)}` |
| `build/<cfg>/stim.mem` | Test vektörleri: her satır `{type (2), aidx (AW), x (WS)}` |
| `build/<cfg>/out.txt` | Beklenen çıkışlar (RTL = golden, 0 uyumsuzluk) |
| `build/<cfg>/synth_stat.txt` | Yosys `synth_xilinx -family xc7` kaynak özeti |

Yapılandırmalar (tasarım noktası: R = 4000, ε = 1e-4, |α| ≤ 0.95, K = 32 + gecikme modu, P = 1024):

| `<cfg>` | Zarf | WS / WST / WM | F (kesir biti) | Örnek | Uyumsuzluk |
|---|---|---|---|---|---|
| `WS36_WM16` | yalnız A/B | 36 / 49 / 16 | 21 | 31 744 | 0 |
| `WS48_WM25` | A/B/D/E | 48 / 61 / 25 | 23 | 62 464 | 0 |

## Arayüz

- `in_valid` / `in_ready`: el sıkışma; `in_ready` örnek işlenirken düşük
- `in_type`: 0 = A, 1 = B, 2 = D, 3 = E
- `in_aidx`: derece ızgara indeksi, α = 0.95·(2·aidx/(P−1) − 1)
- `in_x`: WS-bit ikiye tümleyen, F kesir biti (|x| ≤ 1)
- `out_valid`, `out_y`: aynı format
- Gecikme: örnek başına 4K + 8 = **136 çevrim** (boru hattısız durum makinesi)

**Fiziksel birimler.** Çekirdek örnek birimlerinde çalışıyor (Ts = 1, g₀ = 1); bu sayede D/E terslemesi bölücü gerektirmiyor. Fiziksel Ts için tek bir kazanç Ts^(−α_n) gerekiyor:
- A ve E: çıkışa uygulanıyor
- B ve D: girişe uygulanıyor

## Yeniden üretim

```bash
python3 experiments/e5_fixed_point.py   # kelime uzunluğu taraması, yapılandırma seçimi
python3 experiments/e5_rtl_parity.py    # ROM + vektör üretimi, iverilog paritesi, verilator lint, yosys
```

## Vivado / xsim (örnek: WS48_WM25)

```bash
cd rtl/build/WS48_WM25
xvlog ../../vo_bank_core.v ../../tb_vo_bank.v
xelab tb_vo_bank -generic_top "K=32" -generic_top "WS=48" -generic_top "WST=61" -generic_top "WM=25" \
      -generic_top "N=62464" -s tb
xsim tb -R          # out.txt üretir (dosya adları varsayılan: coef.mem, upole.mem, gain.mem, stim.mem)
diff out.txt <(git show HEAD:rtl/build/WS48_WM25/out.txt)
```

## Kartta yapılması önerilen ölçümler (henüz yapılmadı)

Bu ortamda Vivado ve kart yok. Aşağıdaki ölçümler senin akışında yapılmalı ve **TCAS-I ölçümleri yeniden kullanılmamalı**:
1. Bitstream üzerinde bit-tam parite: `stim.mem` → kart → `out.txt` ile karşılaştırma (hedef: 0 uyumsuzluk)
2. Vivado kaynak raporu ve Fmax (Yosys tahmini aşağıda; Vivado sonuçları farklı olabilir)
3. Örnek hızı: Fmax / 136
4. Her örnekte derece değişimi: vektörlerdeki `per-sample` vakaları; yeniden yükleme yok, derece yalnızca ROM adresi
5. Uzun koşu kararlılığı: D-tipi, α = −0.855 (en kötü kuantize giriş), ≥ 1e7 örnek

## Yosys tahmini (xc7, `synth_xilinx -flatten`)

| `<cfg>` | LUT | FF | DSP48E1 | BRAM (RAMB36 eşdeğeri) |
|---|---|---|---|---|
| `WS36_WM16` | 4 171 | 1 882 | 11 | 22 |
| `WS48_WM25` | 6 009 | 2 360 | 29 | 29.5 |

Verilator `-Wall` 18 uyarı veriyor; hepsi bilerek yapılan genişlik genişletme ve kesmeleri (WIDTHEXPAND/WIDTHTRUNC/UNUSEDSIGNAL), işlevsel uyarı yok.
