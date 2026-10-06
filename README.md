# vofrac: Tanım-tutarlı değişken dereceli kesirli operatörler

CSSP (Circuits, Systems, and Signal Processing) makalesi için araştırma deposu.
Metodoloji, hipotezler, TCAS-I ile örtüşme koruması ve iş planı: [`docs/METODOLOJI.md`](docs/METODOLOJI.md).

**Ana fikir:** Kutupları dereceden bağımsız (sabit kutuplu) bir difüzif banka kurmak. Derece α(t)'yi **çıkış** ağırlıklarına koyunca A-tipi (Sierociuk Tanım 2), **giriş** ağırlıklarına koyunca B-tipi (Tanım 3) VO operatörü elde ediliyor. Kutupları α'ya bağlı yaklaşımlar (Oustaloup vb.) durum korunarak anahtarlandığında hiçbir tanımı tam gerçekleyemiyor.

## Yapı

```
vofrac/reference.py   A/B tipi kapalı-form basamak yanıtları, GL Tanım 2/3
vofrac/bank.py        FixedPoleBank (CT) ve DiscreteFixedPoleBank (DT, GL-tam)
vofrac/oustaloup.py   Durum korumalı anahtarlamalı Oustaloup (paralel / kaskad)
vofrac/statemap.py    En küçük kareler optimal durum eşlemeleri (E2)
vofrac/design.py      Analitik hata modeli ve tasarım kuralı, CT ve DT (E3)
vofrac/types.py       Herhangi bir LTI ailesi için kendi A/B/D/E tipi referansları (E4)
vofrac/fixedpoint.py  Bit-tam sabit noktalı golden model, ROM dışa aktarımı (E5)
vofrac/mbm.py         Multifraksiyonel Brown hareketi üreteci, tam varyans, yerel Hurst kestiricisi (E6)
rtl/                  Verilog çekirdek, testbench, kart test paketi (E5), bkz. rtl/README.md
experiments/          E1 (CT), E1b (DT, GL + tanımsal hata), E2 (durum eşlemesi), E3 (tasarım kuralı), E4 (D/E tipleri), E5 (sabit nokta, RTL), E6 (mBm)
results/              JSON çıktıları, şekiller, loglar
tests/                pytest
```

## Çalıştırma

```bash
pip install -r requirements.txt
python3 -m pytest -q tests                      # ~1 s
python3 experiments/e1_definition_consistency.py  # ~50 s, results/e1_*.json + fig_e1_*.png
python3 experiments/e1b_discrete_gl.py            # ~40 s, results/e1b_discrete.json
python3 experiments/e2_state_map.py               # ~15 dk, results/e2_*.json + fig_e2_*.png
python3 experiments/e3_design_rule.py             # ~30 s, results/e3_*.json + fig_e3_*.png
python3 experiments/e4_recursive_types.py         # ~1 dk, results/e4_*.json + fig_e4_types.png
python3 experiments/e5_fixed_point.py             # ~2 dk, results/e5_fixed_point.json + fig_e5_wordlength.png
python3 experiments/e5_rtl_parity.py              # ~4 dk, iverilog + verilator + yosys gerekli
python3 experiments/e6_mbm.py                     # ~1 dk, results/e6_mbm.json + fig_e6_*.png (E5 sonuçlarını kullanır)
```

## Sonuçlar (özet)

- **E1/E1b:** Sabit kutuplu banka eşit durum sayısında Oustaloup'tan 100–1000 kat daha doğru (anahtarlama sonrası); sabit derecede ise hepsi benzer. DT bankanın tanımsal hatası tam 0 (çıkış) / ≤1e-14 (giriş). Hot-swap edilen Oustaloup'ta paralelde 1e-1'e, kaskadda 3e3'e kadar çıkıyor.
- **E2:** Yoğun, en küçük kareler optimal bir durum eşlemesi Oustaloup'un tanımsal hatasını float64'te 1e-8'e kadar indirebiliyor. Ama her derece çifti için S×S matris istiyor, girdi istatistiğine bağlı ve 24-bit sabit noktada 3–10 mertebe doğruluk kaybediyor (kaskadda tamamen çöküyor). Sabit kutuplu banka eşleme gerektirmiyor.
- **E3:** Regresyonsuz analitik kural, mühürlü 400 spesifikasyonun hepsini karşıladı (CP95 alt sınırı %98.5, ihtiyat payı 1.4–3 kat, K − K_min ≤ 3).
- **E4:** D^α = (A^{−α})⁻¹ ve E^α = (B^{−α})⁻¹ dualitesiyle tek banka dört tipin hepsini O(K) maliyetle gerçekliyor (literal GL'ye göre ≤6.5e-5, tanımsal hata ≤3e-13, dualite ≤2e-14). DC tabanı tüm terslerin kararlı olmasını garanti ediyor (tabansız holdout tasarımlarının yarısında ters kararsız). Hot-swap edilen kaskad Oustaloup'un en yakın tipi ise girişe göre A/B/D/E arasında değişiyor.
- **E5:** Sabit noktalı Verilog çekirdek, golden modelle bit-tam eşleşiyor (94 208 örnek, 0 uyumsuzluk); derece ve tip her örnekte değişebiliyor; örnek başına 136 çevrim. En küçük yapılandırmalar: A/B için 36/49/16 bit, A/B/D/E için 48/61/25 bit (sinyal / durum / mantis). Yosys xc7 tahmini 4–6 bin LUT, 11–29 DSP. Kuantizasyonun bozduğu ters kararlılık, kuantizasyona duyarlı DC tabanıyla geri kazanılıyor. Kart ölçümleri bekliyor.
- **E6:** Tek banka, 1/2 − H derecesinde ve tam tamsayı bölmeyle (A: integratör önce, B: sonra) 0 < H < 1 için RL-mBm'yi (A-tipi) ve B-tipi varyantını örnek başına ~50 MAC ile akış halinde üretiyor. Yollar GL'ye 1e-6, varyans ve kovaryans tam formüle ≤3e-5 yakın; yerel Hurst kestirimi H(t)'yi izliyor. H sıçramasında A-tipi yol sıçrıyor, B-tipi sürekli kalıyor. E5 çekirdeğiyle bit-tam üretimde A-tipi hata 1.8e-5.
