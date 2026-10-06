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
| `refs.bib` | Kaynaklar (29'u atıf alıyor) |
| `make_figures.py` | Altı vektör şekil; yalnızca `results/*.json` okuyor, deney koşturmuyor |
| `figs/` | Üretilen şekiller (PDF) |
| `sn-jnl.cls`, `sn-mathphys-num.bst` | Resmî Springer Nature şablonundan (değiştirilmedi) |
| `main.pdf` | Derlenmiş taslak |

## Bölümler ve dayandıkları deneyler

| Bölüm | İçerik | Kaynak |
|---|---|---|
| 1 | Giriş, katkılar | — |
| 2 | A/B/D/E tanımları, matris formu, dualite, CT basamak referansları, difüzif gösterim | — |
| 3 | CT ve DT sabit kutuplu banka (Beta-integral, Lemma 1), kuyruk kapanışı, OS/IS, Şekil 1 (TikZ) | — |
| 4 | Önerme 2 (OS→A, IS→B), Sonuç 3 (hata sınırı), Önerme 4 (D/E terslemeyle), Teorem 5 (gereklilik), Sonuç 6 | — |
| 5 | Hata modeli, tasarım kuralı, Önerme 7 (ters kararlılık), DC tabanı | — |
| 6.2 | Hangi tanım izleniyor (CT ve DT) | E1, E1b |
| 6.3 | Durum eşlemesi | E2 |
| 6.4 | Mühürlü holdout | E3 |
| 6.5 | Dört tip, ters kararlılık, hot-swap'ın tipi, gevşeme denklemi | E4 |
| 7 | Sabit nokta, iki zarf, kuantizasyon ve kararlılık, kelime uzunluğu, RTL | E5, E5c |
| 8 | mBm uygulaması, Önerme 8 (tamsayı bölme) | E6 |
| 9–10 | Sınırlar, sonuç | — |
| Ekler | A: Teorem 5 ispatı; B: Önerme 7 ispatı; C: B-tipi basamak yanıtı; D: büyük-r alias terimi | — |

Metindeki her sayı `results/` altındaki bir JSON dosyasından alındı. Tablolar elle yazıldı; sonuçlar değişirse tablolar da güncellenmeli.

## Taslak sırasında yapılan düzeltmeler

- **Önerme 7'nin tam hali:** İntegral bankasında gecikme kutbu (z = 0) yüzünden bir sıfır negatif eksene düşüyor. Bu yüzden H(−1) > 0 koşulu da gerekiyor. Türev bankasında c_d > 0 ise aynı koşul geçerli. İspat Ek B'de. İlk iki ağırlık 1/3 doğrulukla gerçekleniyorsa H(−1) > 0 kendiliğinden sağlanıyor. Holdout'taki tüm derecelerde H(−1), tam değeri 2^α·g₀'a %0.06 içinde yakın. `vofrac/bank.py` içindeki `inverse_is_stable` artık bu koşulu da kontrol ediyor. E4 sonuçları değişmedi (200/200 ve 101/200).
- **Özdeğer yerine işaret:** Bir holdout tasarımında (α = 0.95, K = 35) baskın ters kutup 50 basamaklı hesapla 1 − 2.9e-12'de. `numpy.linalg.eigvals` ise 1 + 4.5e-9 veriyor. Bu örnek makalede Remark 3 olarak yer alıyor.
- **E5c (yeni, `experiments/e5c_quantized_stability.py`):** Kuantize ROM satırlarında H_q(±1) işaretleri artık tam rasyonel aritmetikle hesaplanıyor.
  - Sayılar öncekiyle aynı: A/B yapılandırmasında 64/512, A/B/D/E'de 51/512 satır.
  - En kötü satırın baskın kutbu artık tam hesaplanıyor: A/B/D/E'de 1 + 1.9e-9 (önceki özdeğer tahmini 2.5e-9), e-katına çıkma süresi 5.2e8 örnek. A/B'de 1 + 4.8e-6.
  - Kuantizasyona duyarlı tabanla iki yapılandırmada da 0.

## Yapılacaklar (gönderimden önce)

1. **Yazarlar:** isimler, kurumlar, e-postalar (`main.tex` başı, şu an yer tutucu).
2. **Kart ölçümleri** (§7.5'teki kırmızı paragraf):
   - bitstream paritesi
   - Vivado kaynak raporu ve f_max
   - f_max/136 örnek hızı
   - en kötü kuantize satırda (D-tipi, α = −0.855) ≥ 1e7 örneklik uzun koşu
   Paket ve adımlar: `rtl/README.md`. TCAS-I ölçümleri kullanılmayacak.
3. **TCAS-I referansı:** `refs.bib` → `tcas_submission` (başlık, yazarlar, durum).
4. **Kaynak doğrulama:** `montseny1998` (cilt/sayfa TODO). Diğer tüm girdiler yayıncı kaydıyla bir kez daha kontrol edilmeli. Eksik DOI'ler eklenmeli.
5. **Sistematik literatür taraması** (Scopus/WoS, son 10 yıl, VO gerçeklemeleri) ve §9'daki kırmızı TODO: karşılaştırma tablosu.
6. **Beyanlar:** finansman, çıkar çatışması, kod erişimi (depo URL'si veya Zenodo DOI), yazar katkıları, teşekkür.
7. **Kapak mektubu:** TCAS-I çalışmasıyla ilişki açıkça yazılmalı. Springer'in eşzamanlı gönderim politikası kontrol edilmeli.
8. **CSSP yazım kuralları:** özet 249 kelime (sınır 250 kabul edildi). Anahtar kelime sayısı (şu an 7) ve sayfa/şekil sınırları dergi sayfasından doğrulanmalı.
9. **İsteğe bağlı:**
   - D/E tiplerinin keyfi anahtarlamada kararlılığı için bir sonuç (şu an §9'da açık sınır olarak duruyor)
   - çıkış düzeyinde hata kuralı
   - boru hatlı çekirdek
