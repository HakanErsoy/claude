# CSSP Makalesi: Metodoloji ve Çalışma Planı

**Hedef dergi:** Circuits, Systems, and Signal Processing (Springer/Birkhäuser)
**Çalışma başlığı (taslak):**
*Definition-Consistent Realization of Variable-Order Fractional Operators with Fixed-Pole Banks: Theory, Discrete-Time Exactness, and Sample-Rate Order Scheduling*

Durum: **Aşama 6: makale taslağı başladı** (`paper/`, Springer `sn-jnl`, bkz. [`paper/README.md`](../paper/README.md)). **Aşama 5 tamamlandı (E1–E6).** E1/E1b tanım tutarlılığını, E2 durum eşlemesi alternatifinin sınırlarını, E3 analitik tasarım kuralını, E4 dört VO tipinin (A/B/D/E) tek bankadan gerçeklenmesini, E5 sabit noktalı RTL'nin bit-tam doğruluğunu ve kaynak tahminini, E6 gerçek zamanlı multifraksiyonel Brown hareketi sentezini gösterdi (bkz. §7). Kart ölçümleri bekliyor.

---

## 1. Neden yeni bir yöntem? (TCAS-I çalışmasından ayrışma)

TCAS-I makalesi **sabit dereceli** s^α yaklaşımı üzerineydi: kutup–sıfır çiftli (Oustaloup tipi) yapı, regresyonla kalibre edilmiş kapalı-form bant kuralı (δ = 0.410 + 0.2275N + …), derece kuralı N = ⌊log₁₀r⌋ + 5, sabit noktalı kaskad mimarisi, pasif Foster-I eleman, çalışma anında derece seçen FPGA çekirdeği.

O çalışmada sıcak-değişim (hot-swap) testleri **durum korunarak katsayı değiştirmenin** çıkışı bozmadığını gösterdi. Ama şu soru açık kaldı: **α zamanla değiştiğinde bu yapı hangi değişken dereceli (VO) operatörü gerçekliyor?** CSSP makalesi tam bu soruya yanıt veriyor. Yani farklı bir nesne (zamanla değişen operatör), farklı bir teori (gerçekleme yapısı ile tanım arasındaki ilişki) ve farklı bir tasarım yöntemi (sabit kutuplu kuadratür, regresyonsuz analitik kural).

### Örtüşme koruması (çift yayın riskine karşı)

