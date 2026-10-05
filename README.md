# vofrac: Tanım-tutarlı değişken dereceli kesirli operatörler

CSSP (Circuits, Systems, and Signal Processing) makalesi için araştırma deposu.
Metodoloji, hipotezler, TCAS-I ile örtüşme koruması ve iş planı: [`docs/METODOLOJI.md`](docs/METODOLOJI.md).

**Ana fikir:** Kutupları dereceden bağımsız (sabit kutuplu) bir difüzif banka kurmak. Derece α(t)'yi **çıkış** ağırlıklarına koyunca A-tipi (Sierociuk Tanım 2), **giriş** ağırlıklarına koyunca B-tipi (Tanım 3) VO operatörü elde ediliyor. Kutupları α'ya bağlı yaklaşımlar (Oustaloup vb.) durum korunarak anahtarlandığında hiçbir tanımı tam gerçekleyemiyor.

## Yapı

```
vofrac/reference.py   A/B tipi kapalı-form basamak yanıtları, GL Tanım 2/3
vofrac/bank.py        FixedPoleBank (CT) ve DiscreteFixedPoleBank (DT, GL-tam)
vofrac/oustaloup.py   Durum korumalı anahtarlamalı Oustaloup (paralel / kaskad)
experiments/          E1 (CT, kapalı-form), E1b (DT, GL + tanımsal hata)
results/              JSON çıktıları, şekiller, loglar
tests/                pytest
```

## Çalıştırma

```bash
pip install -r requirements.txt
python3 -m pytest -q tests                      # ~1 s
python3 experiments/e1_definition_consistency.py  # ~50 s, results/e1_*.json + fig_e1_*.png
python3 experiments/e1b_discrete_gl.py            # ~40 s, results/e1b_discrete.json
```

## İlk sonuçlar (özet)

- Sabit kutuplu banka eşit durum sayısında Oustaloup'tan 100–1000 kat daha doğru (anahtarlama sonrası); sabit derecede ise hepsi benzer.
- DT bankanın tanımsal hatası tam 0 (çıkış) / ≤1e-14 (giriş). Oustaloup paralelde 1e-1'e, kaskadda 3e3'e kadar çıkıyor.
- Kuyruk düzeltmesi tek bir bankayla −0.9 ≤ α ≤ 0.9 aralığının tamamını, sıfır geçişi dahil ~1e-3 dB doğrulukla kapsıyor.
