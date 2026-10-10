# bluerov_cascade: BlueROV2 Heavy için 6-DOF kaskad FOPID-(1+TFOID)

JESTECH makalemizin (Ersoy vd., *Eng. Sci. Technol. Int. J.* 73 (2026) 102261; tek eksen surge,
PI^λD^μ, PSO/DEA, FPGA) devamı olan yeni makale için araştırma klasörü. Nour, Magdy ve Jurado'nun
(*Sci. Rep.* 16 (2026) 30699) yük-frekans kontrolü için önerdiği kaskad FOPID-(1+TFOID) yapısı,
konum–hız kaskadı biçiminde BlueROV2 Heavy'nin altı serbestlik derecesine uygulanıyor; ayarlama için
en yeni algoritma SOO ve diğerleri, konumsal yanlılığı kontrol eden bir protokolle karşılaştırılıyor.

Makale planı, katkılar, varsayımlar ve açık sorular: [`docs/PLAN.md`](docs/PLAN.md).

## Yapı

```
rovc/params.py       BlueROV2 Heavy parametreleri (von Benzon vd. 2022), itici yerleşimi, tahsis matrisi
rovc/thruster.py     T200 itki ve elektrik gücü modeli (üretici ölçümlerinden, 10–20 V)
rovc/fractional.py   Oustaloup yaklaşımı, Tustin ayrıklaştırma
rovc/controllers.py  7 yapı: FOPID-(1+TFOID) (önerilen), FOPID, PID, P-PID, PI-(1+FOPID), FOPID-FOPI, FOPI-FOPD
rovc/sim.py          6-DOF Fossen modeli + 8 itici + kontrolcü, numba ile paralel toplu simülasyon
rovc/scenarios.py    Eğitim ve test senaryoları (T1–T4), dalga/akıntı, sensör gürültüsü, dayanıklılık varyantları
rovc/objective.py    Çok senaryolu maliyet: ağırlıklı ITAE + elektrik enerjisi; aynalı kutu seçeneği
rovc/optim.py        SOO, BC-SOO, PSO, DE, GWO, GJO, rastgele arama; eşit değerlendirme bütçesi
rovc/margins.py      Doğrusallaştırılmış DOF çevrimlerinin faz/gecikme payları (Oustaloup veya tam)
experiments/         fetch_t200, X0 (yanlılık), X1 (ayarlayıcılar), X2 (yapılar), X3 (testler), X4 (marjlar),
                     X5 (kısıtsız ayar), summarize, make_figures, make_tables
matlab/              T200 yeniden tanımlama betiği (System Identification Toolbox)
paper/               Makale taslağı (elsarticle), tablolar results/'tan üretiliyor
results/             JSON çıktıları, loglar, iz kayıtları
figs/                Şekiller (make_figures.py)
tests/               pytest
```

## Çalıştırma

```bash
pip install -r ../requirements.txt numba openpyxl
python3 -m pytest -q tests                        # ~10 s (17 test)
python3 -I experiments/fetch_t200.py              # T200 verisi (SHA-256 kontrollü) ve katsayılar; depoda veri yok
python3 -I experiments/x0_center_bias.py          # ~3 dk
python3 -I experiments/x1_optimizers.py           # ~90 dk (4 çekirdek)
python3 -I experiments/x2_controllers.py          # ~80 dk
python3 -I experiments/x3_evaluate.py             # ~1 dk
python3 -I experiments/x4_margins.py              # saniyeler
python3 -I experiments/x5_unconstrained.py        # ~3 dk
python3 -I experiments/x2b_budget.py              # ~2.5 sa, nominal ayar, 10 030 değerlendirme
X2R_STRUCTURES=7 python3 -I experiments/x2r_robust.py  # ~3.5 sa, sağlam ayar
python3 -I experiments/x3_evaluate.py x2r_robust.json x3r && python3 -I experiments/x4_margins.py x2r_robust.json x4r
python3 -I experiments/x6_tradeoff.py             # ~7 dk, maliyet–dayanıklılık
python3 -I experiments/summarize.py               # tablolar, results/summary.json
python3 -I experiments/make_figures.py            # figs/
python3 -I experiments/make_tables.py             # paper/tables/
cd paper && latexmk -pdf main.tex                 # paper/main.pdf
```

