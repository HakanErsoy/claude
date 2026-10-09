# Kart ölçümleri için oturum talimatı (vo_bank_core)

Bu dosya, FPGA kartının bağlı olduğu bilgisayarda açılacak ayrı bir Claude oturumu için yazıldı. Amaç: makalenin 9. bölümündeki (Fixed-point realization) bekleyen ölçümleri **yeni çekirdekle** yapmak ve sonuçları makine tarafından okunabilir biçimde depoya koymak. Makale metni bu oturumda **değiştirilmez**; sonuçlar ana oturumda makaleye işlenir.

## 0. Bağlam

- Depo: `https://github.com/HakanErsoy/claude`, dal `claude/tender-ritchie-ltym3n`.
- Çekirdek: `rtl/vo_bank_core.v`. Sabit kutuplu, değişken dereceli kesirli operatör; dört tip (A/B/D/E). Derece ve tip her örnekte değişebiliyor; değişim yalnızca bir ROM adresi.
- Golden model: `vofrac/fixedpoint.py` (`FixedPointBank.run`). RTL simülasyonda bununla bit-tam eşleşiyor (31 744 + 62 464 vektör, 0 uyumsuzluk).
- Testbench, ROM dosyaları, vektörler ve beklenen çıktılar: `rtl/tb_vo_bank.v`, `rtl/build/<cfg>/`. Ayrıntılar `rtl/README.md`'de.
- İki yapılandırma (`<cfg>`):

| `<cfg>` | Zarf | WS / WST / WM | Vektör |
|---|---|---|---|
| `WS36_WM16` | yalnız A/B | 36 / 49 / 16 | 31 744 |
| `WS48_WM25` | A/B/D/E | 48 / 61 / 25 | 62 464 |

- Ortak parametreler: K = 32 (+ gecikme modu), P = 1024 derece seviyesi, örnek başına 4K + 8 = 136 çevrim.

## 1. Kesin kurallar

1. **Önceki makalenin (TCAS-I'ye gönderilen, şu an AEÜ'de incelemedeki sabit dereceli FPGA çalışması) hiçbir ölçümü, şekli, tablosu ya da sayısı kullanılmayacak.** Her sayı bu oturumda, bu çekirdekle yeniden ölçülecek. Genel amaçlı test altyapısı (ör. bir UART modülü) yeniden kullanılabilir; bu durumda hangi dosyanın nereden geldiği `rtl/board/README.md`'de belirtilecek.
2. `rtl/vo_bank_core.v` ve `vofrac/fixedpoint.py` **değiştirilmeyecek**. Zamanlama hedefe yetmezse çekirdeğe boru hattı eklenmeyecek; ulaşılan Fmax olduğu gibi raporlanacak. Değişiklik gerekiyorsa önce kullanıcıya sorulacak.
3. Çalışma yeni bir dalda yapılacak: `fpga/board-measurements` (`claude/tender-ritchie-ltym3n` dalından açılacak). Yalnızca `rtl/` ve `results/e5_board*.json` dosyalarına dokunulacak; `paper/` ve diğer klasörler değişmeyecek.
4. Sonuçlar olduğu gibi raporlanacak. Uyumsuzluk, taşma ya da zamanlama ihlali varsa gizlenmeyecek; ilk uyumsuz örneğin indeksi ve değerleri kaydedilecek.
5. Ölçüm koşulları (kart, FPGA parçası, saat, Vivado sürümü, sentez/yerleştirme ayarları) eksiksiz kaydedilecek.

## 2. Hazırlık

1. Depoyu klonla, dalı aç: `git checkout claude/tender-ritchie-ltym3n && git checkout -b fpga/board-measurements`.
2. Kullanıcıya sor ve `rtl/board/README.md`'ye yaz:
   - kart modeli ve FPGA parça numarası (ör. `xc7a100tcsg324-1`),
   - kart saat kaynağı ve frekansı,
   - bilgisayarla iletişim yolu (USB-UART önerilir) ve pinler,
   - Vivado sürümü.
3. Python 3 ortamı: `numpy`, `scipy`, `pyserial`.
4. `rtl/README.md`, `rtl/vo_bank_core.v`, `rtl/tb_vo_bank.v` ve `vofrac/fixedpoint.py` dosyalarını oku.

## 3. Simülasyon paritesi (xsim)

Her iki `<cfg>` için `rtl/README.md`'deki xsim komutlarını çalıştır. Üretilen `out.txt` depodaki `rtl/build/<cfg>/out.txt` ile **birebir** aynı olmalı. Değilse dur ve kullanıcıya bildir; sonraki adımlara geçme.

## 4. Vivado sentezi ve zamanlama (her `<cfg>` için)

1. Çekirdeği tek başına (out-of-context) kartın parçası için sentezle ve yerleştir. ROM dosyaları (`coef.mem`, `upole.mem`, `gain.mem`) ilgili `rtl/build/<cfg>/` klasöründen.
2. Yeniden üretilebilir bir TCL betiği yaz: `rtl/vivado/ooc_<cfg>.tcl`.
3. Fmax'ı bul: önce dar bir saat kısıtıyla (ör. 5 ns) dene, sonra kısıtı WNS'ye göre ayarla. Fmax = 1 / (T_kısıt − WNS). Ayar ve deneme sayısını kaydet.
4. Raporlar `rtl/build/<cfg>/vivado/` altına:
   - `utilization.rpt`: LUT, FF, DSP48, BRAM,
   - `timing_summary.rpt`.
