# Makale taslağı ve ek materyal

Springer Nature `sn-jnl` şablonu (pdflatex, `sn-mathphys-num` numaralı kaynak stili). Taslak İngilizce; bu not Türkçe. Hedef dergi Signal Processing (Elsevier) olursa elsarticle'a geçiş gerekecek.

**Başlık (2026-10-07'de güncellendi):** *Definition-Consistent Variable-Order Fractional Operators from Fixed-Pole Banks: Structure, Error Guarantees, and Order Tracking*

Önceki başlık: *... from a Single Fixed-Pole Bank: Structure, Design Rule, and Fixed-Point Realization*. Donanım ayrıntıları ek materyale taşındığı ve izleme uygulaması eklendiği için başlık değişti; istenirse eskisine dönülebilir.

## Derleme

```bash
cd paper
make            # önce şekiller (results/*.json'dan), sonra main.pdf ve supplement.pdf
make figs       # yalnız şekiller
make clean      # LaTeX ara dosyalarını siler
```

Gerekenler: TeX Live (pdflatex, bibtex, latexmk, tikz, booktabs, algorithmicx) ve Python 3 (numpy, matplotlib).

## Dosyalar

| Dosya | İçerik |
|---|---|
| `main.tex` | Makale metni (41 sayfa) |
| `supplement.tex` | Ek materyal (8 sayfa, S1–S7): CT anahtarlama tablosu, durum eşlemesi ayrıntıları, hot-swap tip analizi, sabit nokta ayrıntıları ve kelime uzunluğu şekli, mBm ayrıntıları ve tablosu, iki türetme (B-tipi basamak yanıtı, büyük-r alias terimi). Ana metne `xr` paketiyle çapraz referans veriyor |
| `refs.bib` | Kaynaklar (72 girdi; Crossref ile doğrulandı, `litreview/bib_check.csv`). Son eklenen üçü (Widder 1941, Sabzikar ve ark. 2015, Mainardi–Garrappa 2015) 2026-10-07'de Crossref'te doğrulandı |
| `make_figures.py` | Sekiz vektör şekil; yalnızca `results/*.json` okuyor, deney koşturmuyor |
| `figs/` | Üretilen şekiller (PDF) |
| `sn-jnl.cls`, `sn-mathphys-num.bst` | Resmî Springer Nature şablonundan (değiştirilmedi) |
| `main.pdf`, `supplement.pdf` | Derlenmiş taslak ve ek materyal |

## Bölümler ve dayandıkları deneyler

| Bölüm | İçerik | Kaynak |
|---|---|---|
| 1 | Giriş, altı maddelik katkı listesi; 1.1 ilgili çalışmalar ve Tablo 1 | `litreview/` |
| 2 | A/B/D/E tanımları, matris formu, dualite, CT basamak referansları, difüzif gösterim | — |
| 3 | CT ve DT sabit kutuplu banka (Beta-integral, Lemma 1), kuyruk kapanışı, OS/IS, Şekil 1 (TikZ) | — |
| 4 | Önerme 2 (OS→A, IS→B), Sonuç 3, Önerme 4 (D/E terslemeyle), Teorem 5 (operatör normu), Not 2 (koşul sayısı), Teorem 6 (gereklilik), Sonuç 7 | E7 |
| 5 | Hata modeli, tasarım kuralı, Önerme 8 (ters kararlılık), DC tabanı | — |
| 6 | Tam monoton çekirdek aileleri: Teorem 9, Lemma 10 (GL sabitleri kapalı formda), örnekler | E9 |
| 7.2–7.8 | Hangi tanım izleniyor; durum eşlemesi (özet); mühürlü holdout; dört tip; operatör normu; CM aileleri; maliyet–doğruluk (Pareto) | E1, E1b, E2, E3, E4, E7, E9, E8 |
| 8.1 | **Çevrimiçi derece izleme** (yeni): A-tipi ızgara filtresi ve EKF, B-tipi artırılmış EKF, yanlış tip yanlılığı (Tablo 7, Şekil 6) | E10 |
| 8.2 | mBm (özet): Önerme 11 (tamsayı bölme), sonuçlar, Şekil 7 | E6 |
| 9 | Sabit nokta (özet): Algoritma 1, iki zarf, kuantizasyon ve kararlılık, kelime uzunlukları, RTL paritesi ve Tablo 8 | E5, E5c |
| 10–11 | Sınırlar (tahmin, ortak kutup kümesinin boyutu dahil), sonuç | — |
| Ekler | A: gereklilik; B: ters kararlılık; C: operatör normu; D: CM teoremi ve Lemma 10 | — |
| Ek materyal | S1 CT tablosu; S2 durum eşlemeleri; S3 hot-swap tipi; S4 sabit nokta; S5 mBm; S6 B-tipi basamak yanıtı; S7 alias terimi | E1, E2, E4, E5, E6 |

Not: teorem numaraları LaTeX'te paylaşılan sayaçla otomatik veriliyor; yukarıdaki numaralar derlenmiş PDF'e göre (Algoritma 1, Tablo 7–8, Şekil 6–7 dahil).

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

- **İkinci tur (2026-10-07):**
  - **Lemma 10:** GL ailesi için (H1)–(H3) sabitleri kapalı formda, L_d ≤ (2/(1−e^{−2}))^ā (cos d)^{−(1+ā)}. Teorem 9(c) böylece GL'ye özgü hata modeli olmadan a priori tasarım veriyor; dört spesifikasyonda ε 13–17 kat payla tutuldu, K kuraldan 1.4–1.6 kat büyük (E9 P5).
  - **Çevrimiçi derece izleme (Bölüm 8.1, E10).** Doğru tipte hata SNR ile azalıyor: 60 dB'de A-ızgara 1.3e-3, B-EKF 1.2e-2. Yanlış tipte hata SNR ile artıyor: 0.14–0.24. A-EKF bankayla kesin GL-EKF'yi 9e-6 içinde tekrarlıyor.
  - **Toparlama:** sabit nokta ayrıntıları, durum eşlemesi şekli ve tablosu, mBm tablosu, CT tablosu ve iki türetme eki ek materyale taşındı. Katkı listesi altı maddeye indi, başlık güncellendi.
- **Üç ekleme (2026-10-07):**
  - **Operatör normu sınırları (Teorem 5, Not 2, Ek E; E7).** İleri tiplerde ℓ1/ℓ∞ göreli operatör hatası her derece dizisi için ≤ ε_R. Schur sabitleri ρ_row/ρ_col hiç aşılmadı ve sabit/kötü niyetli dizilerde tam yakalandı. Özyinelemeli integrallerde koşul sayısıyla (≈ 2N^a/Γ(1+a)) büyüme var; garanti için tasarım ε/κ ile yapılmalı. Adım yanıtından a-posteriori sertifika da verildi.
  - **Tam monoton çekirdek aileleri (Bölüm 6, Teorem 9, Ek F; E9).** Yapı, tersleme ve gereklilik sonuçları her CM aileye taşınıyor. Şerit analitikliği ve kuvvet yasası koşullarıyla hata terimleri ve K = O(ln(1/ε) ln(R/ε)) elde edildi; 35 tasarımda uydurulan katsayı 0.106, teoride 1/π² = 0.101. Örnekler: zamanla değişen dağılımlı derece, sabit temperleme. CT için Bernstein notu var.
  - **Karşılaştırma ve Pareto (Bölüm 7.8, Şekil 7; E8).** Kayan kutup (hot swap), budanmış GL, kısıtsız ve işaret kısıtlı LP artıkları karşılaştırıldı. Kural en küçük bankayı vermiyor: işaret kısıtlı LP %20–30, kısıtsız LP %40–50 daha az kutupla aynı doğruluğa ulaşıyor. Ancak kısıtsız LP ters kararlılık sertifikasını kaybediyor. Bu bulgu makalede açıkça yazıldı.
  - Yeni kaynaklar: Widder 1941, Sabzikar ve ark. 2015, Mainardi–Garrappa 2015 (Crossref ile doğrulandı).

## Yapılacaklar (gönderimden önce)

1. **Yazarlar:** isimler, kurumlar, e-postalar (`main.tex` başı, şu an yer tutucu).
2. **Kart ölçümleri** (Bölüm 9'daki kırmızı paragraf):
   - bitstream paritesi
   - Vivado kaynak raporu ve f_max
   - f_max/136 örnek hızı
   - en kötü kuantize satırda (D-tipi, α = −0.855) ≥ 1e7 örneklik uzun koşu
   Paket ve adımlar: `rtl/README.md`. TCAS-I ölçümleri kullanılmayacak.
3. **Önceki makalenin referansı:** `refs.bib` → `tcas_submission`. TCAS-I editörü önceki makaleyi kapsam dışı buldu; makale AEÜ'de incelemede. Başlık ve yazarlar eklenecek, karar gelince durum güncellenecek. TCAS-I bu makale için hedef değil; önerilen hedef Signal Processing (Elsevier).
4. **Kaynak doğrulama:** yapıldı (`litreview/verify_bib.py`). `montseny1998` doğrulandı ve DOI eklendi. Crossref'te olmayan kitaplar, INRIA raporu ve FCAA 2000 web üzerinden kontrol edildi. Yalnızca TCAS-I yer tutucusu kaldı.
5. **Literatür taraması:** Crossref + arXiv üzerinde yapıldı (`litreview/`: PROTOKOL.md, SENTEZ.md, FULLTEXT.md; 131 dahil kayıt). §1.1 ve Tablo 1 buna dayanıyor. Tam metin kontrolleri yapıldı; dört ifade düzeltildi ve bir öncül eklendi. **Kalan:** aynı dizgelerle Scopus/WoS tekrarı (Bölüm 10'daki kırmızı TODO) ve FULLTEXT.md'de "okunamadı" diye işaretlenen 11 kaydın kurumsal erişimle okunması.
6. **Beyanlar:** finansman, çıkar çatışması, kod erişimi (depo URL'si veya Zenodo DOI), yazar katkıları, teşekkür.
7. **Kapak mektubu:** TCAS-I çalışmasıyla ilişki açıkça yazılmalı. Springer'in eşzamanlı gönderim politikası kontrol edilmeli.
8. **Dergi yazım kuralları:** özet 249 kelime (sınır 250 kabul edildi). Hedef Signal Processing olursa elsarticle şablonuna geçiş gerekecek. Anahtar kelime sayısı (şu an 7) ve sayfa/şekil sınırları dergi sayfasından doğrulanmalı.
9. **İsteğe bağlı:**
   - D/E tiplerinin keyfi anahtarlamada kararlılığı için bir sonuç (şu an tartışma bölümünde açık sınır olarak duruyor)
   - ~~çıkış düzeyinde hata kuralı~~ → Teorem 5 ile ℓ1/ℓ∞ en kötü durum anlamında yapıldı; özyinelemeli integraller için ε/κ kuralı Not 2'de
   - K için alt sınır (ortak kutup kümesi tek dereceye göre ne kadar büyük olmalı; açık soru olarak tartışmada)
   - işaret kısıtlı LP'yi kurala alternatif bir tasarım yolu olarak kütüphaneye eklemek (şu an `vofrac/baselines.py` içinde)
   - ~~VO derece kestirimi (EKF, O(K) Jacobian)~~ → Bölüm 8.1'de yapıldı (bilinen giriş); bilinmeyen giriş veya durumla ortak kestirim açık
   - boru hatlı çekirdek
