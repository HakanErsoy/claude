# CSSP makale taslağı

Springer Nature `sn-jnl` şablonu (pdflatex, `sn-mathphys-num` numaralı kaynak stili). Taslak İngilizce; bu not Türkçe.

**Çalışma başlığı:** *Definition-Consistent Variable-Order Fractional Operators from a Single Fixed-Pole Bank: Structure, Design Rule, and Fixed-Point Realization*

## Derleme

```bash
cd paper
make            # önce şekiller (results/*.json'dan), sonra main.pdf
make figs       # yalnız şekiller
make clean      # LaTeX ara dosyalarını siler
```

Gerekenler: TeX Live (pdflatex, bibtex, latexmk, tikz, booktabs, algorithmicx) ve Python 3 (numpy, matplotlib).

## Dosyalar

| Dosya | İçerik |
|---|---|
| `main.tex` | Makale metni |
| `refs.bib` | Kaynaklar (72 girdi; Crossref ile doğrulandı, `litreview/bib_check.csv`). Son eklenen üçü (Widder 1941, Sabzikar ve ark. 2015, Mainardi–Garrappa 2015) 2026-10-07'de Crossref'te doğrulandı |
| `make_figures.py` | Yedi vektör şekil; yalnızca `results/*.json` okuyor, deney koşturmuyor |
| `figs/` | Üretilen şekiller (PDF) |
| `sn-jnl.cls`, `sn-mathphys-num.bst` | Resmî Springer Nature şablonundan (değiştirilmedi) |
| `main.pdf` | Derlenmiş taslak |

## Bölümler ve dayandıkları deneyler

| Bölüm | İçerik | Kaynak |
|---|---|---|
| 1 | Giriş, katkılar; 1.1 ilgili çalışmalar ve karşılaştırma tablosu (Tablo 1) | `litreview/` |
| 2 | A/B/D/E tanımları, matris formu, dualite, CT basamak referansları, difüzif gösterim | — |
| 3 | CT ve DT sabit kutuplu banka (Beta-integral, Lemma 1), kuyruk kapanışı, OS/IS, Şekil 1 (TikZ) | — |
| 4 | Önerme 2 (OS→A, IS→B), Sonuç 3 (hata sınırı), Önerme 4 (D/E terslemeyle), **Teorem 5 (operatör normu sınırları)**, **Not 2 (özyinelemeli tiplerin koşul sayısı)**, Teorem 6 (gereklilik), Sonuç 7 | E7 |
| 5 | Hata modeli, tasarım kuralı, Önerme 8 (ters kararlılık), DC tabanı | — |
| 6 | **Tam monoton (CM) çekirdek aileleri:** Tanım, Teorem 9 (yapı + hata + K = O(ln(1/ε) ln(R/ε))), dağılımlı derece ve temperleme örnekleri, CT/Bernstein notu | E9 |
| 7.2 | Hangi tanım izleniyor (CT ve DT) | E1, E1b |
| 7.3 | Durum eşlemesi | E2 |
| 7.4 | Mühürlü holdout | E3 |
| 7.5 | Dört tip, ters kararlılık, hot-swap'ın tipi, gevşeme denklemi | E4 |
| 7.6 | **Operatör normu hatası** (Tablo: sınır/ölçüm oranları) | E7 |
| 7.7 | **CM aileleri:** şerit sabiti, kuadratür sınırı, K uydurması, dağılımlı ve temperli çekirdekler | E9 |
| 7.8 | **Maliyet–doğruluk karşılaştırması** (Pareto şekli): sabit kutup (kural, LP, işaret kısıtlı LP), kayan kutup (hot swap), budanmış GL | E8 |
| 8 | Sabit nokta, iki zarf, kuantizasyon ve kararlılık, kelime uzunluğu, RTL | E5, E5c |
| 9 | mBm uygulaması, Önerme (tamsayı bölme) | E6 |
| 10–11 | Sınırlar, sonuç | — |
| Ekler | A: gereklilik ispatı; B: ters kararlılık ispatı; C: B-tipi basamak yanıtı; D: büyük-r alias terimi; **E: operatör normu ispatı; F: CM teoremi ispatı** | — |

Not: teorem numaraları LaTeX'te paylaşılan sayaçla otomatik veriliyor; yukarıdaki numaralar derlenmiş PDF'e göre.

Metindeki her sayı `results/` altındaki bir JSON dosyasından alındı. Tablolar elle yazıldı; sonuçlar değişirse tablolar da güncellenmeli.

## Taslak sırasında yapılan düzeltmeler