5. Yosys tahminleri (README'de) yalnız karşılaştırma için; Vivado sonuçları ayrı raporlanacak.

## 5. Kartta bit-tam parite

1. Sarmalayıcı üst modül yaz: `rtl/board/board_top.v`.
   - UART (önerilen 921 600 baud ya da kartın desteklediği en yüksek güvenilir hız) üzerinden her örnek için `{type, aidx, x}` alıp çekirdeğe ver, `out_y`'yi geri gönder.
   - Çekirdeğin `in_valid`/`in_ready` el sıkışmasına uy. Örnek sırası korunmalı; testbench'teki gibi başta **tek bir reset** olmalı.
   - Basit bir çerçeve protokolü kullan (ör. örnek başına sabit uzunlukta küçük-endian kelime) ve `rtl/board/README.md`'de tanımla.
2. Ana bilgisayar betiği yaz: `rtl/board/host_parity.py`.
   - `stim.mem`'i (onaltılık satırlar) okuyup karta gönder, çıktıları topla, `out.txt` ile karşılaştır.
   - Uyumsuzluk sayısını ve varsa ilk uyumsuzluğu (indeks, beklenen, gelen) yazdır.
3. Her `<cfg>` için ayrı bitstream üret, SHA-256 özetini kaydet, pariteyi çalıştır. **Hedef: 0 uyumsuzluk.**
4. Kart üstünde bir çevrim sayacı ile örnek başına çevrimi ölç (kabul anından `out_valid`'e kadar). 136 olmalı.

## 6. Örnek hızı

- Teorik: Fmax / 136 (adım 4'teki Fmax ile).
- Kartta kullanılan saatte ölçülen değer: çevrim sayacından. UART hızı ana bilgisayar tarafındaki aktarımı sınırlar; bu ayrıca not edilecek, çekirdeğin hızıyla karıştırılmayacak.

## 7. Uzun koşu kararlılığı (yalnız `WS48_WM25`)

- Tip D (`in_type = 2`), `in_aidx = 51`, yani α ≈ −0.855. Çekirdek D/E için satırı aynalar (P − 1 − 51 = 972 → α ≈ +0.855). Bu, `results/e5c_quantized_stability.json`'daki en kötü kuantize satır (`worst_alpha` ≈ 0.8553). Bu eşlemeyi `vofrac/fixedpoint.py` içindeki `run` ve `index` fonksiyonlarından doğrula.
- Örnek sayısı en az 10⁷ (önerilen 2²⁴ ≈ 1.68·10⁷).
- Giriş kartta üretilsin: tanımlı bir 32-bit LFSR (polinom ve tohum README'ye yazılacak). Değerleri |x| ≤ 0.25 olacak biçimde ölçekle ve WS = 48, F = 23 biçimine çevir.
- Kart, 2¹⁶ örneklik her blok için şunları ana bilgisayara göndersin:
  - en büyük |y|,
  - Σ y² (yeterince geniş akümülatörle),
  - doygunluk/taşma bayrağı.
- Golden karşılaştırma: aynı LFSR dizisini Python'da üret, `FixedPointBank` ile ilk 2¹⁷ örneğin çıktısını hesapla ve kartın çıktısıyla bit bit karşılaştır. Golden model yavaş olduğu için tamamını değil bu öneki kullan.
  - Gerekirse kart bu önek boyunca tüm çıktıları göndersin.
  - Ya da her iki taraf aynı CRC-32'yi hesaplasın.
- Beklenen: çıktı sınırlı kalır, taşma olmaz, blok RMS'si büyümez. (Kuantizasyona duyarlı DC tabanı bu satırı kararlı yapıyor; yalnız kayan nokta tabanıyla bu satırın ters kutbu 1 + 1.9·10⁻⁹'da, e-katlanma süresi yaklaşık 5.2·10⁸ örnek.)

## 8. Sonuç dosyası

Tüm sayıları `results/e5_board.json` dosyasına yaz. Önerilen şema:

```json
{
  "board": "...", "part": "...", "vivado_version": "...", "date": "YYYY-MM-DD",
  "clock_source_mhz": 0,
  "configs": {
    "WS36_WM16": {
      "ooc": {"clock_constraint_ns": 0, "wns_ns": 0, "fmax_mhz": 0,
              "lut": 0, "ff": 0, "dsp48": 0, "bram36_equiv": 0},
      "board": {"clock_mhz": 0, "bitstream_sha256": "...",
                "parity": {"vectors": 31744, "mismatches": 0},
                "cycles_per_sample": 136, "samples_per_s_theoretical": 0}
    },
    "WS48_WM25": {
      "ooc": {"...": "aynı alanlar"},
      "board": {"...": "aynı alanlar, parity.vectors = 62464"},
      "long_run": {"type": "D", "aidx": 51, "samples": 16777216,
                   "input": "LFSR32 poly=..., seed=..., scale=0.25",
                   "block": 65536, "max_abs_y": 0, "rms_first_block": 0, "rms_last_block": 0,
                   "overflow": false, "golden_prefix_samples": 131072, "golden_prefix_mismatches": 0}
    }
  },
  "notes": "..."
}
```

Ayrıca `rtl/board/README.md`'ye şunları yaz: yeniden üretim adımları, protokol, pin eşlemesi, hangi dosyanın nereden geldiği.

## 9. Bitirme

1. Testleri ve paritenin sonucunu tekrar kontrol et; `git status` temiz olsun.
2. `fpga/board-measurements` dalına commit ve push yap.
3. Kullanıcıya kısa bir özet ver: Fmax, kaynaklar, parite sonucu, uzun koşu sonucu ve varsa sorunlar.

Kullanıcı bu dalı ana oturuma bildirince, makalenin 9. bölümündeki kırmızı "pending" paragrafı ve Tablo 8 ana oturumda bu sonuçlarla güncellenecek.
