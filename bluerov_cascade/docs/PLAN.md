# Makale planı: 6-DOF BlueROV2 Heavy için kaskad FOPID-(1+TFOID)

Bu çalışma, JESTECH makalemizin doğrudan devamıdır:

> H. Ersoy, B. Akgül, E. Akpınar, A. Kartci, U. E. Ayten, "Design and implementation of PI^λD^μ
> controller for ROVs: Thruster modeling, controller parameter optimization, and FPGA realization",
> *Engineering Science and Technology, an International Journal* 73 (2026) 102261,
> doi:10.1016/j.jestch.2025.102261.

Kontrolcü yapısı şu çalışmadan uyarlanıyor (orada iki bölgeli yük-frekans kontrolü):

> M. Nour, G. Magdy, F. Jurado, "A new fractional-order cascade controller structure for frequency
> regulation of interconnected renewable-dominant power systems", *Scientific Reports* 16 (2026) 30699,
> doi:10.1038/s41598-026-70937-0.

## 1. JESTECH makalesinden farkı

| | JESTECH (2026) | Bu çalışma |
|---|---|---|
| Eksen | Tek eksen (surge) | 6 DOF (x, y, z, φ, θ, ψ), eşleşmiş doğrusal olmayan model |
| Araç / itici | T200 deneyinden tanımlanmış 4. derece surge modeli | BlueROV2 Heavy, 8 × T200 (4 yatay vektörel + 4 dikey), aşırı tahrikli tahsis |
| Kontrolcü | PID, PI^λD^μ (tek döngü) | Kaskad FOPID-(1+TFOID), konum–hız biçiminde; 6 karşılaştırma yapısı |
| İtici modeli | Deneysel tanımlama | Üreticinin ölçümlerinden itki **ve elektrik gücü** (10–20 V); ölü bant, asimetri, doyum, gecikme |
| Optimizasyon | PSO, DEA | SOO (en yeni), GJO, GWO, PSO, DE, rastgele arama; **eşit değerlendirme bütçesi + aynalı kutu testi** |
| Maliyet | Çok senaryolu (basamak + bozucu + efor) | Çok senaryolu: 6 DOF ağırlıklı ITAE + gerçek veriden elektrik enerjisi |
| Testler | 4 test (gürültüsüz basamak, şiddetli gürültü, fırtına, çok seviyeli + fırtına) | Aynı 4 test 6 DOF'ta + parametre (±%20–50), batarya 12/20 V, motor gecikmesi, itici kaybı, Monte Carlo |
| Gerçekleme | FPGA | (Plan) FPGA/HIL veya gerçek BlueROV2 Heavy deneyi |

## 2. Katkılar (taslak)

1. **Kaskad FOPID-(1+TFOID)'in sualtı aracına ilk uygulaması.** LFC'deki "ikinci kademe girdisi
   = u₁ − Δf" yapısı, mekanik karşılığı olan "u₁ − ν" (hız geri beslemesi) ile konum–hız kaskadına
   çevriliyor; aşırı tahrikli BlueROV2 Heavy'nin altı serbestlik derecesinin hepsi kontrol ediliyor.
2. **İtici belirsizliğine karşı faz payı kısıtlı, çok senaryolu ayarlama.** T200'ün dinamiği iyi
   bilinmiyor (ölçülmüş transfer fonksiyonu yok; Blue Robotics motor dönerken 25–40 ms ESC gecikmesi
   tahmin ediyor, duruştan ~110 ms ölçülmüş). Bu yüzden her DOF'un doğrusallaştırılmış çevriminde
   (kesirli terimler simülatörün uyguladığı Oustaloup yaklaşımıyla) üç noktada kısıt var: nominal
   itici (τ_m = 0.1 s, 30 ms) PM ≥ 45°, yavaş köşe (0.2 s, 60 ms) ve hızlı köşe (0.05 s, 10 ms)
   PM ≥ 20°. Geliştirme sırasında görüldü ki kısıtsız ITAE ayarı PM ≈ 0–10° veren çevrimler üretiyor
   ve 1–2 örneklik ek gecikme bunları kararsız yapıyor; tek noktada (10 ms) PM ≥ 45° ile ayarlanmış
   çözümler de 30 ms'de 11–17°'ye, 0.2 s + 60 ms'de negatife düşüyordu (X5 belgeliyor). Sci. Rep.
   çalışmasının kendi belirttiği "formal kararlılık analizi yok" eksiğini kapatıyor; doğrusal
   analizin kararlılık sınırını simülatörle tutarlı öngördüğü testle doğrulandı.
