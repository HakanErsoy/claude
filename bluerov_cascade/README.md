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
- **X2 (yapılar):** nominal eğitim maliyetinde en iyi tamsayı P-PID kaskadı (en iyi 33.4, medyan 36.2);
  önerilen FOPID-(1+TFOID) en iyi 35.8, medyan 40.0. Tek döngülü FOPID/PID ve FOPID-FOPI faz payı
  kısıtını yararlı bant genişliğiyle sağlayamıyor (J 300–640).
- **X3 (testler, en iyi ayarlar):** önerilen yapı T4'te (çok seviyeli + fırtına) en düşük hata (128.8; P-PID
  152.8), şiddetli gürültüde (T2) P-PID'den 6.5 kat daha az hata, 100 Monte Carlo örneğinde **hiç
  ıraksama yok** (P-PID 8, PI-(1+FOPID) 12, FOPI-FOPD 1) ve en düşük p90. P-PID yalnızca T3'te %10 önde.
  Yatay itici kaybı tahsise bildirilmezse tüm kaskadlar ıraksıyor; bildirilip 7 iticiye yeniden tahsis
  edilince önerilen yapının maliyeti yalnızca %10–13 artıyor.
- **X4 (marjlar):** önerilen yapı nominalde PM 45.1–52.1°, 40–67 ms ek gecikme payı; yavaş köşede 20.0°.
- **X5 (kısıtsız ayar):** gecikmesiz ve kısıtsız ITAE ayarı PM 3.8–24.7° veriyor; T4 maliyeti 30 ms
  gecikmede 1.8–5.6 kat, 60 ms'de 4–16 kat artıyor. Kısıtlı tasarım 0 → 60 ms'de 128.6 → 135.3.

Makale taslağı: `paper/main.pdf` (sayılar `experiments/make_tables.py` ile JSON'lardan üretiliyor).
T200 yeniden tanımlama: `matlab/` (MATLAB Student'ta çalıştırılacak).
