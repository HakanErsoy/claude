# IEEE TSP sürümü

Bu klasör makalenin IEEE Transactions on Signal Processing sürümünü içeriyor. Signal Processing (Elsevier) sürümü `../paper/` altında.

İki sürümün metni ortak:

- ana metin `../paper/body.tex`,
- ek materyal `../paper/supp_body.tex`,
- makrolar `../paper/macros.tex`,
- ayrı parçalar `../paper/parts/`.

Bu klasördeki dosyalar yalnızca sarmalayıcı. TSP'ye özgü kısımlar şunlar:

- ön kısım (başlık, yazarlar, özet, IEEE anahtar kelimeleri),
- IEEEtran biçimi,
- `\spfalse`.

Şekiller (`../paper/figs/`), kaynakça (`../paper/refs.bib`) ve sonuç dosyaları da ortak. Ayrıntılar `../paper/README.md` içinde.

| Dosya | İçerik |
|---|---|
| `main.tex` | Ana metin, IEEEtran journal, **11 sayfa** (kaynaklar ve ekler dahil). TSP sınırı ilk gönderimde 13 çift sütun sayfa (SPS yayın SSS'si, 2026-10-09'da kontrol edildi); revizyonda 16 |
| `supplement.tex` | Ek materyal, 11 sayfa: sürekli zaman bankası ve sonuçları, durum eşlemeleri, hot-swap tipi, tek bankadan dört tip, sabit nokta ve kart ölçümleri, mBm, iki türetme. Ana metne `xr` ile `M-` önekli referans veriyor |
| `IEEEtran.cls`, `IEEEtran.bst` | Resmî IEEEtran v1.8b (CTAN, 2015-08-26; değiştirilmedi). SHA-256: cls `da751920…3bd7`, bst `314f0ece…5f` |
| `Makefile` | `make`: şekiller (`../paper` üzerinden), `main.pdf`, `supplement.pdf` |

## SP sürümünden farklar

İçerik iki sürümde aynı; yalnızca yerleşim farklı.

**TSP ana metninde olup SP'de ek materyalde olanlar:**

- ispatlar (TSP'de Ek A–D),
- ilgili çalışmalar tablosu,
- tasarım kuralı ve holdout şekli,
- sıçramalı izleme şekli,
- pil verisinde başka gerçeklemeler tablosu,
- sabit nokta ve kart ölçümlerinin uzun özeti.

**SP'de kısaltılanlar:** bazı kaynak listeleri.

**İki sürümde de ek materyalde olanlar:**

- sürekli zaman bankası ve hata terimleri,
- sürekli zaman anahtarlama sonuçları,
- durum eşlemeleri,
- hot-swap tipi,
- dört tip ve gevşeme denklemleri,
- sabit nokta ayrıntıları ve RTL tablosu,
- mBm,
- iki türetme.

## Gönderimden önce

1. Yazarlar ve kurumlar (`\author`, `\thanks`), finansman.
2. TSP yazar talimatlarının güncel hali (sayfa sınırı, ek materyal kuralları, özet uzunluğu) dergi sayfasından son kez kontrol edilmeli.
3. Önceki makalenin (AEÜ'de incelemede) kapak mektubunda belirtilmesi; bu sürüm o çalışmadan hiçbir ölçüm, şekil ya da metin kullanmıyor.