3. **Veriye dayalı itici ve enerji modeli.** T200'ün 10–20 V itki ve güç eğrileri parametrik
   modele oturtuldu (16 V'ta itki 0.24 N RMS, güç 3.1 W RMS hata); maliyetteki efor terimi gerçek
   (gecikmeli) itkinin Joule cinsinden elektrik enerjisi; batarya voltajı değişimi gerçek eğrilerle.
4. **Konumsal yanlılığa karşı kontrollü optimizasyon karşılaştırması.** Tüm algoritmalar eşit
   fonksiyon değerlendirme sayısıyla (3030) karşılaştırılıyor (Sci. Rep. çalışmasında SOO iterasyon
   başına iki kat değerlendirme yapıyordu). Her algoritma, parametre kutusu aynalanmış
   (x → lb + ub − x) problemde de çalıştırılıyor: yanlılığı olmayan bir yöntemin sonucu değişmemeli.
   Kaydırılmış test fonksiyonlarıyla (X0) SOO/GJO/GWO'nun orijine yanlılığı gösteriliyor.
5. **Kapsamlı sınamalar:** JESTECH'in dört testi 6 DOF'ta, eğitim senaryolarından farklı bozucu
   gerçeklemeleriyle; ±kütle/ek kütle/sönüm, pozitif kaldırma, 12/20 V batarya, motor zaman sabiti,
   30 ms gecikme, bir yatay veya dikey iticinin kaybı ve 100 örnekli Monte Carlo.

## 3. SOO hakkında önemli not

"Optimizasyon makaledeki gibi yeni olsun" isteği için SOO (Stellar Oscillation Optimizer; Rodan,
Al-Tamimi, Al-Alnemer, Mirjalili, *Cluster Computing* 28 (2025) 362) uygulandı. Ancak:

- mealpy kütüphanesi SOO'yu `scientific_status="questionable"` olarak işaretliyor: makaledeki
  denklemler ile yazarın MATLAB kodu birbirini tutmuyor (Denk. 8'deki ortalama kodda farklı,
  algoritma 1'deki değerlendirme/güncelleme adımları kodda yok).
- Birinci hareketteki `r3·(x_osc1 + x_osc2)/2` ve `|r3·x_best|` terimleri çözümleri **koordinat
  orijinine** çekiyor. X0 deneyinde (D = 22): optimum orijindeyken SOO küre fonksiyonunda 1e-49,
  Rastrigin'de 0 buluyor; optimum kaydırılınca 6e3 ve 8e3'e çıkıyor. PSO ve DE kaydırmadan
  etkilenmiyor. GJO ve GWO da benzer biçimde yanlı (Kudela 2022, *Nat. Mach. Intell.* 4, 1238'in
  eleştirdiği durum).
- Aynı operatörleri x_best'e göre ölçülen koordinatlarda yazınca (BC-SOO, öteleme-değişmez) algoritma
  rastgele aramadan iyi olmuyor: SOO'nun arama gücü büyük ölçüde orijine çekilmeden geliyor.

Makalede SOO'yu "önerilen" algoritma olarak sunmak, hakem tarafından bu yanlılık fark edilirse riskli.
Seçenekler (karar senin):

- **(a) Önerilen yol:** SOO'yu en yeni algoritma olarak dahil edip adil protokolle (eşit bütçe,
  aynalı kutu, X0) değerlendirmek; ayarlayıcıyı sonuçlara göre seçmek. Optimizasyon katkısı
  "yanlılık-kontrollü karşılaştırma protokolü" olur.
- (b) SOO'yu Sci. Rep. gibi "önerilen" ayarlayıcı yapmak (yanlılık testleri yine eklenmeli).
- (c) Başka bir yeni algoritma seçmek (aynı protokolden geçirilmeli).

## 4. Model ve varsayımlar

- **Araç:** Fossen 6-DOF modeli; von Benzon vd. (2022, *JMSE* 10, 1898) BlueROV2 Heavy parametreleri
  (m = 13.5 kg, ek kütleler, doğrusal + karesel sönüm, r_b = [0, 0, −0.01] m, nötr kaldırma).
  Akıntı göreli hız üzerinden (C_A ve D), M_A ν̇_c ihmal edildi.
- **İticiler:** tahsis matrisi von Benzon vd. Denk. (14) ile aynı (testte doğrulandı); f_d = T⁺τ,
  sınır aşılınca vektör bütün olarak ölçekleniyor; nominal 16 V eğrisinin tersi (ölü bant telafili)
  ile PWM; gerçek eğri + birinci derece gecikme. Ölçümden itici komutuna 3 örnek (30 ms) gecikme.
  τ_m = 0.1 s ve 30 ms nominal değerler; tasarım [0.05, 0.2] s × [10, 60] ms aralığında kısıtlı,
  dayanıklılık testleri ve Monte Carlo da bu aralığı tarıyor (JESTECH'teki T200 transfer fonksiyonu
  güvenilir değil, kullanılmıyor).
- **Kontrolcü:** kontrol periyodu 10 ms; kesirli operatörler Oustaloup (N = 5, [1e-3, 1e2] rad/s),
  Tustin ile ayrıklaştırıldı; λ > 1 için tam integratör ayrılıyor. Çıkış ivme talebi, τ = M_nom·a.
  Öteleme (x, y, z) ve dönme (φ, θ, ψ) için iki ayrı parametre seti (önerilen yapı: 22 değişken).
- **Referans:** kritik sönümlü 2. derece referans modeli (ω = 1 rad/s), tüm yapılar için aynı.
- **Navigasyon hatası:** kontrolcü navigasyon filtresinin çıkışını görüyor: birinci derece
  Gauss–Markov (2 Hz bant), σ: konum 1 cm, derinlik 5 mm, yönelim 0.17–0.29°, hız 1 cm/s, açısal hız
  0.29°/s. T2 "şiddetli gürültü": 3 kat σ, 100 Hz beyaz + beyaz süreç gürültüsü (5 N, 0.3 N m).
- **Maliyet:** J = Σ_senaryo [Σ_d w_d ITAE_d + ρ·E] + K_pm Σ_a Σ_d max(0, PM*_a − PM_{a,d})/PM*_a,
  a ∈ {nominal (PM* = 45°), yavaş köşe (20°), hızlı köşe (20°)}, w = [1, 1, 1, 2, 2, 2],
  ρ = 2·10⁻⁴ 1/J, K_pm = 200; ıraksama cezası 1e4. Geçişi 300 rad/s'nin (Nyquist 314 rad/s)
  üstünde kalan çevrim PM = −180° sayılıyor.
- **Arama uzayı:** kazançlar log₁₀ ölçekte [10⁻², 50] (birkaç mertebeye yayılıyorlar; doğrusal
  [0, 50] kutusunda rastgele başlangıçların çoğu PM kısıtını ihlal ediyor ve tüm algoritmalar
  J ≈ 100'de takılıyordu), integral dereceleri [0, 1.5], türev dereceleri [0, 1] (gürültülü ölçümde
  μ > 1 gerçekçi değil), eğim üssü n ∈ [1, 10].

## 5. Deneyler

| | Betik | İçerik |
|---|---|---|
| X0 | `experiments/x0_center_bias.py` | Kaydırılmış küre/Rastrigin/Rosenbrock/Ackley, D = 22, 15 koşu |
| X1 | `experiments/x1_optimizers.py` | Önerilen yapı; 7 yöntem × {düz, aynalı} × 10 koşu + SOO eşit-iterasyon |
| X2 | `experiments/x2_controllers.py` | 7 yapı × {DE, PSO} × 10 koşu (SOO X1'de) |
| X3 | `experiments/x3_evaluate.py` | En iyi ayarlar: T1–T4, 30 dayanıklılık varyantı, 100 Monte Carlo |
| X4 | `experiments/x4_margins.py` | Üç itici noktasında DOF başına PM, geçiş frekansı, gecikme payı |
| X5 | `experiments/x5_unconstrained.py` | Gecikmesiz/kısıtsız ITAE ayarının marjları ve gecikmeye duyarlılığı |
| — | `experiments/summarize.py` | Tablolar (medyan, IQR, Mann–Whitney p) |

## 6. Senden gerekenler

1. **JESTECH makalesinin PDF'i** (Elsevier tam metni buradan indirilemiyor): PSO/DEA ayarları,
   maliyet ağırlıkları ve dört testin tanımları için. T200 transfer fonksiyonu güvenilir olmadığı için
   kullanılmayacak; itici dinamiği belirsizlik aralığıyla ele alınıyor.
2. SOO çerçevesi kararı (Bölüm 3).
3. Hedef dergi (JESTECH, *Ocean Engineering*, *ISA Transactions*, *Fractal and Fractional*, ...).
4. Laboratuvarda BlueROV2 Heavy varsa gerçek deney / HIL imkânı (en güçlü katkı olur).

## 7. Örtüşme koruması

- JESTECH'ten metin, şekil, tablo kopyalanmayacak; tanımlanmış model kullanılırsa atıfla.
- Sci. Rep. makalesinin yapısı atıfla kullanılıyor; denklemler kendi gösterimimizle yazılacak.
- vofrac (CSSP) çalışmasının sabit kutuplu bankası burada kullanılmıyor (Oustaloup kullanılıyor),
  bu yüzden iki makale arasında yöntem örtüşmesi yok.
