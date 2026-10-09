# Makale taslağı ve ek materyal (Signal Processing sürümü)

Elsevier `elsarticle` şablonu, `review` seçeneği (tek sütun, 12 pt, 1.5 satır aralığı; pdflatex, `elsarticle-num` numaralı kaynak stili). Taslak İngilizce; bu not Türkçe. Hedef dergi Signal Processing (Elsevier).

**Sayfa sınırı:** araştırma makaleleri şekiller, tablolar ve kaynaklar dahil en çok 30 sayfa (tek sütun, çift aralık). Bu bilgi derginin yazar kılavuzunun arama sonucundaki alıntısından alındı; kılavuz sayfası doğrudan açılamadı (403). Gönderimden önce [kılavuzdan](https://www.elsevier.com/journals/signal-processing/0165-1684/guide-for-authors) son kez kontrol edilmeli.

**Başlık:** *Variable-Order Fractional Operators from Fixed-Pole Banks: Definition by Structure, Error Guarantees, and Order Tracking* (TSP sürümüyle aynı).

## Derleme

```bash
cd paper
make            # önce şekiller (results/*.json'dan), sonra main.pdf ve supplement.pdf
make figs       # yalnız şekiller
make clean      # LaTeX ara dosyalarını siler
```

Gerekenler: TeX Live (pdflatex, bibtex, latexmk, tikz, booktabs, algorithmicx) ve Python 3 (numpy, matplotlib).

## Ortak metin: SP ve TSP sürümleri

İki sürümün metni tek kaynaktan derleniyor; bir düzeltme iki sürüme birden geçiyor.

- `body.tex`: ana metin (Giriş'ten Sonuç'a).
- `supp_body.tex`: ek materyal.
- `macros.tex`: teorem ortamları ve makrolar.
- `parts/`: SP sürümünün sayfa sınırı yüzünden ek materyale taşıdığı parçalar.

Sürüm farkları `\ifsp` anahtarıyla seçiliyor. `paper/main.tex` bunu `\sptrue`, `../paper_tsp/main.tex` ise `\spfalse` yapıyor. Bazı yardımcı makrolar her sürümde farklı tanımlı:

- `\proofref`: ispatın yeri (SP'de ek materyal, TSP'de Ek A–D).
- `\citesp{uzun}{kısa}`: SP'de kısaltılmış kaynak listeleri.
- `\tabfont`, `\colfigwidth`, `\partsdir`: biçim ve dosya yolu.
- `\mref`/`\meqref`: ek materyalde ana metne `M-` önekli referans (`xr` paketi).

SP sürümünde ek materyale taşınanlar:

- dört ispat (gereklilik, ters kararlılık, operatör normu, CM teoremi ve Lemma 2);
- ilgili çalışmalar tablosu;
- tasarım kuralı terimleri ve holdout şekli;
- sıçramalı izleme senaryosunun şekli;
- pil modelinin başka gerçeklemelerle karşılaştırma tablosu.

SP sürümünde kısaltılanlar:

- sabit nokta, kart ölçümleri ve mBm paragrafı (ayrıntılar ek materyalde);
- bazı kaynak listeleri.

TSP metni bu yeniden düzenlemeden etkilenmedi (pdftotext çıktısı önceki sürümle aynı).

Kısaltmadan önceki 48 sayfalık uzun sürüm (sn-jnl şablonu) git geçmişinde duruyor: `git show 8518915:paper/main.tex`.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `main.tex` | SP sarmalayıcısı: ön kısım (başlık, yazarlar, özet, anahtar kelimeler), `body.tex`, beyanlar, kaynakça. **29 sayfa** (kaynaklar dahil) |
| `supplement.tex` | SP ek materyal sarmalayıcısı, `supp_body.tex`'i derliyor. **15 sayfa**: S1–S4 ispatlar, S5 ilgili çalışmalar tablosu, S6 tasarım kuralı ve holdout, S7 sıçramalı izleme, S8 pil verisinde başka gerçeklemeler, S9 sürekli zaman bankası, S10 sürekli zaman anahtarlama sonuçları, S11 durum eşlemeleri, S12 hot-swap tipi, S13 tek bankadan dört tip, S14 sabit nokta ve kart ölçümleri, S15 mBm, S16 B-tipi basamak yanıtı, S17 alias terimi |
| `body.tex`, `supp_body.tex`, `macros.tex`, `parts/` | İki sürümün ortak metni (yukarıya bakın) |
| `refs.bib` | Kaynaklar (78 girdi; Crossref ile doğrulandı, `litreview/bib_check.csv`). En son eklenen Tichavský ve ark. 1998 (PCRB). Ondan önceki beş kaynak 2026-10-09'da doğrulandı: Panasonic veri seti DataCite ile; Zou ve ark. 2018, Lu ve ark. 2018, Wang ve ark. 2022, Mao ve ark. 2023 Crossref ile |
| `make_figures.py` | On vektör şekil; yalnızca `results/*.json` okuyor, deney koşturmuyor |
| `figs/` | Üretilen şekiller (PDF); TSP sürümü de bunları kullanıyor |
| `elsarticle.cls`, `elsarticle-num.bst` | Resmî elsarticle paketinden (CTAN; `.cls`, `elsarticle.ins`'ten üretildi; değiştirilmedi) |
| `main.pdf`, `supplement.pdf` | Derlenmiş taslak ve ek materyal |

## Bölümler ve dayandıkları deneyler

Numaralar SP sürümünün derlenmiş PDF'ine göre. TSP sürümünde aynı bölümler, ispatlar Ek A–D'de.

| Bölüm | İçerik | Kaynak |
|---|---|---|
| 1 | Giriş, katkı listesi, ilgili çalışmalar (tablo ek materyalde, S5) | `litreview/` |
| 2 | A/B/D/E tanımları, matris formu, dualite | — |
| 3 | Sabit kutuplu banka (Beta-integral, Lemma 1), OS/IS, Şekil 1 (TikZ) | — |
| 4 | Önerme 1 (OS→A, IS→B), Önerme 2 (D/E terslemeyle), Teorem 1 (operatör normu), Teorem 2 (gereklilik), Sonuç 1 | E7 |
| 5 | Tam monoton çekirdek aileleri: Teorem 3, Lemma 2 (GL sabitleri kapalı formda) | E9 |
| 6 | Hata modeli, tasarım kuralı, Önerme 3 (ters kararlılık), DC tabanı | — |
| 7 | Sayısal sonuçlar: tanım tutarlılığı, mühürlü holdout, operatör normu, maliyet–doğruluk (Tablo 1–2, Şekil 2) | E1, E1b, E2, E3, E4, E7, E8, E9 |
| 8 | Çevrimiçi derece izleme: A-tipi ızgara filtresi ve EKF, B-tipi artırılmış EKF, UFOKF tarzı karşılaştırma, Bayesçi CRB (Tablo 3–4, Şekil 3) | E10, E11, E13 |
| 9 | Ölçülmüş pil verisi: SOC'ye bağlı RC + kesirli integral modeli, birini dışarıda bırak doğrulaması, tip takası, EIS, başka gerçeklemeler (Tablo 5, Şekil 4) | E12, E12b, E12c |
| 10 | Sabit nokta, kart ölçümleri ve mBm (kısa özet; ayrıntılar S14–S15) | E5, E5c, E6 |
| 11 | Sonuç ve sınırlar | — |

Not: teorem numaraları elsarticle'da tür başına ayrı sayaçla veriliyor; TSP sürümünde numaralar farklı.

Metindeki her sayı `results/` altındaki bir JSON dosyasından alındı. Tablolar elle yazıldı; sonuçlar değişirse tablolar da güncellenmeli.

## Taslak sırasında yapılan düzeltmeler

Bu bölümdeki bölüm, teorem, tablo ve şekil numaraları o tarihteki uzun sürüme (sn-jnl) göre verildi; güncel numaralar yukarıdaki tabloda.

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
  - **UFOKF tarzı karşılaştırma (Bölüm 8.1, Tablo 7 alt kısım, E11).** Doğrudan GL toplamı üzerinde unscented filtreler (bizim uygulamamız): kısaltılmış bellek yanlı; tam bellek bankayla aynı sonucu O(n) yerine O(K) maliyetle veriyor; B-tipinde pencereli UKF, B-EKF kadar iyi ama O(n).
  - **Toparlama:** sabit nokta ayrıntıları, durum eşlemesi şekli ve tablosu, mBm tablosu, CT tablosu ve iki türetme eki ek materyale taşındı. Katkı listesi altı maddeye indi, başlık güncellendi.
- **Ölçülmüş pil verisi (2026-10-09, Bölüm 8.2, E12/E12b):**
  - Panasonic 18650PF (Kollmeyer 2018, CC BY 4.0), 5 sıcaklık × 4 sürüş çevrimi ve 2 ısınma koşusu. SOC'ye bağlı RC + kesirli integral modeli, derece her örnekte değişiyor; A, B, sabit derece, 1RC, 2RC.
  - Birini dışarıda bırak doğrulaması (üç çevrime ortak uydurma, dördüncüyü simülasyon). Tek çevrime uydurma ve 600 s'lik bloklarla uydurma denendi; başka çevrimlere taşınmadığı için bırakıldı (tek çevrim sonuçları JSON'da ve metinde).
  - Ana bulgu: uydurulmuş modeli diğer tipin operatörüyle çalıştırmak hatayı 56 durumun 51'inde artırıyor (B → A: 28/28, medyan 4.4 kat). Aynı veriden A ve B farklı derece yasaları veriyor.
  - Dürüst sınır: değişken derece yalnızca 25 °C'de en iyi. 0 °C ve altında RC modelleri eşit ya da daha iyi; EIS karşılaştırması (E12b) düşük sıcaklık hatalarının doğrusal olmayan yük transferinden ve ısınmadan geldiğini gösteriyor. Bu sınır özet, sonuçlar ve tartışmada açıkça yazıldı.
  - Özet, katkı listesi, anahtar kelimeler, sonuç ve veri erişilebilirliği güncellendi; özet 248 kelime.
- **Üç ekleme (2026-10-07):**
  - **Operatör normu sınırları (Teorem 5, Not 2, Ek E; E7).** İleri tiplerde ℓ1/ℓ∞ göreli operatör hatası her derece dizisi için ≤ ε_R. Schur sabitleri ρ_row/ρ_col hiç aşılmadı ve sabit/kötü niyetli dizilerde tam yakalandı. Özyinelemeli integrallerde koşul sayısıyla (≈ 2N^a/Γ(1+a)) büyüme var; garanti için tasarım ε/κ ile yapılmalı. Adım yanıtından a-posteriori sertifika da verildi.
  - **Tam monoton çekirdek aileleri (Bölüm 6, Teorem 9, Ek F; E9).** Yapı, tersleme ve gereklilik sonuçları her CM aileye taşınıyor. Şerit analitikliği ve kuvvet yasası koşullarıyla hata terimleri ve K = O(ln(1/ε) ln(R/ε)) elde edildi; 35 tasarımda uydurulan katsayı 0.106, teoride 1/π² = 0.101. Örnekler: zamanla değişen dağılımlı derece, sabit temperleme. CT için Bernstein notu var.
  - **Karşılaştırma ve Pareto (Bölüm 7.8, Şekil 7; E8).** Kayan kutup (hot swap), budanmış GL, kısıtsız ve işaret kısıtlı LP artıkları karşılaştırıldı. Kural en küçük bankayı vermiyor: işaret kısıtlı LP %20–30, kısıtsız LP %40–50 daha az kutupla aynı doğruluğa ulaşıyor. Ancak kısıtsız LP ters kararlılık sertifikasını kaybediyor. Bu bulgu makalede açıkça yazıldı.
  - Yeni kaynaklar: Widder 1941, Sabzikar ve ark. 2015, Mainardi–Garrappa 2015 (Crossref ile doğrulandı).

## Yapılacaklar (gönderimden önce)

1. **Yazarlar:** isimler, kurumlar, e-postalar (`main.tex` ön kısmı ve `../paper_tsp/main.tex`; şu an yer tutucu).
2. ~~Kart ölçümleri~~ → yapıldı (2026-10-09, PYNQ-Z1; SP'de Bölüm 10 özet ve S14, TSP'de ana metin; `results/e5_board.json`). Önceki makalenin hiçbir ölçümü kullanılmadı.
3. **Önceki makalenin referansı:** `refs.bib` → `tcas_submission`. TCAS-I editörü önceki makaleyi kapsam dışı buldu; makale AEÜ'de incelemede. Başlık ve yazarlar eklenecek, karar gelince durum güncellenecek. TCAS-I bu makale için hedef değil; önerilen hedef Signal Processing (Elsevier).
4. **Kaynak doğrulama:** yapıldı (`litreview/verify_bib.py`). `montseny1998` doğrulandı ve DOI eklendi. Crossref'te olmayan kitaplar, INRIA raporu ve FCAA 2000 web üzerinden kontrol edildi. Yalnızca TCAS-I yer tutucusu kaldı.
5. **Literatür taraması:** Crossref + arXiv üzerinde yapıldı (`litreview/`: PROTOKOL.md, SENTEZ.md, FULLTEXT.md; 131 dahil kayıt). §1.1 ve Tablo 1 buna dayanıyor. Tam metin kontrolleri yapıldı; dört ifade düzeltildi ve bir öncül eklendi. **Kalan:** aynı dizgelerle Scopus/WoS tekrarı (metindeki kırmızı TODO kısaltmada çıkarıldı, burada takip ediliyor) ve FULLTEXT.md'de "okunamadı" diye işaretlenen 11 kaydın kurumsal erişimle okunması.
6. **Beyanlar:** finansman, çıkar çatışması, kod erişimi (depo URL'si veya Zenodo DOI), yazar katkıları, teşekkür.
7. **Kapak mektubu:** TCAS-I çalışmasıyla ilişki açıkça yazılmalı. Derginin eşzamanlı gönderim politikası kontrol edilmeli.
8. **Dergi yazım kuralları:** elsarticle'a geçildi (2026-10-09); ana metin 29 sayfa, sınır 30. Özet yaklaşık 245 kelime (sınır 250 kabul edildi). Anahtar kelime sayısı (şu an 7), sayfa sınırı ve ek materyal kuralları kılavuzdan doğrulanmalı. Highlights (3–5 madde, her biri ≤ 85 karakter) ve grafik özet istenip istenmediği de kontrol edilmeli.
9. **İsteğe bağlı:**
   - D/E tiplerinin keyfi anahtarlamada kararlılığı için bir sonuç (şu an tartışma bölümünde açık sınır olarak duruyor)
   - ~~çıkış düzeyinde hata kuralı~~ → Teorem 5 ile ℓ1/ℓ∞ en kötü durum anlamında yapıldı; özyinelemeli integraller için ε/κ kuralı Not 2'de
   - K için alt sınır (ortak kutup kümesi tek dereceye göre ne kadar büyük olmalı; açık soru olarak tartışmada)
   - işaret kısıtlı LP'yi kurala alternatif bir tasarım yolu olarak kütüphaneye eklemek (şu an `vofrac/baselines.py` içinde)
   - ~~VO derece kestirimi (EKF, O(K) Jacobian)~~ → Bölüm 8.1'de yapıldı (bilinen giriş); bilinmeyen giriş veya durumla ortak kestirim açık
   - boru hatlı çekirdek
