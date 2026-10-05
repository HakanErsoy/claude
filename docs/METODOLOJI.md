# CSSP Makalesi: Metodoloji ve Çalışma Planı

**Hedef dergi:** Circuits, Systems, and Signal Processing (Springer/Birkhäuser)
**Çalışma başlığı (taslak):**
*Definition-Consistent Realization of Variable-Order Fractional Operators with Fixed-Pole Banks: Theory, Discrete-Time Exactness, and Sample-Rate Order Scheduling*

Durum: **Aşama 1 (fikir doğrulama) tamamlandı.** E1/E1b ilk hipotezleri sayısal olarak doğruladı (bkz. §7).

---

## 1. Neden yeni bir yöntem? (TCAS-I çalışmasından ayrışma)

TCAS-I makalesi **sabit dereceli** s^α yaklaşımı üzerineydi: kutup–sıfır çiftli (Oustaloup tipi) yapı, regresyonla kalibre edilmiş kapalı-form bant kuralı (δ = 0.410 + 0.2275N + …), derece kuralı N = ⌊log₁₀r⌋ + 5, sabit noktalı kaskad mimarisi, pasif Foster-I eleman, çalışma anında derece seçen FPGA çekirdeği.

O çalışmada sıcak-değişim (hot-swap) testleri **durum korunarak katsayı değiştirmenin** çıkışı bozmadığını gösterdi. Ama şu soru açık kaldı: **α zamanla değiştiğinde bu yapı hangi değişken dereceli (VO) operatörü gerçekliyor?** CSSP makalesi tam bu soruya yanıt veriyor. Yani farklı bir nesne (zamanla değişen operatör), farklı bir teori (gerçekleme yapısı ile tanım arasındaki ilişki) ve farklı bir tasarım yöntemi (sabit kutuplu kuadratür, regresyonsuz analitik kural).

### Örtüşme koruması (çift yayın riskine karşı)

| Konu | TCAS-I (incelemede) | CSSP (yeni) |
|---|---|---|
| Operatör | sabit α | zamanla değişen α(t) |
| Kutuplar | α'ya bağlı (kutup–sıfır çiftleri) | **α'dan bağımsız** (sabit kutuplu banka) |
| Tasarım kuralı | regresyonla uydurulmuş δ(N, ᾱ, ρ̄) | Poisson + kuyruk sınırlarından **analitik** K(ε, bant, α-aralığı) |
| Ana iddia | doğruluk ve donanım verimi | **tanım tutarlılığı** (A/B tipi), ayrık-zamanda tamlık |
| Donanım | derece seçimli W48 çekirdeği, ms mertebesinde yeniden yükleme | **her örnekte** α güncelleme (sadece çıkış/giriş ağırlıkları) |

Kurallar:
- TCAS-I'den şekil, tablo veya metin yeniden kullanılmayacak. TCAS-I "under review" olarak atıf alacak, hot-swap sonucu sadece motivasyon cümlesi olarak geçecek.
- δ kuralı ve N = ⌊log₁₀r⌋ + 5 kuralı CSSP'de **kullanılmayacak**. Sabit kutuplu bankanın kendi analitik kuralı türetilecek.
- Kart ölçümleri CSSP için **yeniden** yapılacak (yeni çekirdek, yeni bitstream). Eski ölçümler raporlanmayacak.
- Gönderimden önce: Springer'in "eşzamanlı gönderim" politikası kontrol edilecek ve kapak mektubunda TCAS-I ile ilişki açıkça yazılacak.

---

## 2. Literatür konumu (ön tarama, tamamlanması gerekiyor)

