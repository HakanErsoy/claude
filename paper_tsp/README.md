# IEEE TSP sürümü

Bu klasör makalenin IEEE Transactions on Signal Processing sürümünü içeriyor. Tam metinli Signal Processing (Elsevier) sürümü `../paper/` altında; iki sürüm aynı sonuç dosyalarını, şekilleri (`../paper/figs/`) ve kaynakçayı (`../paper/refs.bib`) kullanıyor.

| Dosya | İçerik |
|---|---|
| `main.tex` | Ana metin, IEEEtran journal, **11 sayfa** (kaynaklar ve ekler dahil). TSP sınırı ilk gönderimde 13 çift sütun sayfa (SPS yayın SSS'si, 2026-10-09'da kontrol edildi); revizyonda 16 |
| `supplement.tex` | Ek materyal, 11 sayfa: sürekli zaman bankası ve sonuçları, durum eşlemeleri, hot-swap tipi, tek bankadan dört tip, sabit nokta ve kart ölçümleri, mBm, iki türetme. Ana metne `xr` ile `M-` önekli referans veriyor |
| `IEEEtran.cls`, `IEEEtran.bst` | Resmî IEEEtran v1.8b (CTAN, 2015-08-26; değiştirilmedi). SHA-256: cls `da751920…3bd7`, bst `314f0ece…5f` |
| `Makefile` | `make`: şekiller (`../paper` üzerinden), `main.pdf`, `supplement.pdf` |

## SP sürümünden farklar

- Ana metin: teori (gereklilik, yapı ⇔ tanım, operatör normu, CM ailesi), tasarım kuralı ve kararlılık, sayısal sonuçlar (tanım tutarlılığı, mühürlü holdout, operatör normu, maliyet–doğruluk), derece izleme (Bayesçi CRB dahil), pil verisi, sabit nokta ve kart ölçümlerinin özeti. İspatlar ekte (A–D).
- Ek materyale taşınanlar: sürekli zaman bankası ve hata terimleri, sürekli zaman anahtarlama sonuçları, durum eşlemeleri, dört tip ve gevşeme denklemleri, sabit nokta ayrıntıları ve RTL tablosu, mBm.
- Kısaltılanlar: ilgili çalışmalar (metin kısaldı, tablo aynı), CM örnekleri, tasarım kuralının ayrıntıları.

## Gönderimden önce

1. Yazarlar ve kurumlar (`\author`, `\thanks`), finansman.
2. TSP yazar talimatlarının güncel hali (sayfa sınırı, ek materyal kuralları, özet uzunluğu) dergi sayfasından son kez kontrol edilmeli.
3. Önceki makalenin (AEÜ'de incelemede) kapak mektubunda belirtilmesi; bu sürüm o çalışmadan hiçbir ölçüm, şekil ya da metin kullanmıyor.
