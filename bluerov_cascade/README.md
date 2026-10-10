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
experiments/         fetch_t200 (veri + uydurma), X0 (yanlılık), X1 (ayarlayıcılar), X2 (yapılar), X3 (testler)
results/             JSON çıktıları, loglar, iz kayıtları
figs/                Şekiller (make_figures.py)
tests/               pytest
```

## Çalıştırma

```bash
pip install -r ../requirements.txt numba openpyxl
python3 -m pytest -q tests                        # ~10 s
python3 -I experiments/fetch_t200.py              # T200 verisi (SHA-256 kontrollü) ve katsayılar; depoda veri yok
python3 -I experiments/x0_center_bias.py          # ~3 dk
python3 -I experiments/x1_optimizers.py           # ~60 dk (4 çekirdek)
python3 -I experiments/x2_controllers.py          # ~45 dk
python3 -I experiments/x3_evaluate.py             # ~2 dk
python3 -I experiments/summarize.py               # tablolar, results/summary.json
python3 -I experiments/make_figures.py            # figs/
```

## Sonuçlar (özet)

Bkz. [`docs/PLAN.md`](docs/PLAN.md) ve `results/summary.json`; sonuçlar aşağıda güncelleniyor.