| Konu | Önceki makale (sabit derece; TCAS-I kapsam dışı buldu, AEÜ'de incelemede) | Bu makale (yeni) |
|---|---|---|
| Operatör | sabit α | zamanla değişen α(t) |
| Kutuplar | α'ya bağlı (kutup–sıfır çiftleri) | **α'dan bağımsız** (sabit kutuplu banka) |
| Tasarım kuralı | regresyonla uydurulmuş δ(N, ᾱ, ρ̄) | Poisson + kuyruk sınırlarından **analitik** K(ε, bant, α-aralığı) |
| Ana iddia | doğruluk ve donanım verimi | **tanım tutarlılığı** (A/B tipi), ayrık-zamanda tamlık |
| Donanım | derece seçimli W48 çekirdeği, ms mertebesinde yeniden yükleme | **her örnekte** α güncelleme (sadece çıkış/giriş ağırlıkları) |

Kurallar:
- TCAS-I'den şekil, tablo veya metin yeniden kullanılmayacak. Önceki makale "AEÜ'de incelemede" olarak atıf alacak (karar gelince güncellenecek), hot-swap sonucu sadece motivasyon cümlesi olarak geçecek.
- δ kuralı ve N = ⌊log₁₀r⌋ + 5 kuralı CSSP'de **kullanılmayacak**. Sabit kutuplu bankanın kendi analitik kuralı türetilecek.
- Kart ölçümleri CSSP için **yeniden** yapılacak (yeni çekirdek, yeni bitstream). Eski ölçümler raporlanmayacak.
- Gönderimden önce: Springer'in "eşzamanlı gönderim" politikası kontrol edilecek ve kapak mektubunda TCAS-I ile ilişki açıkça yazılacak.

---

## 2. Literatür konumu

**Sistematik tarama yapıldı** (2026-10-06): [`litreview/PROTOKOL.md`](../litreview/PROTOKOL.md), [`litreview/SENTEZ.md`](../litreview/SENTEZ.md).
- Kapsam: Crossref ve arXiv, 30 sorgu, 2639 kayıt, 1702 tekil. Kural filtresinden 368 kayıt geçti; elle elemeden ve kartopundan sonra 129 kayıt dahil edildi.
- **Ana sonuç:** VO Caputo için dereceden bağımsız üstel toplam (Zhang–Fang–Sun 2021–2022) ve mBm'de A/B ayrımı (MMFBM, Wang ve ark. 2023) öncül çalışmalar. Yapı ⇔ tanım bağı, A ve B'nin tek bankada gerçeklenmesi, ayrık-zaman GL tamlığı, D/E terslemesi, kural, kararlılık ve donanım için öncül bulunmadı. Makalenin katkı listesi buna göre güncellendi.

İlk ön tarama notları:

- **VO tanımları:** Lorenzo–Hartley; Sierociuk, Malesza, Macias (A/B/C tipi GL tanımları, D/E özyinelemeli tanımlar, anahtarlama şemaları, domino-merdiven analog gerçeklemesi, iki derece arasında anahtarlama). [arXiv:1304.5072](https://arxiv.org/pdf/1304.5072)
- **D/E tanımları ve dualite (E4'te kullanılan birincil kaynaklar):** Sierociuk, Macias, Malesza, Wiraszka, *Electronics* 9 (2020) 855, denklem (7)–(8) ([PDF](https://mdpi-res.com/d_attachment/electronics/electronics-09-00855/article_deploy/electronics-09-00855.pdf)); Sierociuk ve ark., *CSSP* 35 (2016) 2055–2082, Remark 2 ([açık erişim](https://d-nb.info/1095394320/34)); Sierociuk, Malesza, Macias, *CSSP* 34 (2015) 1077–1113 (özyinelemeli tanım, dualite, analog model). Son ikisi hedef dergide yayımlanmış; mutlaka atıf alacaklar.
- **Sabit kutuplu yaklaşım (sabit α için):** Wei ve ark., ISA Trans. 2016 ([link](https://www.sciencedirect.com/science/article/abs/pii/S0019057816000288)), ISA Trans. 2019 ([link](https://www.sciencedirect.com/science/article/abs/pii/S0019057818303707)). Burada VO tanım tutarlılığı ele alınmıyor; α≈0 çevresinde iyileştirme gerekiyor (bizdeki kuyruk düzeltmesi bunu analitik olarak çözüyor).
- **Zamanla değişen derece için devre:** Arıcıoğlu, Axioms 2025 ([link](https://doi.org/10.3390/axioms14040310)). LTI tabanlı tanım kullanıyor, hangi VO tanımının gerçeklendiği analiz edilmiyor.
- **Difüzif gösterim kuadratürü:** Diethelm 2023 ([arXiv:2301.11931](https://arxiv.org/pdf/2301.11931)), sadece sabit α.
- **Uygulama (E6):**
  - RL-mBm: Lim, *J. Phys. A* 34 (2001) 1301; Muniandy ve Lim, *Phys. Rev. E* (2001)
  - Homojen olmayan kesirli integrasyon, B-tipi benzeri süreçler: Surgailis, *Stoch. Proc. Appl.* 118 (2008) 171–198
  - VO operatörleriyle mGn sentezi: Sheng, Sun, Chen, Qiu, *Signal Processing* 91 (2011) 1645–1650
  - Güncel mBm yazılımları: R paketi Rmfrac (2026), MATLAB mBm (Rabelaiss)
  - Yerel Hurst kestiricisi: genelleştirilmiş kuadratik varyasyon (Istas–Lang, Coeurjolly 2005)

**Boşluk:** Sonlu boyutlu (rasyonel) VO gerçeklemelerinde *hangi tanımın gerçeklendiği* yapısal olarak hiç analiz edilmemiş. Tanımı "yapıdan seçen" bir tasarım yöntemi de önerilmemiş.
**Yapılacak (kısmen yapıldı, §2 başı):** Scopus/WoS'ta sistematik tarama ("variable order" ∧ (realization ∨ approximation ∨ FPGA ∨ analog)), son 10 yıl, CSSP/FCAA/Nonlinear Dyn/Signal Process./ISA Trans./Mechatronics.

---

## 3. Temel fikir

Difüzif gösterim (0 < a < 1):

    s^(-a) = (sin aπ/π) ∫₀^∞ ξ^(-a) /(s+ξ) dξ,        s^(+a) = (sin aπ/π) ∫₀^∞ ξ^(a-1) · s/(s+ξ) dξ

Geometrik ξ_k ızgarasında trapez kuralı uygulanınca **kutuplar α'dan bağımsız** kalıyor, α sadece ağırlıklara giriyor:

    H_α(s) = Σ_k m_k(α) · ξ_k/(s+ξ_k) + d(α)

Kesilen kuyruklar analitik olarak geri katılıyor (biri doğrudan geçiş terimine, diğeri en dış kutba). Böylece **tek bir durum bankası** −1 < α < 1 aralığının tamamını, α = 0 geçişi dahil sürekli olarak kapsıyor.

**Kuyruk kapanışı (E3'te geliştirildi):** Tüm düğümler tam h ağırlığı taşıyor. Her kuyruk, ızgaranın ötesindeki *sanal trapez düğümlerinin geometrik serisiyle* kapatılıyor ("Poisson-tutarlı kapanış"). Banka böylece sonsuz trapez kuralına eşit oluyor; yarım uç ağırlıklarının h² mertebesindeki Euler–Maclaurin uç hatası ortadan kalkıyor. Kalan hata yalnızca kapalı formda yazılabilen üç terimden oluşuyor (§3.1).

**Yapı tanımı belirliyor:**
- **Çıkış zamanlaması** (x' = −Ξx + Ξu, y = m(α(t))ᵀx + d(α(t))u): tüm geçmiş *güncel* dereceyle ağırlıklanır → **A-tipi** (Sierociuk Tanım 2, "order memory yok").
- **Giriş zamanlaması** (x' = −Ξx + Ξ m(α(t)) u, y = 1ᵀx + d u): her örnek *girdiği andaki* dereceyle ağırlıklanır → **B-tipi** (Tanım 3, "zayıf order memory").

**Ayrık-zaman tamlığı:** GL ağırlıklarının Beta-integral gösterimi

    (−1)^r C(a, r) = −(sin aπ/π) ∫₀¹ θ^r · θ^(−a−1)(1−θ)^a dθ,   r ≥ 1

GL ağırlıklarını sabit ayrık kutupların (θ_k = e^(−ξ_k Ts)) geometrik dizilerinin süperpozisyonu olarak yazıyor. Aynı yerleştirme kuralıyla Tanım 2 ve Tanım 3 **sadece kuadratür hatasıyla** gerçekleniyor; ZOH ayrıklaştırma hatası yok. (Bu, sürekli-zaman bankasında yumuşak α(t) ile türevde gözlenen sorunu da ortadan kaldırıyor, bkz. §7.)

### 3.1 Analitik hata modeli (E3, regresyonsuz)

CT, |H/s^α − 1|, ω₁ ≤ ω ≤ ω₂; S = sin(π|α|)/π, G(p) = h/(e^{ph}−1), H(p,q) = G(p) − G(q):

| Terim | integral (α = −a < 0) | türev (α = a > 0) |
|---|---|---|
| kuadratür (ilk Poisson aliası) | 2·sin(πa)·e^{−π²/h} | aynı |
| alt kuyruk | S·(ξ_lo/ω₁)^{2−a}·H(1−a, 2−a) | S·(ξ_lo/ω₁)^{1+a}·G(1+a) |
| üst kuyruk | S·(ω₂/ξ_hi)^{1+a}·G(1+a) | S·(ω₂/ξ_hi)^{2−a}·H(1−a, 2−a) |

Integral ile türev arasındaki alt↔üst simetrisi kendiliğinden çıkıyor. DT'de (GL ağırlıkları, 1 ≤ r < R, u = ξTs):
- kuadratür: büyük r için 2√(2π)·(2π/h)^{a+½}·e^{−π²/h}/Γ(1+a); küçük r'de alias genliği temsilden doğrudan hesaplanıyor
- alt kuyruk: (r−1)·u_lo^{2+a}·H(1+a, 2+a)/B(r−a, 1+a), en kötüsü r = R−1'de
- üst kuyruk: Σ_j h·u_j·e^{−(2−a)u_j}(1−e^{−u_j})^a / B(2−a, 1+a)

**Kural:** ε bütçesi ε/2 (kuadratür) + ε/4 + ε/4 (kuyruklar) olarak bölünüyor. CT'de h = π²/ln(4·max|sin πα|/ε) kapalı form; kuyruk oranları her α için güç yasasından kapalı formda bulunuyor ve en dar olanı seçiliyor. K = ⌈ln(ξ_hi/ξ_lo)/h⌉ + 1. DT'de h ve u_hi tek boyutlu monoton kök bulmayla, u_lo kapalı formla bulunuyor.

### 3.4 Tamsayı integratörle bileşim (E6)

Derece 1'i aşınca (ör. RL-mBm'de a = H + ½ ∈ (½, 3/2)) bir tamsayı integrasyonu ayırmak ayrık zamanda **tam**, ama yalnızca doğru yerde:
- **A-tipi:** önce integre et: A^{−a} ξ = A^{−(a−1)}(cumsum ξ)
- **B-tipi:** sonra integre et: B^{−a} ξ = cumsum(B^{−(a−1)} ξ)

Ters sıralar tam değil (bağıl hata 0.1–1.3). Bu sayede tek bir banka 1/2 − H derecesinde (|α| < ½) 0 < H < 1 aralığının tamamını kapsıyor ve H = ½'yi pürüzsüz geçiyor (bankada α = 0 tam).

### 3.2 Gereklilik teoremi ve pratik karşılığı (E2 ile düzeltildi)

> **Teorem (gereklilik).** (A(α), B(α), C(α), D(α)) minimal gerçeklemeler olsun. α₁ → α₂ anahtarlamasında A-tipi davranışı **her giriş için tam** veren doğrusal bir durum eşlemesi Φ (x⁺ = Φx⁻) ancak ve ancak (A(α₁), B(α₁)) ile (A(α₂), B(α₂)) benzer ise vardır. B-tipi için de aynısı (C, A) çifti üzerinden geçerli.
>
> *Taslak:* x₂(T) = Φx₁(T) her u için ⇔ e^{A₂s}B₂ = Φe^{A₁s}B₁, ∀s ≥ 0 ⇔ (minimallikte) A₂ = ΦA₁Φ⁻¹, B₂ = ΦB₁. B-tipi: C₂e^{A₂s}Φ = C₁e^{A₁s}, ∀s ≥ 0.

**E2'nin gösterdiği (dürüst çerçeve):** *Tam* eşleme imkânsız, ama *yaklaşık* eşleme mümkün. İyi regülarize edilmiş yoğun bir Φ, S ≥ 21'de float64'te tanımsal hatayı 1e-5…1e-8'e indiriyor; çünkü iki kutup kümesinin erişilebilir durum bilgisi pratikte düşük boyutlu bir alt uzayda örtüşüyor. Yani makalenin iddiası "eşleme işe yaramaz" değil, şu:
1. Hot-swap (Φ = I) tanımsal olarak yanlış; kaskadda S artınca da düzelmiyor.
2. Yaklaşık eşleme her derece çifti için yoğun bir S×S matris istiyor (örnek başına S² MAC, çift başına S² kelime bellek, eğitim ya da Gramian çözümü). Ayrıca girdi istatistiğine bağlı: basamak gibi dağılım dışı girişlerde hata 1–2 mertebe kötüleşiyor.
3. Sayısal olarak kırılgan: ‖Φ‖ 1e3–1e10. 24-bit sabit noktada kaskadda hata 20–800'e çıkıyor, paralelde (S ≥ 15) 4e-3 ile 1e-1 arasında kalıyor (float64'te 5e-8).
4. Sabit kutuplu bankada Φ = I, tanımsal hata **tam 0**, ek maliyet yok, kuantizasyona karşı bir kuvvetlenme yok.

### 3.3 Tek bankadan dört tip: D ve E (E4)

Birincil kaynaktaki tanımlar (Electronics 2020, denklem 7–8):

    D-tipi: z_k = x_k/h^{α_k} − Σ_{j≥1} (−1)^j C(−α_k, j) · z_{k−j}
    E-tipi: z_k = x_k/h^{α_k} − Σ_{j≥1} (−1)^j C(−α_{k−j}, j) · (h^{α_{k−j}}/h^{α_k}) · z_{k−j}

Matris formuyla gösterilen ilişki **D^α = (A^{−α})⁻¹, E^α = (B^{−α})⁻¹** (iki yönlü ters). Literal özyinelemelerle 1e-13 hassasiyetle doğrulandı. Bankada her örnekte operatör çıkışı g₀(α)·v_k + hist_k biçiminde ve hist yalnızca geçmişe bağlı, çünkü kutuplar dereceden bağımsız. g₀ = Ts^{−α} hiç sıfır olmadığından:
- **A, B:** ileri yön (çıkış / giriş zamanlaması)
- **D:** çıkış-zamanlamalı bankanın −α derecesinde cebirsel tersi: v_k = (x_k − hist_k)/g₀
- **E:** giriş-zamanlamalı bankanın −α derecesinde cebirsel tersi

Dördü de O(K) maliyetli. Dualite banka içinde yuvarlama düzeyinde korunuyor; dolayısıyla Malesza ve ark.'nın dualiteye dayalı analitik çözüm yöntemleri bankaya doğrudan taşınabiliyor. Aynı yapı T^α y + λy = u (T ∈ {A,B,D,E}) VO gevşeme denklemini de O(K) maliyetle çözüyor.

**Önerme (ters kararlılık):**
- *İntegral dereceleri:* bütün rezidüler pozitif, dolayısıyla H'nin sıfırları (0,1) içindeki kutupların arasına düşüyor ve ters her zaman kararlı.
- *Türev dereceleri:* gecikme modu dışında bütün rezidüler negatif; z·H(z), z > θ_max'ta artan. Ters kararlı ⇔ H(1) = Σ_r g_r > 0 (c_d > 0 ise ayrıca H(−1) > 0).
- *Ek koşul (taslakta tamamlandı):* gecikme kutbu z = 0 olduğundan son sıfır negatif eksene düşebiliyor. Bu yüzden integral bankasında da H(−1) > 0 gerekiyor. İlk iki ağırlık 1/3 doğrulukla gerçekleniyorsa bu kendiliğinden sağlanıyor. Holdout'ta H(−1), tam değeri 2^α·g₀'a %0.06 içinde yakın. İspat: makale Ek B.
- Gerçek GL değeri 0. Büyük α'da DC toplamının kuadratür hatası H(1)'i hafifçe negatife itebiliyor. **DC tabanı**, kuyruğun doğal pozitif DC katkısının %1'i (0.01·|S|·g₀·u_lo^α/(α(1+α))) ve gecikme modu üzerinden uygulanıyor.
- Taban yalnızca g₁'i, yaklaşık DC kuadratür hatası kadar değiştiriyor. E3 holdout sonuçları byte düzeyinde aynı kaldı.
- Kararlılık özdeğerle değil H(1)'in işaretiyle test ediliyor, çünkü kutuplar 1'e çok yakın kümelendiğinde özdeğer çözücü güvenilmez.

---

## 4. Hipotezler

| # | Hipotez | Durum |
|---|---|---|
| H1 | Çıkış zamanlamalı sabit kutuplu banka A-tipini izler; hata kuadratürle üstel azalır | **Doğrulandı** (E1, E1b) |
| H2 | Giriş zamanlamalı banka B-tipini izler | **Doğrulandı.** CT bankada yumuşak α'lı türev hariç; DT bankada tüm durumlar |
| H3 | Durum korumalı Oustaloup: kaskad hiçbir tanıma yakınsamaz; paralel A'ya yavaş (cebirsel) yakınsar | **Doğrulandı** (E1) |
| H3b | Optimal durum eşlemesi bile tanımsal hatayı sıfırlayamaz | **Kısmen.** Tam sıfır imkânsız (teorem), ama float64'te 1e-8'e iniyor. Bedeli yoğun S×S eşleme, girdi bağımlılığı ve sabit noktada kırılganlık (E2) |
| H4 | Gerekli K, bant ve α-aralığı için analitik kural (Poisson ayrıklaştırma + kuyruk sınırları) regresyonsuz verilebilir | **Doğrulandı** (E3: mühürlü holdout 400/400, CP95 alt sınırı %98.5, K − K_min ≤ 3) |
| H5 | D/E tipleri, OS/IS bankaların geri-besleme ile terslenmesiyle (dualite) gerçeklenebilir | **Doğrulandı** (E4: literal GL'ye göre ≤6.5e-5, kendi tipine göre ≤3e-13, dualite ≤2e-14) |
| H5b | Ters her derecede kararlı | **DC tabanıyla doğrulandı.** Tabansız E3 holdout tasarımlarının 99/200'ünde en az bir derecede ters kararsız; tabanla 200/200 kararlı |
| H5c | Hot-swap edilen Oustaloup tutarlı bir tip gerçekler | **Reddedildi.** Paralel form yaklaşık A, kaskadda en yakın tip girişe göre A/B/D/E arasında değişiyor. Bant > Nyquist iken D/E referansları bile kurulamıyor (ZOH üyeleri minimum-fazlı değil) |
| H6 | Örnek hızında α güncelleme donanımda ucuzdur | **RTL'de doğrulandı** (E5): derece değişimi yalnızca bir ROM adresi, örnek başına 136 çevrim, 0 uyumsuzluk. Kart ölçümü bekliyor. (İlk hipotezdeki q^(±α) özyinelemesi DT bankada kesin değil; yerine P = 1024 seviyeli katsayı tablosu kullanıldı) |
| H6b | Kuantizasyon ters kararlılığı bozabilir | **Doğrulandı.** Float katsayılar tabanlı olsa bile, kuantizasyondan sonra pozitif derece girişlerinin ~%10'unda H_q(1) ≤ 0 çıkıyor. Kuantizasyona duyarlı taban ile 0 |
| H7 | Uygulama: gerçek zamanlı multifraksiyonel Brown hareketi (RL-mBm = A-tipi) sentezi, O(K) maliyetle | **Doğrulandı** (E6): yollar GL'ye 1e-6, varyans ve kovaryans tam formüle ≤3e-5 ve ≤2e-6 yakın; örnek başına 47–55 MAC; sabit noktalı çekirdekle A-tipi 1.8e-5 |

---

## 5. Deney planı

| Deney | İçerik | Çıktı |
|---|---|---|
| **E1** (CT) | Basamak girişi, kapalı-form A/B referansları; 6 anahtarlama + 3 yumuşak profil; S = 7…41 durum | `results/e1_*.json`, `fig_e1_*.png` |
| **E1b** (DT) | GL Tanım 2/3 referansları; basamak, beyaz gürültü, çoklu sinüs; 7 profil; *tanımsal hata* metriği | `results/e1b_discrete.json` |
| **E2** | En küçük kareler optimal Φ (A: durum kestirimi, B: çıkış eşleme); 6 anahtarlama × S = 7…31 × paralel/kaskad; 4 giriş sınıfında eğitim, taze kümede ve basamakta test; ‖Φ‖–hata Pareto; float32, 18/24/32-bit kuantizasyon, 24-bit durum gürültüsü; sürekli α altında zincirleme eşleme | `results/e2_*.json`, `fig_e2_*.png` |
| **E3** | Hata terimlerinin izole doğrulaması; 72 spesifikasyonluk geliştirme ızgarası; 400 spesifikasyonluk mühürlü holdout (değerlendirmeden önce SHA-256 ile yazıldı) | `results/e3_*.json`, `fig_e3_*.png` |
| **E4** | Literal D/E özyinelemeleri ve dualite; bankadan A/B/D/E (5 profil × 3 giriş); E3 holdout tasarımlarında ters kararlılık; hot-swap Oustaloup'un en yakın tipi (own-type referansları); dört tipte VO gevşeme denklemi, O(K) ve O(n²) karşılaştırması | `results/e4_recursive_types.json`, `fig_e4_types.png` |
| **E5** | Bit-tam tamsayı modeli (örnek birimleri, mod başına durum ölçeklemesi, mantis+kaydırma katsayılar, P = 1024 derece tablosu); iki zarf (A/B, A/B/D/E); WS × WM taraması; kuantize DC tabanı; Verilog çekirdek, iverilog bit-tam paritesi, Verilator lint, Yosys xc7 tahmini; kart paketi | `results/e5_*.json`, `fig_e5_wordlength.png`, `rtl/` |
| **E6** | mBm sentezi: bileşim kuralları; GL ile yol karşılaştırması; üretecin n×n ağırlık matrisiyle tam varyans ve kovaryans (Monte Carlo'suz); yerel Hurst izleme (sabit/rampa/sinüs/basamak, A ve B); H sıçramasında A/B davranışı; maliyet; E5 çekirdekleriyle bit-tam üretim | `results/e6_mbm.json`, `fig_e6_*.png` |

**İstatistik ve tekrarlanabilirlik:** sabit tohumlar; tüm deneyler `python3 experiments/<e>.py` ile tek komutla üretiliyor; testler `pytest`. E3'te geçme/kalma için Clopper–Pearson alt sınırı kullanılacak (TCAS-I'deki yaklaşımla tutarlı).

---

## 6. Makale iskeleti (CSSP)

1. Introduction: VO tanımlarının çokluğu, pratik gerçeklemelerin tanım belirsizliği, katkılar
2. Preliminaries: A/B tipi tanımlar, difüzif gösterim, kapalı-form basamak yanıtları (B-tipi için kısmi integrasyon formülü)
3. Fixed-pole banks: CT kuadratür, kuyruk düzeltmeleri, α = 0 sürekliliği
4. Definition by structure: OS → A, IS → B (önermeler), gereklilik teoremi
5. Discrete-time exactness: Beta-integral gösterimi, ayrık banka, Tanım 2/3'ün kuadratür hatası dışında tam gerçeklenmesi; D/E tiplerinin cebirsel ters ile gerçeklenmesi, dualitenin korunması, ters kararlılık önermesi ve DC tabanı; VO diferansiyel denklem çözücüsü
6. Design rule: analitik K(ε, bant, α-aralığı)
7. Hardware: örnek birimlerinde bölücüsüz D/E, mod başına durum ölçeklemesi, D/E anahtarlama dinamik aralığı, kuantizasyona duyarlı DC tabanı, kelime uzunluğu seçimi, RTL paritesi, kaynaklar, kart ölçümleri
8. Application: gerçek zamanlı mBm sentezi (RL-mBm = A-tipi, B-tipi varyant; tamsayı bölme kuralı; H sıçramasında süreklilik farkı; O(K) akış maliyeti; sabit noktalı çekirdek)
9. Conclusion
Ekler: ispatlar, referans formüllerin GL ile doğrulanması

CSSP formatı: Springer `sn-jnl` şablonu; Data Availability ve Conflict of Interest beyanları.

---

## 7. Sonuçlar

### E1: CT, basamak girişi, kapalı-form referanslar (S = durum sayısı)

Anahtarlamadan sonraki bağıl RMS hata (A-tipine / B-tipine göre), S = 15 → 41 (geometrik kuyruk kapanışıyla yeniden koşturuldu):

| α₁ → α₂ | A–B farkı | FP-out (A) | FP-in (B) | Ou-par (A) | Ou-cas (A / B), S=41 |
|---|---|---|---|---|---|
| −0.3 → −0.7 | 0.52 | 1.0e-4 → 1.7e-4 | 1.0e-4 → 5.1e-5 | 0.12 → 0.042 | 0.16 / 0.33 |
| +0.3 → +0.7 | 0.65 | 2.1e-3 → 1.5e-5 | 4.2e-3 → 1.5e-4 | 0.14 → 0.053 | 1.6 / 1.7 |
| −0.5 → +0.5 | 0.81 | 1.1e-3 → 4.3e-5 | 5.1e-4 → 3.1e-5 | 0.23 → 0.085 | 4.6 / 1.6 |
| +0.5 → −0.5 | 1.35 | 9.8e-5 → 3.4e-5 | 9.4e-4 → 8.0e-6 | 0.25 → 0.080 | 0.24 / 0.87 |

(FP-out'ta S=15'te bazı değerlerin S=41'den küçük olması, sabit [1e-3, 1e5] ızgarasında kuyruk tabanına ulaşılmasından kaynaklanıyor. E3 kuralı ızgarayı ε'a göre seçiyor.)

- Anahtarlamadan **önce** (sabit derece) tüm yapıların hatası benzer (1e-3 ile 1e-4 arası). Fark tamamen anahtarlamadan, yani tanımsal etkiden geliyor.
- Kaskad Oustaloup'ta derece artınca hata **azalmıyor**. Paralel Oustaloup A-tipine yavaş yakınsıyor (kutup kayması, kutup aralığının sabit bir kesri olduğu için). Sabit kutuplu banka eşit durum sayısında 100–1000 kat daha doğru.
- **Bulgu (olumsuz, raporlanacak):** CT giriş-zamanlamalı banka, yumuşak α(t) ile *türevde* başarısız (bağıl hata ~12). Nedeni: 1/Ts'den hızlı modlar örneklenmiş α'nın her adımdaki sıçramasına türev gibi yanıt veriyor. Bu bulgu §3'teki ayrık-zaman formülasyonunu gerekçelendiriyor (E1b'de sorun ortadan kalkıyor).

### E1b: DT banka ile GL Tanım 2/3 (Ts = 1 ms, 4001 örnek; DFP: 32 mod + gecikme modu; Oustaloup: N = 15, 31 durum)

**Toplam hata** (GL referansına göre, bağıl RMS), 7 α profili × 3 giriş:
- DFP-out → Tanım 2: **2.5e-6 … 2.0e-3**. DFP-in → Tanım 3: **1.9e-6 … 1.6e-3**. Yumuşak α ile türev dahil, CT'deki sorun ortadan kalktı.

**Tanımsal hata** (her gerçeklemenin kendi dondurulmuş-derece LTI eşdeğerine göre; yaklaşım kalitesinden bağımsız), parçalı-sabit profiller:

| Gerçekleme | kendi A-tipine göre | kendi B-tipine göre |
|---|---|---|
| DFP-out | **0 (tam)** | = A–B farkı |
| DFP-in | = A–B farkı | **≤ 1e-14** (yuvarlama) |
| Ou-par | 4e-6 … 0.13 (girişe bağlı, en kötüsü basamakta) | 7e-3 … 1.0 |
| Ou-cas | 7e-3 … **3.0e+3** (−0.5 → +0.5 basamak) | 0.03 … 4.8e+2 |

Yorum: sabit kutuplu yapıda tanımsal hata tam sıfır. Hot-swap edilen Oustaloup'ta ise sıfır değil; kaskadda derece artışı da bunu gidermiyor. (Bir durum eşlemesiyle ne kadar giderilebildiği E2'de.)
Not: Oustaloup'un GL'ye göre *toplam* hatası gürültü/çoklu sinüs girişlerinde büyük çıkıyor (≈10). Bu tanımsal bir etki değil, CT tasarımın (bant 1e5 rad/s > Nyquist) ZOH ile ayrıklaştırılmasından kaynaklanan statik CT/DT uyumsuzluğu. Bu yüzden karşılaştırmada tanımsal hata metriği esas alınacak.

### E2: durum eşlemesi Oustaloup'u kurtarabilir mi?

Kurgu: Ts = 1 ms, anahtarlama nT = 2000'de, pencere L = 2000. Eğitim: 4 sınıf × 200 giriş (beyaz, parçalı-sabit, çoklu sinüs, Brown). Test: 4 sınıf × 150 taze giriş ve basamak. Φ, rcond taramasıyla kesilmiş en küçük kareler ile bulunuyor. "Sağlam" seçim, doğrulama hatası en iyinin 2 katı içinde kalan en küçük normlu Φ.
Değerler 6 anahtarlama üzerinden en kötü durum (dağılım içi / basamak):

| S | biçim | Φ = I (hot-swap) | LS Φ, float64 | sağlam Φ, float64 (‖Φ‖) | sağlam Φ, float32 | sağlam Φ, 24-bit | B-tipi: Φ = I → LS |
|---|---|---|---|---|---|---|---|
| 7 | paralel | 0.9 / 0.7 | 2e-2 / 3e-2 | 3e-2 / 5e-2 (3e4) | 3e-2 / 5e-2 | 3e-2 / 5e-2 | 1.0 → 1e-2 |
| 7 | kaskad | 4e2 / 1e4 | 2e-2 / 4e-2 | 2e-2 / 4e-2 (9e2) | 2e-2 / 4e-2 | 2e-2 / 3e1 | 2e2 → 1e-2 |
| 15 | paralel | 0.3 / 0.3 | 1e-4 / 2e-2 | 2e-4 / 4e-4 (5e4) | 2e-4 / 4e-4 | 1e-2 / 8e-3 | 1.0 → 7e-4 |
| 15 | kaskad | 4e2 / 1e4 | 1e-4 / 1e-3 | 3e-4 / 3e-4 (8e3) | 1e-3 / 0.8 | 0.6 / 4e2 | 2e2 → 2e-4 |
| 31 | paralel | 0.1 / 0.1 | 4e-8 / 5e-7 | 5e-8 / 2e-7 (5e3) | 2e-7 / 1e-5 | 4e-3 / 2e-3 | 1.0 → 6e-7 |
| 31 | kaskad | 4e2 / 1e4 | 4e-8 / 6e-7 | 9e-8 / 6e-7 (4e4) | 7e-3 / 0.3 | 2e1 / 8e2 | 2e2 → 5e-7 |

Sürekli α (yumuşak profil 41 seviyeli ızgarada, 80 geçiş, paralel form, sağlam eşleme zinciri), basamak girişi:
- türev, N=7: Φ=I 4.1e-2 → zincir 1.2e-4. N=15: 2.0e-2 → 1.0e-7
- integral, N=7: 1.4e-1 → 5.9e-6. N=15: 6.2e-2 → 4.9e-9
- sabit kutuplu banka: **0** (eşleme yok)
(İlk denemede doğrulama minimumuyla seçilen büyük normlu eşlemeler N=7'de zinciri hot-swap'tan bile kötü yapmıştı. Sağlam seçim bunu giderdi; makalede iki seçim de raporlanacak.)

**Sonuç:** Yaklaşık tanım tutarlılığı, Oustaloup'a yoğun ve çifte özel bir eşleme eklenerek float64'te elde edilebiliyor. Ancak maliyet O(S²)/geçiş, bellek O(P·S²) (P derece seviyesi). Ayrıca 24-bit sabit noktada 3–10 mertebe doğruluk kaybediliyor, kaskadda yöntem tamamen çöküyor. Sabit kutuplu banka aynı işi O(S) maliyetle, tam ve kuantizasyona dayanıklı biçimde yapıyor.
Uyarı: sabit nokta testi basit bir tek-ölçekli Q formatı. Satır başına ölçekleme (block floating point) daha iyi sonuç verebilir; makalede bu sınırlama olarak belirtilecek.

### E3: analitik tasarım kuralı

**Terim doğrulaması** (her terim izole; tahmini > 1e-10 olan noktalar): DT'de ölçüm/tahmin 0.49–1.05 (n=45), CT'de 0.99–1.01 (n=66). Model hiçbir terimde hatayı %5'ten fazla küçümsemiyor.

**Kural doğrulaması:**

| Küme | DT geçen | CT geçen | CP95 alt sınırı | elde/ε medyan (maks.) | K − K_min medyan (maks.) |
|---|---|---|---|---|---|
| Geliştirme (72) | 36/36 | 36/36 | %92.0 (her biri) | 0.39 / 0.42 (0.61 / 0.53) | 1 / 2 |
| **Mühürlü holdout (400)** | **200/200** | **200/200** | **%98.5** (her biri) | 0.41 / 0.50 (0.67 / 0.72) | 1 / 1 (3 / 3) |

Holdout spesifikasyonları: ε ∈ [1e-5, 1e-2], R ∈ [1e2, 1e5], bant 0.5–6 dekad, rastgele α-aralıkları ⊂ [−0.95, 0.95]. SHA-256 `ddc4fcf1…` ile değerlendirmeden önce mühürlendi.

**Gereken K, α ∈ [−0.9, 0.9]:**

| ε | DT: R = 1e3 / 1e4 / 1e5 | CT: 2 / 4 / 6 dekad |
|---|---|---|
| 1e-2 | 14 / 17 / 19 | 11 / 14 / 16 |
| 1e-3 | 21 / 24 / 27 | 18 / 22 / 26 |
| 1e-4 | 29 / 32 / 36 | 27 / 32 / 37 |
| 1e-5 | 38 / 42 / 46 | 38 / 44 / 50 |

Kaba ölçekleme: K ≈ ln(4/ε)·[ln R + ln(1/ε)/(2+α_min) + …]/π². Bellek uzunluğunun her dekadı ~3 mod, doğruluğun her dekadı ~8 mod ekliyor.

### E4: tek bankadan dört tip (A/B/D/E)

**P1, tanımlar:** Literal D/E özyinelemeleri, inv(W_A(−α)) ve inv(W_B(−α)) ile 1.4e-13 hassasiyetle aynı. Dual bileşimler (A∘D, D∘A, B∘E, E∘B) birim operatörü 1e-12 ile veriyor. Dual olmayanlarda (A∘A, B∘B, A∘B, B∘A, A∘E, B∘D, D∘E, D∘D) fark 1e-2 ile 2.4e3 arasında.

**P2, banka:** E3 kuralıyla tasarlandı (ε = 1e-5, |α| ≤ 0.95, K = 41). 5 profil × 3 giriş:

| Tip | literal GL'ye göre | kendi tipine göre (tanımsal) |
|---|---|---|
| A | 9.5e-8 … 6.9e-5 | ≤ 2.6e-14 |
| B | 3.1e-8 … 1.2e-5 | ≤ 1.0e-14 |
| D | 2.0e-8 … 6.5e-5 | ≤ 2.3e-14 |
| E | 2.2e-8 … 5.5e-5 | ≤ 2.8e-13 |

Banka içinde dualite (A∘D, B∘E): ≤ 2.0e-14.
Not: türevlerde yumuşak girişlerde çıkış düzeyindeki hata ağırlık düzeyindeki ε'u biraz aşabiliyor (en fazla 6.9e-5), çünkü Σg_r ≈ 0 iptali hatayı büyütüyor. Kuralın ölçütü ağırlık düzeyinde; makalede bu ayrım açıkça yazılacak.

**P3, ters kararlılık:** E3 holdout'undaki 200 DT tasarımında tüm derecelerde kararlı ters: tabanla **200/200**, tabansız 101/200. Uzun koşu örneği (ε = 1e-2, R = 1000, 0.95 dereceli D-tipi integral, 2e5 örnek beyaz gürültü): tabansız RMS **1.9e21**, tabanla 0.24.

**P4, hot-swap Oustaloup hangi tipi gerçekliyor?** 2 profil türü × 2 giriş × 4 durum:

| Gerçekleme | en yakın tip (8 vaka) | en yakın tipe uzaklık | own-D/E kurulamadı |
|---|---|---|---|
| DFP-out / DFP-in | A 8/8 / B 8/8 | ≤ 2e-14 | 0/8 |
| Ou-par, ω_h = 1e5 | A 8/8 | 5e-6 … 0.4 | 6/8 (üyeler minimum-fazlı değil) |
| Ou-par, ω_h = 1e3 | A 8/8 | 7e-4 … 0.3 | 0/8 |
| Ou-cas, ω_h = 1e5 | A 4, B 4 | 1.5e-2 … **1.3e3** | 6/8 |
| Ou-cas, ω_h = 1e3 | **A 2, B 2, D 2, E 2** | 9e-4 … 2.8 | 0/8 |

ZOH'lu Oustaloup integral üyelerinde bant Nyquist'i aştığında birim çember dışında, büyüklüğü 3 ile 41 arasında sıfırlar oluşuyor; bu yüzden ters ıraksıyor ve D/E kurulamıyor. ω_h ≤ ~Nyquist/3 olduğunda sorun kayboluyor.

**P5, VO gevşeme denklemi** T^α y + λy = u (Ts = 1 ms, n = 4000, K = 40):
- λ = 1: bankanın GL'ye göre hatası ≤ 1.7e-5. Tipler arası fark ise 0.40'a kadar (A–B), yani tip seçimi çözümü belirgin biçimde değiştiriyor.
- λ = 100: hata ≤ 4.9e-7, tipler arası fark ≤ 0.02 (λy baskın, tip etkisi kayboluyor).
- Süre (24 çözüm): banka 1.2 s (Python döngüsü, O(nK)), GL üçgensel çözümü 9.6 s (O(n²), C). Fark n ile büyüyor.

### E5: sabit nokta ve RTL

**Tasarım noktası:** R = 4000, ε = 1e-4, |α| ≤ 0.95 → K = 32 (+ gecikme modu). Derece ızgarası P = 1024 (Δα = 1.9e-3).

**Mimari kararlar:**
- **Örnek birimleri (Ts = 1):** g₀ = 1 olduğu için D/E terslemesi bölücüsüz, v = x − hist. Fiziksel ölçek tek bir Ts^(−α) kazancı (A ve E'de çıkışta, B ve D'de girişte).
- **Mod başına durum ölçeklemesi (2^G):** giriş zamanlamasında yavaş modların c·v artışları sinyal LSB'sinin çok altında kalıyor. Ölçeklemesiz ilk denemede B/E hatası 2e-2 ile 0.66 arasındaydı.
- **Kelime genişlikleri:** durum kelimesi = sinyal + 13 bit (log₂ n_max + 1). Katsayılar mantis + 7 bit kaydırma biçiminde.

**Dinamik aralık (çok önemli):** D/E'de integral ile türev dereceleri arasında anahtarlama, çıkışı dondurulmuş-derece l1 sınırının **820 katına** çıkarıyor (DC girişte 2.2e6, sınır 2696). Yeni derecedeki ters işlem, büyümüş bir geçmişe uygulanıyor; bu D-tipi tanımın kendi davranışı. Bu yüzden iki çalışma zarfı var:
- A/B: 14 tamsayı biti
- A/B/D/E: 24 tamsayı biti

**Kelime uzunluğu** (36 vaka, kabul ölçütü: GL'ye göre hata ≤ float hatası + 0.1ε):

| Zarf | En küçük yapılandırma (WS / durum / WM) | Not |
|---|---|---|
| A/B | **36 / 49 / 16** | A/B, 16-bit mantisle bile float düzeyinde |
| A/B/D/E | **48 / 61 / 25** | D/E 18-bit mantiste ~1e-3 tabanına takılıyor (terslemenin kötü koşulluluğu: türev bankasının düşük frekans kazancı ~R^(−α)) |

Ayrıca float bankanın kendi çıkış hatası D/E'de 6e-4'e kadar çıkıyor (ağırlık düzeyi ε = 1e-4). Kural ağırlık düzeyinde garanti veriyor; çıkış düzeyindeki bu büyüme makalede ayrıca belirtilecek.

**Kuantizasyon ve ters kararlılık:** Float katsayılar tabanlı olsa bile, kuantizasyondan sonra pozitif derece girişlerinde H_q(1) ≤ 0 çıkıyor:
- A/B yapılandırmasında 64/512 giriş
- A/B/D/E yapılandırmasında 51/512 giriş

En kötü girişte (α = 0.855) baskın ters kutup 1 + 1.9e-9 (E5c, tam rasyonel aritmetik; önceki özdeğer tahmini 2.5e-9 idi). e-katına çıkması 5.2e8 örnek alıyor, 1 MS/s'de ~520 s. A/B yapılandırmasında en kötü satır α = 0.931, kutup 1 + 4.8e-6. Kuantizasyona duyarlı taban (c_delay'i mantis LSB'si adımlarıyla artırarak H_q(1) ≥ H_float(1) yapmak) bunu 0/512'ye indiriyor. Doğruluk maliyeti yok.

**RTL** (`rtl/vo_bank_core.v`, zaman paylaşımlı, örnek başına 4K + 8 = 136 çevrim):

| Zarf | Yapılandırma | Örnek | Uyumsuzluk | LUT | FF | DSP48E1 | BRAM36 eşd. |
|---|---|---|---|---|---|---|---|
| A/B | WS36 / WST49 / WM16 | 31 744 | **0** | 4 171 | 1 882 | 11 | 22 |
| A/B/D/E | WS48 / WST61 / WM25 | 62 464 | **0** | 6 009 | 2 360 | 29 | 29.5 |

- Vektörler: sabit, parçalı, **her örnekte değişen** ve işaret değiştiren dereceler; tam ölçekli girişler; çalışma anında tip değişimi.
- Kaynaklar Yosys 0.33 `synth_xilinx -family xc7` tahmini. Vivado sonuçları ve Fmax farklı olabilir.
- Derece değişimi yalnızca bir ROM adresi: yeniden yükleme yok, ek çevrim yok.
- Karşılaştırma: E2'deki durum eşlemesi yaklaşımı yalnızca komşu dereceler için 2(P−1) yoğun 33×33 matris ister. Bu yaklaşık 56 Mbit; katsayı tablosu ise 0.78–1.08 Mbit, yani ~50–70 kat daha az.

**Açık / sınırlar:** Fmax ve kart ölçümleri yok (Vivado + kart gerekli, paket `rtl/README.md`'de). Boru hattısız durum makinesi; boru hattıyla örnek başına ~K + birkaç çevrime inilebilir. Sabit nokta tek ölçekli Q formatında, D/E için block-floating denenmedi.

### E6: gerçek zamanlı multifraksiyonel Brown hareketi

Banka E3 kuralıyla tasarlandı (ε = 1e-4, |α| ≤ 0.45, yani 0.05 ≤ H ≤ 0.95); n = 1024 / 4096 / 16384 için K = 22 / 24 / 26.

| Bölüm | Sonuç |
|---|---|
| P1 bileşim | A integratör önce, B integratör sonra: ≤ 9e-15. Ters sıralar: 0.1–1.3 |
| P2 yol (aynı gürültü) | GL'ye göre A ≤ 1.9e-6, B ≤ 2.4e-6 |
| P3 ikinci derece istatistik (n = 2048, deterministik) | varyans ≤ 3.1e-5, kovaryans (Frobenius) ≤ 1.7e-6 |
| P4 yerel Hurst (M = 400, n = 16384, pencere 1024, genişletme 4/8) | sabit H'de kestirici bias'ı +0.06 (H=0.2), 0.00 (0.5), −0.02 (0.8), std 0.06. Değişken H'de ortalamanın RMSE'si 0.014–0.036; A ve B aynı |
| P5 H sıçraması (0.3 → 0.8) | A-tipi (RL-mBm) varyansı 119 → 154 297'e sıçrıyor ve yol süreksiz (sıçrama anındaki artışın karesi, öncekinin 1.3e5 katı). B-tipi sürekli (oran 1.0). Kestirici sıçrama penceresinde A için geçici bir plato gösteriyor |
| P6 maliyet | Banka örnek başına 47–55 MAC (n'den bağımsız); GL ortalama n/2 MAC. Yol başına süre (Python): banka toplu 0.6 / 2.2 / 11.5 ms, GL 10 / 120 / 1060 ms. Tek yol Python döngüsünde banka 32 / 113 / 506 ms (yorumlayıcı yükü; donanımda örnek başına sabit 136 çevrim) |
| P7 sabit nokta (E5 çekirdekleri) | A/B çekirdeği (36/49/16): A 1.8e-5, **B 8.9e-4**. A/B/D/E çekirdeği (48/61/25): A 3.8e-6, B 1.2e-4 |

Yorum:
- Banka mBm'yi tanım düzeyinde tam üretiyor; kalan farklar kuadratür (~1e-6) ve kestiricinin kendi bias'ı.
- A ile B'nin farkı en çarpıcı biçimde H sıçramasında görünüyor. A-tipi (RL-mBm) bütün geçmişin çekirdeğini değiştirdiği için yol sıçrıyor; B-tipi sürekli kalıyor. Bu, uygulamada hangi tanımın seçileceğini doğrudan belirliyor (ör. süreklilik gerekiyorsa B).
- Donanım notu: A-tipinde akümülatör çekirdeğin önünde ve tam (tamsayı toplam), bu yüzden ucuz çekirdek yetiyor. B-tipinde akümülatör çekirdeğin arkasında ve çekirdeğin düşük frekans yuvarlama hatalarını biriktiriyor; bu da daha geniş bir çekirdek gerektiriyor.
- Önemli düzeltme: golden model artık girişleri Python tamsayısına çeviriyor. numpy int64 girişler geniş çarpımlarda sessizce taşabiliyordu; E5 sonuçları bundan etkilenmedi.

### E7: operatör normu sınırları (Teorem 5)

İki kural tasarımı (R = N = 1000, |α| ≤ 0.95): ε = 1e-3 (K = 22) ve ε = 1e-6 (K = 49). On bir derece dizisi için dört tipin gerçeklenen ve literal operatörleri yoğun 1000×1000 matris olarak kuruldu. Diziler: sabitler, anahtarlamalar, rastgele parçalı, her örnekte bağımsız, düzgün geçiş ve iki "kötü niyetli" dizi.

| Nicelik | ε = 1e-3 | ε = 1e-6 |
|---|---|---|
| A, B: ‖E‖_p / sınır (a), p = 1, ∞ | 0.28–1.00 | 0.45–1.00 |
| A, B: ‖E‖_2 / sınır (a) | 0.13–0.87 | 0.16–0.89 |
| A, B: (‖E‖/‖W‖)/ε_R, p = 1, ∞ | 0.04–0.39 | 0.03–0.45 |
| D, E integral: ‖E‖_∞ / sınır (c) | 0.23–0.31 | 0.006–0.23 |
| D, E: en büyük göreli ∞-hata / ε_R (tasarım) | 22 | 17 |

Yorum:
- A/B için sınırlar hiç aşılmadı. Sabit ve kötü niyetli dizilerde dört basamak doğrulukla tam olarak yakalandı.
- İleri tiplerde göreli operatör hatası ≤ ε_R. Bu, "çıkış düzeyinde kural" eksiğini ℓ1/ℓ∞ en kötü durum anlamında kapatıyor.
- Özyinelemeli integrallerde hata, ters çevrilen türevin koşul sayısıyla büyüyor; κ ≈ 2N^a/Γ(1+a), burada 71–668. Bu gerçek bir etki (DC kazancı küçük). Garanti için tasarım ε/κ ile yapılmalı.
- Adım yanıtından tek koşuluk a-posteriori sertifika, ölçülen hatanın 3–4 katı içinde.
- Türev D/E'de ölçülen hata ε_R düzeyinde kalıyor; sınır κ kadar ihtiyatlı.
- Holdout'taki 4294 türev derecesinin hepsinde ĝ₁ < 0. Bu, (c)'deki negatif olmama hipotezi.

### E9: tam monoton çekirdek aileleri (Teorem 9)

- Şerit sabiti L_d (GL ailesi): d = 0.8 / 1.2 / 1.4 / 1.5 için 2.0 / 7.2 / 31.7 / 175. Bu, (cos d)^(−1.95) davranışıyla uyumlu.
- Genel kuadratür sınırı, ölçülen en kötü trapez hatasının 1.9–3.7 katı. GL'ye özgü E_q ölçümle %1 içinde örtüşüyor.
- K ölçeklemesi: R = 1e2…1e6 ve ε = 1e-2…1e-8 aralığındaki 35 tasarım (K = 12…90), K ≈ 0.57 + 1.06 ln(1/ε) + 0.53 ln R + 0.106 ln(1/ε) ln(R/ε) ile 0.7 kutup içinde açıklanıyor. Çarpım katsayısı 0.106, teorideki 1/π² = 0.101'e çok yakın.
- Zamanla değişen dağılımlı derece: aynı banka (K = 39) karışım artıklarıyla çalıştırıldı. Çekirdek hatası en kötü bileşenin altında kaldı (≤ 2.6e-6); A/B göreli operatör hatası ≤ 1.8e-7; akış ile yoğun operatör farkı 3e-16.
- Sabit temperleme (λ = 0.01): kutuplar e^(−λ)θ_k oluyor; göreli hata temperlenmemiş bankayla aynı (3.877e-6).

---

## 8. Sonraki adımlar

1. Kart ölçümleri (`rtl/README.md`): bit-tam parite, Vivado kaynak ve Fmax, uzun koşu kararlılığı (isteğe bağlı: kartta gürültü üretecili mBm demosu)
2. Teoremin, ters-kararlılık önermesinin ve bileşim önermesinin tam ispatı; DT hata modelinin küçük-r terimi için kapalı form
3. Sistematik literatür taraması: Crossref + arXiv ile yapıldı (§2). Kalan: Scopus/WoS tekrarı
4. Makale taslağı: **başladı** (`paper/main.tex`, 29 sayfa, 6 şekil + TikZ şema, 8 tablo, 4 ek). Açık maddeler `paper/README.md`'de
4. E5: RTL ağırlık üretici, TCAS-I'deki W48 altyapısı yeniden kullanılarak ama yeni çekirdekle
5. E6 uygulaması (mBm). Alternatif: VO kesirli PID veya zamanla değişen spektral eğimli filtre