- **VO tanımları:** Lorenzo–Hartley; Sierociuk, Malesza, Macias (A/B/C tipi GL tanımları, D/E özyinelemeli tanımlar, anahtarlama şemaları, domino-merdiven analog gerçeklemesi, iki derece arasında anahtarlama). [arXiv:1304.5072](https://arxiv.org/pdf/1304.5072)
- **Sabit kutuplu yaklaşım (sabit α için):** Wei ve ark., ISA Trans. 2016 ([link](https://www.sciencedirect.com/science/article/abs/pii/S0019057816000288)), ISA Trans. 2019 ([link](https://www.sciencedirect.com/science/article/abs/pii/S0019057818303707)). Burada VO tanım tutarlılığı ele alınmıyor; α≈0 çevresinde iyileştirme gerekiyor (bizdeki kuyruk düzeltmesi bunu analitik olarak çözüyor).
- **Zamanla değişen derece için devre:** Arıcıoğlu, Axioms 2025 ([link](https://doi.org/10.3390/axioms14040310)). LTI tabanlı tanım kullanıyor, hangi VO tanımının gerçeklendiği analiz edilmiyor.
- **Difüzif gösterim kuadratürü:** Diethelm 2023 ([arXiv:2301.11931](https://arxiv.org/pdf/2301.11931)), sadece sabit α.
- **Uygulama adayı:** Sheng, Sun, Chen, Qiu, "Synthesis of multifractional Gaussian noises based on variable-order fractional operators", Signal Processing 2011.

**Boşluk:** Sonlu boyutlu (rasyonel) VO gerçeklemelerinde *hangi tanımın gerçeklendiği* yapısal olarak hiç analiz edilmemiş. Tanımı "yapıdan seçen" bir tasarım yöntemi de önerilmemiş.
**Yapılacak:** Scopus/WoS'ta sistematik tarama ("variable order" ∧ (realization ∨ approximation ∨ FPGA ∨ analog)), son 10 yıl, CSSP/FCAA/Nonlinear Dyn/Signal Process./ISA Trans./Mechatronics.

---

## 3. Temel fikir

Difüzif gösterim (0 < a < 1):

    s^(-a) = (sin aπ/π) ∫₀^∞ ξ^(-a) /(s+ξ) dξ,        s^(+a) = (sin aπ/π) ∫₀^∞ ξ^(a-1) · s/(s+ξ) dξ

Geometrik ξ_k ızgarasında trapez kuralı uygulanınca **kutuplar α'dan bağımsız** kalıyor, α sadece ağırlıklara giriyor:

    H_α(s) = Σ_k m_k(α) · ξ_k/(s+ξ_k) + d(α)

Kesilen kuyruklar analitik olarak geri katılıyor (biri doğrudan geçiş terimine, diğeri en dış kutba). Böylece **tek bir durum bankası** −1 < α < 1 aralığının tamamını, α = 0 geçişi dahil sürekli olarak kapsıyor.

**Yapı tanımı belirliyor:**
- **Çıkış zamanlaması** (x' = −Ξx + Ξu, y = m(α(t))ᵀx + d(α(t))u): tüm geçmiş *güncel* dereceyle ağırlıklanır → **A-tipi** (Sierociuk Tanım 2, "order memory yok").
- **Giriş zamanlaması** (x' = −Ξx + Ξ m(α(t)) u, y = 1ᵀx + d u): her örnek *girdiği andaki* dereceyle ağırlıklanır → **B-tipi** (Tanım 3, "zayıf order memory").

**Ayrık-zaman tamlığı:** GL ağırlıklarının Beta-integral gösterimi

    (−1)^r C(a, r) = −(sin aπ/π) ∫₀¹ θ^r · θ^(−a−1)(1−θ)^a dθ,   r ≥ 1

GL ağırlıklarını sabit ayrık kutupların (θ_k = e^(−ξ_k Ts)) geometrik dizilerinin süperpozisyonu olarak yazıyor. Aynı yerleştirme kuralıyla Tanım 2 ve Tanım 3 **sadece kuadratür hatasıyla** gerçekleniyor; ZOH ayrıklaştırma hatası yok. (Bu, sürekli-zaman bankasında yumuşak α(t) ile türevde gözlenen sorunu da ortadan kaldırıyor, bkz. §7.)

### Çekirdek teorem adayı (ispat yazılacak)

> **Teorem (gereklilik).** (A(α), B(α), C(α), D(α)) minimal gerçeklemeler olsun. α₁ → α₂ anahtarlamasında A-tipi davranışı **her giriş için** tam veren doğrusal bir durum eşlemesi Φ (x⁺ = Φx⁻) ancak ve ancak (A(α₁), B(α₁)) ile (A(α₂), B(α₂)) benzer ise, yani kutuplar dereceden bağımsızsa vardır.
>
> *Taslak:* x₂(T) = Φx₁(T) her u için ⇔ e^{A₂s}B₂ = Φe^{A₁s}B₁, ∀s ≥ 0 ⇔ (minimallikte) A₂ = ΦA₁Φ⁻¹, B₂ = ΦB₁.

**Sonuç:** Oustaloup, CFE, Matsuda, Carlson gibi kutupları α'ya bağlı tüm yaklaşımlar, durum eşlemesi nasıl seçilirse seçilsin anahtarlamada tanımsal hata üretir. Sabit kutuplu bankada Φ = I ve tanımsal hata sıfırdır.

---

## 4. Hipotezler

| # | Hipotez | Durum |
|---|---|---|
| H1 | Çıkış zamanlamalı sabit kutuplu banka A-tipini izler; hata kuadratürle üstel azalır | **Doğrulandı** (E1, E1b) |
| H2 | Giriş zamanlamalı banka B-tipini izler | **Doğrulandı.** CT bankada yumuşak α'lı türev hariç; DT bankada tüm durumlar |
| H3 | Durum korumalı Oustaloup: kaskad hiçbir tanıma yakınsamaz; paralel A'ya yavaş (cebirsel) yakınsar | **Doğrulandı** (E1) |
| H4 | Gerekli K, bant ve α-aralığı için analitik kural (Poisson ayrıklaştırma + kuyruk sınırları) regresyonsuz verilebilir | Açık (E3) |
| H5 | D/E tipleri, OS/IS bankaların geri-besleme ile terslenmesiyle (dualite) gerçeklenebilir | Açık. Önce tanımlar literatürden kesinleştirilecek (E4) |
| H6 | Örnek hızında α güncelleme donanımda ucuzdur: geometrik ızgara sayesinde ağırlıklar m_{k+1} = m_k · q^(±α) özyinelemesiyle üretilir | Açık (E5, RTL + kart) |
| H7 | Uygulama: gerçek zamanlı multifraksiyonel Brown hareketi (RL-mBm = A-tipi) sentezi, O(K) maliyetle | Açık (E6) |

---

## 5. Deney planı

| Deney | İçerik | Çıktı |
|---|---|---|
| **E1** (CT) | Basamak girişi, kapalı-form A/B referansları; 6 anahtarlama + 3 yumuşak profil; S = 7…41 durum | `results/e1_*.json`, `fig_e1_*.png` |
| **E1b** (DT) | GL Tanım 2/3 referansları; basamak, beyaz gürültü, çoklu sinüs; 7 profil; *tanımsal hata* metriği | `results/e1b_discrete.json` |
| **E2** | Tanımsal hata ile durum eşlemesi ilişkisi: Oustaloup için en küçük kareler optimal Φ ile bile hatanın sıfıra inmediğini göstermek (teoremin sayısal kanıtı) | planlı |
| **E3** | Analitik K kuralı: ε ∈ {1e-2, 1e-3, 1e-4}, bant 2–6 dekad, α-aralıkları; kuralın tahmini ile gerçek hatanın karşılaştırılması; holdout kümesi ayrı tutulacak | planlı |
| **E4** | D/E tipleri: geri-beslemeli terslemenin doğrulanması | planlı |
| **E5** | Sabit nokta + RTL: ağırlık üretici (sin, exp2 LUT + çarpım zinciri), kelime uzunluğu taraması, xsim paritesi, kartta ölçüm (kaynak, gecikme, α-güncelleme hızı) | planlı |
| **E6** | mBm sentezi: yerel Hurst tahmini (artış varyansı / dalgacık), A/B farkı, maliyet karşılaştırması (Cholesky, FFT, GL O(n²)) | planlı |

**İstatistik ve tekrarlanabilirlik:** sabit tohumlar; tüm deneyler `python3 experiments/<e>.py` ile tek komutla üretiliyor; testler `pytest`. E3'te geçme/kalma için Clopper–Pearson alt sınırı kullanılacak (TCAS-I'deki yaklaşımla tutarlı).

---

## 6. Makale iskeleti (CSSP)

1. Introduction: VO tanımlarının çokluğu, pratik gerçeklemelerin tanım belirsizliği, katkılar
2. Preliminaries: A/B tipi tanımlar, difüzif gösterim, kapalı-form basamak yanıtları (B-tipi için kısmi integrasyon formülü)
3. Fixed-pole banks: CT kuadratür, kuyruk düzeltmeleri, α = 0 sürekliliği
4. Definition by structure: OS → A, IS → B (önermeler), gereklilik teoremi
5. Discrete-time exactness: Beta-integral gösterimi, ayrık banka, Tanım 2/3'ün kuadratür hatası dışında tam gerçeklenmesi
6. Design rule: analitik K(ε, bant, α-aralığı)
7. Hardware: örnek hızında α güncelleme, sabit nokta analizi, FPGA ölçümleri
8. Application: gerçek zamanlı mBm sentezi
9. Conclusion
Ekler: ispatlar, referans formüllerin GL ile doğrulanması

CSSP formatı: Springer `sn-jnl` şablonu; Data Availability ve Conflict of Interest beyanları.

---

## 7. İlk sonuçlar (Aşama 1)

### E1: CT, basamak girişi, kapalı-form referanslar (S = durum sayısı)

Anahtarlamadan sonraki bağıl RMS hata (A-tipine / B-tipine göre), S = 15 → 41:

| α₁ → α₂ | A–B farkı | FP-out (A) | FP-in (B) | Ou-par (A) | Ou-cas (A / B) |
|---|---|---|---|---|---|
| −0.3 → −0.7 | 0.52 | 1.9e-3 → 3.9e-4 | 1.2e-3 → 2.1e-4 | 0.12 → 0.042 | 0.16 / 0.33 (sabit) |
| +0.3 → +0.7 | 0.65 | 1.4e-3 → 1.4e-4 | 4.2e-3 → 1.1e-4 | 0.14 → 0.053 | 1.7 / 1.7 (sabit) |
| −0.5 → +0.5 | 0.81 | 1.7e-3 → 2.1e-4 | 1.4e-3 → 1.9e-4 | 0.23 → 0.085 | 4.6 / 1.6 (sabit) |
| +0.5 → −0.5 | 1.35 | 1.1e-3 → 1.8e-4 | 1.2e-3 → 1.1e-4 | 0.25 → 0.080 | 0.24 / 0.87 (sabit) |

- Anahtarlamadan **önce** (sabit derece) tüm yapıların hatası benzer (1e-3 ile 1e-4 arası). Fark tamamen anahtarlamadan, yani tanımsal etkiden geliyor.
- Kaskad Oustaloup'ta derece artınca hata **azalmıyor**. Paralel Oustaloup A-tipine yavaş yakınsıyor (kutup kayması, kutup aralığının sabit bir kesri olduğu için). Sabit kutuplu banka eşit durum sayısında 100–1000 kat daha doğru.
- **Bulgu (olumsuz, raporlanacak):** CT giriş-zamanlamalı banka, yumuşak α(t) ile *türevde* başarısız (bağıl hata ~12). Nedeni: 1/Ts'den hızlı modlar örneklenmiş α'nın her adımdaki sıçramasına türev gibi yanıt veriyor. Bu bulgu §3'teki ayrık-zaman formülasyonunu gerekçelendiriyor (E1b'de sorun ortadan kalkıyor).

### E1b: DT banka ile GL Tanım 2/3 (Ts = 1 ms, 4001 örnek; DFP: 32 mod + gecikme modu; Oustaloup: N = 15, 31 durum)

**Toplam hata** (GL referansına göre, bağıl RMS), 7 α profili × 3 giriş:
- DFP-out → Tanım 2: **5.6e-6 … 2.1e-3**. DFP-in → Tanım 3: **5.6e-6 … 1.7e-3**. Yumuşak α ile türev dahil, CT'deki sorun ortadan kalktı.

**Tanımsal hata** (her gerçeklemenin kendi dondurulmuş-derece LTI eşdeğerine göre; yaklaşım kalitesinden bağımsız), parçalı-sabit profiller:

| Gerçekleme | kendi A-tipine göre | kendi B-tipine göre |
|---|---|---|
| DFP-out | **0 (tam)** | = A–B farkı |
| DFP-in | = A–B farkı | **≤ 1e-14** (yuvarlama) |
| Ou-par | 4e-6 … 0.13 (girişe bağlı, en kötüsü basamakta) | 7e-3 … 1.0 |
| Ou-cas | 7e-3 … **3.0e+3** (−0.5 → +0.5 basamak) | 0.03 … 4.8e+2 |

Yorum: gereklilik teoremi sayısal olarak doğrulandı. Tanımsal hata sıfırsa yapı tanımı tam gerçekliyor, değilse hiçbir derece artışı onu gidermiyor.
Not: Oustaloup'un GL'ye göre *toplam* hatası gürültü/çoklu sinüs girişlerinde büyük çıkıyor (≈10). Bu tanımsal bir etki değil, CT tasarımın (bant 1e5 rad/s > Nyquist) ZOH ile ayrıklaştırılmasından kaynaklanan statik CT/DT uyumsuzluğu. Bu yüzden karşılaştırmada tanımsal hata metriği esas alınacak.

---

## 8. Sonraki adımlar

1. E2 (gereklilik teoreminin sayısal kanıtı) ve teoremin tam ispatı
2. E3: analitik K kuralının türetilmesi ve holdout doğrulaması
3. Sistematik literatür taraması (§2)
4. E5: RTL ağırlık üretici, TCAS-I'deki W48 altyapısı yeniden kullanılarak ama yeni çekirdekle
5. E6 uygulaması (mBm). Alternatif: VO kesirli PID veya zamanla değişen spektral eğimli filtre