## Sonuçlar (özet)

Model: 6-DOF BlueROV2 Heavy, 8 × T200 (üretici eğrileri), 30 ms komut gecikmesi; ayarlama: 6-DOF ağırlıklı
ITAE + enerji, her DOF çevriminde üç itici noktasında faz payı kısıtı (nominal ≥ 45°, köşeler ≥ 20°).

- **X0 (konumsal yanlılık):** optimum orijindeyken SOO küre fonksiyonunda 1e-49, Rastrigin/Rosenbrock'ta 0
  buluyor; optimum kaydırılınca 6e3 / 8e3 / 4e3. GJO ve GWO da yanlı; PSO ve DE değişmiyor. Orijine
  bağımlılığı kaldırılan SOO (BC-SOO) rastgele arama düzeyinde.
- **X1 (ayarlayıcılar, önerilen yapı, 10 koşu, 3030 değerlendirme):** PSO medyan J 40.0 (aynalı kutuda
  40.4, p = 1.0); DE 67.0; GWO 68.4; SOO 85.0 (PSO'ya karşı p = 0.002), iki kat bütçeyle 60.7; GJO 122
  (aynalı kutuda 208, p = 0.002); BC-SOO ve rastgele arama 330–400.
- **X2 / X2b (nominal ayar, iki bütçe):** 3030 değerlendirmede P-PID en iyi nominal maliyeti buluyor (33.4;
  önerilen 35.8). 10 030 değerlendirmede kesirli kaskadlar öne geçiyor (PI-(1+FOPID) 29.7, önerilen 31.5;
  medyan önerilen 36.9, P-PID 65.0) — fark arama bütçesinden.
- **X6 (aşırı ayarlama):** 120 nominal koşunun hepsinde düşük eğitim maliyeti daha çok Monte Carlo ıraksaması
  demek (Spearman: P-PID −0.92, önerilen −0.63, PI-(1+FOPID) −0.45, FOPI-FOPD −0.44). Önerilen yapının
  en iyi nominal ayarı 100 örnekte 14 kez ıraksıyor. Dayanıklılık maliyete girmeli.
- **X2r / X3r (sağlam ayar: eğitime şiddetli gürültü + zayıf itici köşesi):** 40 kaskad ayarının hiçbiri
  ıraksamıyor. Önerilen yapı medyan eğitim maliyetinde en iyi (80.4; P-PID 125.3, p = 0.026;
  PI-(1+FOPID) 88.0, p = 0.47). En iyi ayarıyla T4'te en düşük hata (132.8; P-PID 203.0, −%35), en düşük
  MC medyanı ve p90, şiddetli gürültüde P-PID'den 3 kat az hata. 10 koşunun hepsinde: T4 171.5 / 345.2
  (p = 0.021), T2 14.2 / 33.7 (p = 0.003).
- **Dayanıklılık (sağlam ayar):** gövde parametreleri ≤ %5, 12 V batarya %19–37, yavaş itici + 60 ms
  %3–11. Yatay itici kaybı tahsise bildirilmezse kaskadlar ıraksıyor; bildirilip yeniden tahsis edilince
  önerilen yapı yalnızca %1–3 (P-PID %5–11).
- **X4r (marjlar):** önerilen yapı nominalde PM 45.0–52.3°, 43–60 ms ek gecikme payı; yavaş köşede 20.2°.
- **X5 (kısıtsız ayar):** gecikmesiz ve kısıtsız ITAE ayarı PM 3.8–24.7°; T4 maliyeti 30 ms gecikmede
  1.8–5.6 kat, 60 ms'de 4–16 kat artıyor. Sağlam ve kısıtlı tasarım 0 → 60 ms'de 133.5 → 138.1.

Makale taslağı: `paper/main.pdf` (sayılar `experiments/make_tables.py` ile JSON'lardan üretiliyor).
T200 yeniden tanımlama: `matlab/` (MATLAB Student'ta çalıştırılacak).