- **Ters kararlılık önermesinin (şimdi Önerme 8) tam hali:** İntegral bankasında gecikme kutbu (z = 0) yüzünden bir sıfır negatif eksene düşüyor. Bu yüzden H(−1) > 0 koşulu da gerekiyor. Türev bankasında c_d > 0 ise aynı koşul geçerli. İspat Ek B'de. İlk iki ağırlık 1/3 doğrulukla gerçekleniyorsa H(−1) > 0 kendiliğinden sağlanıyor. Holdout'taki tüm derecelerde H(−1), tam değeri 2^α·g₀'a %0.06 içinde yakın. `vofrac/bank.py` içindeki `inverse_is_stable` artık bu koşulu da kontrol ediyor. E4 sonuçları değişmedi (200/200 ve 101/200).
- **Özdeğer yerine işaret:** Bir holdout tasarımında (α = 0.95, K = 35) baskın ters kutup 50 basamaklı hesapla 1 − 2.9e-12'de. `numpy.linalg.eigvals` ise 1 + 4.5e-9 veriyor. Bu örnek makalede Remark 4 olarak yer alıyor.
- **E5c (yeni, `experiments/e5c_quantized_stability.py`):** Kuantize ROM satırlarında H_q(±1) işaretleri artık tam rasyonel aritmetikle hesaplanıyor.
  - Sayılar öncekiyle aynı: A/B yapılandırmasında 64/512, A/B/D/E'de 51/512 satır.
  - En kötü satırın baskın kutbu artık tam hesaplanıyor: A/B/D/E'de 1 + 1.9e-9 (önceki özdeğer tahmini 2.5e-9), e-katına çıkma süresi 5.2e8 örnek. A/B'de 1 + 4.8e-6.
  - Kuantizasyona duyarlı tabanla iki yapılandırmada da 0.

- **Literatür taraması sonrası (2026-10-06):**
  - **Katkı iddiaları daraltıldı.** VO Caputo için dereceden bağımsız üsler Zhang–Fang–Sun 2021'de zaten var; mBm'de A/B ayrımı Wang ve ark. 2023'te (MMFBM) var. Yenilik artık şu noktalarda: yapı ⇔ tanım bağı, A ve B tek bankada, ayrık-zaman GL tamlığı, D/E terslemesi, tasarım kuralı, kararlılık ve donanım.
  - **Hatalı bir atıf düzeltildi.** Arıcıoğlu 2025, hot-swap örneği değil; LTI (üçüncü) tanımı tek transfer fonksiyonuyla gerçekliyor.

## Yapılacaklar (gönderimden önce)

1. **Yazarlar:** isimler, kurumlar, e-postalar (`main.tex` başı, şu an yer tutucu).
2. **Kart ölçümleri** (§7.5'teki kırmızı paragraf):
   - bitstream paritesi
   - Vivado kaynak raporu ve f_max
   - f_max/136 örnek hızı
   - en kötü kuantize satırda (D-tipi, α = −0.855) ≥ 1e7 örneklik uzun koşu
   Paket ve adımlar: `rtl/README.md`. TCAS-I ölçümleri kullanılmayacak.
3. **Önceki makalenin referansı:** `refs.bib` → `tcas_submission`. TCAS-I editörü önceki makaleyi kapsam dışı buldu; makale AEÜ'de incelemede. Başlık ve yazarlar eklenecek, karar gelince durum güncellenecek. TCAS-I bu makale için hedef değil; önerilen hedef Signal Processing (Elsevier).
4. **Kaynak doğrulama:** yapıldı (`litreview/verify_bib.py`). `montseny1998` doğrulandı ve DOI eklendi. Crossref'te olmayan kitaplar, INRIA raporu ve FCAA 2000 web üzerinden kontrol edildi. Yalnızca TCAS-I yer tutucusu kaldı.
5. **Literatür taraması:** Crossref + arXiv üzerinde yapıldı (`litreview/`: PROTOKOL.md, SENTEZ.md, FULLTEXT.md; 131 dahil kayıt). §1.1 ve Tablo 1 buna dayanıyor. Tam metin kontrolleri yapıldı; dört ifade düzeltildi ve bir öncül eklendi. **Kalan:** aynı dizgelerle Scopus/WoS tekrarı (§9'daki kırmızı TODO) ve FULLTEXT.md'de "okunamadı" diye işaretlenen 11 kaydın kurumsal erişimle okunması.
6. **Beyanlar:** finansman, çıkar çatışması, kod erişimi (depo URL'si veya Zenodo DOI), yazar katkıları, teşekkür.
7. **Kapak mektubu:** TCAS-I çalışmasıyla ilişki açıkça yazılmalı. Springer'in eşzamanlı gönderim politikası kontrol edilmeli.
8. **CSSP yazım kuralları:** özet 249 kelime (sınır 250 kabul edildi). Anahtar kelime sayısı (şu an 7) ve sayfa/şekil sınırları dergi sayfasından doğrulanmalı.
9. **İsteğe bağlı:**
   - D/E tiplerinin keyfi anahtarlamada kararlılığı için bir sonuç (şu an §9'da açık sınır olarak duruyor)
   - çıkış düzeyinde hata kuralı
   - boru hatlı çekirdek
