# Literatür taraması: protokol

Tarih: 2026-10-06. Amaç: CSSP makalesinin "ilgili çalışmalar" bölümünü ve yenilik iddialarını sistematik ve denetlenebilir bir taramaya dayandırmak.

## Araştırma soruları

| # | Soru |
|---|---|
| RQ1 | Değişken dereceli (VO) operatörlerin hangi gerçeklemeleri var (analog, dijital filtre, FPGA, ayarlanabilir dereceli eleman, rasyonel/durum uzayı) ve hangi VO tanımını gerçekliyorlar? |
| RQ2 | Bir gerçeklemenin hangi tanımı gerçeklediğini (anahtarlama şemaları, dualite, başlangıç koşulları) inceleyen çalışmalar hangileri? |
| RQ3 | Dereceden bağımsız düğüm/kutup kullanan yaklaşımlar (sabit kutup, üstel toplam, çekirdek sıkıştırma, difüzif/sonsuz durum gösterimi) VO operatörlerde nasıl kullanılmış? |
| RQ4 | Derecenin her örnekte değiştiği donanım gerçeklemeleri var mı? |
| RQ5 | Operatör düzeyinde VO yaklaşımları (GL tipi, özyinelemeli, seri açılımı) |
| RQ6 | Multifraksiyonel süreçler: farklı derece belleğine sahip tanımlar ve sentez yöntemleri |

## Kaynaklar

| Kaynak | Durum |
|---|---|
| Crossref (`api.crossref.org/works`, `query.bibliographic`) | Kullanıldı. Dergi, bildiri ve kitap bölümü türleri; 2000 ve sonrası; sorgu başına alaka sırasına göre ilk 100 kayıt |
| arXiv (`export.arxiv.org/api/query`) | Kullanıldı. Boole sorguları; sorgu başına ilk 100 kayıt |
| OpenAlex | Kullanılamadı: ortamın IP'sinin günlük ücretsiz kotası dolmuştu (429) |
| Semantic Scholar | Kullanılamadı: sürekli 429 |
| Scopus, Web of Science | Bu ortamdan erişim yok. **Kurumsal erişimle aynı dizgelerle tekrarlanmalı** (aşağıda) |
| Web araması ve tam metin | Kartopu adımında ve şüpheli kayıtlarda; açık erişim PDF'ler `pdftotext` ile okundu |

## Sorgular

Crossref sorguları (C01–C24) ve arXiv sorguları (A01–A06) `search.py` içinde sabit; kayıt sayıları `search_log.csv` dosyasında. Konu grupları:
- VO gerçekleme ve devreler (C01–C07, C17–C19, C24)
- tanımlar, anahtarlama ve dualite (C08–C10)
- sabit kutup, SOE ve difüzif yöntemler (C12–C16)
- FPGA (C04, C05)
- mBm (C20–C22)

**Scopus/WoS için önerilen dizge:**

```
TITLE-ABS-KEY( ("variable order" OR "variable-order" OR "time-varying order" OR "variable fractional order")
  AND fractional
  AND (realization OR realisation OR implementation OR circuit OR analog OR FPGA OR "digital filter"
       OR approximation OR "switching scheme" OR duality) )
AND PUBYEAR > 2009
```

Ek dizgeler:

```
TITLE-ABS-KEY( fractional AND ("fixed pole" OR "sum-of-exponentials" OR "exponential sum"
  OR "kernel compression" OR "diffusive representation") AND ("variable order" OR "variable-order") )

TITLE-ABS-KEY( "multifractional Brownian motion" AND (simulation OR synthesis OR generation OR "variable order") )
```

## Eleme

1. **Otomatik tekilleştirme** (`search.py`): önce DOI, sonra normalleştirilmiş başlık.
2. **Aşama 1, kural tabanlı filtre** (`screen_stage1.py`). Başlık ve özette aranan etiketler: FRAC, VO, IMPL, FP, MBM, DEF. Kayıt şu koşullarda geçiyor:
   - FRAC etiketi var ve
   - VO ile birlikte IMPL ya da DEF var, ya da FP var, ya da MBM var.
3. **Aşama 2, elle başlık ve özet taraması** (`screening.py`). Her kayıt için karar, ölçüt veya dışlama kodu ve not tutuldu. Kararsız kalınan kayıtlarda tam metin okundu.
   - Dahil etme ölçütleri: I1 gerçekleme, I2 tanım ve dualite, I3 dereceden bağımsız düğüm, I4 operatör düzeyinde yaklaşım, I5 mBm, BG makale için gereken arka plan.
   - Dışlama kodları: PDE, SPACE, VFD (kesirli **gecikme** filtresi), FPAPP, THEORY, APP, MBM, OFF, DUP.
4. **Kartopu** (`snowball.py`): tohum çalışmaların kaynakçaları ve atıfları ile bilinen eksikler. Hedef başlık Crossref'te en az 0.85 benzerlikle eşleşmeliydi. Üç tur yapıldı:
   - 1. tur: S01–S30
   - 2. tur: S31–S42; Sierociuk ve ark. 2020, Arıcıoğlu 2025, Jia ve ark. 2022 ve Ślęzak–Metzler 2023'ün kaynakçalarından
   - 3. tur: S43–S44; tam metin kontrolü sırasında bulundu (FULLTEXT.md)
5. **Tam metin kontrolü** (`fulltext.py`, `fulltext_log.csv`, `FULLTEXT.md`): yalnızca özetten veya ikincil kaynaktan sınıflandırılan kayıtlar için Unpaywall ve arXiv ile açık erişim yeri arandı.
6. **Kaynak doğrulama** (`verify_bib.py`): `paper/refs.bib` içindeki her girdi Crossref ile karşılaştırıldı (`bib_check.csv`). Son durum (72 girdi, 2026-10-07): 56 OK, 12 CHECK, 3 bulunamadı, 1 atlandı.
   - CHECK satırlarının hepsi beklenen farklar:
     - 8 satırda Crossref çevrimiçi-ilk yılı veriyor; `refs.bib`'de cilt yılı kullanıldı.
     - `philippe2008`: Crossref Rusça özgün baskıyla (2007) eşleşiyor; `refs.bib`'de İngilizce çeviri (2008) var.
     - `peltier1995` için Crossref'in eşleştirdiği kayıt farklı bir çalışma (Ayache–Lévy Véhel 1999). Doğrusu INRIA RR-2645 (1995).
     - `wood1994` kaydında Crossref'te yalnızca ilk sayfa var.
     - `widder1941`: başlık araması başka bir çalışmaya (1945 tarihli bir dergi yazısı) eşleşiyor. Kitabın DOI'si (10.1515/9781400876457, Princeton University Press, PMS-6) doğrudan DOI sorgusuyla doğrulandı. Crossref dijital baskıyı 1942 tarihiyle listeliyor; özgün baskı 1941.
   - Bulunamayanlar (Podlubny 1999 ve Kailath 1980 kitapları, Vinagre ve ark. 2000 FCAA) web aramasıyla doğrulandı.
   - Atlanan: TCAS-I yer tutucusu.

## Akış (PRISMA benzeri, `prisma.json`)

| Aşama | Kayıt |
|---|---|
| Bulunan (30 sorgu) | 2639 |
| Tekilleştirme sonrası | 1702 |
| Aşama 1'de dışlanan | 1334 |
| Aşama 1'den geçen | 368 |
| Aşama 2'de dahil edilen (arama) | 90 |
| Kartopu hedefleri / düşen / dahil edilen | 44 / 3 / 41 |
| **Toplam dahil** | **131** |

Ölçütlere göre dağılım: I1 33, I2 27, I3 36, I4 7, I5 23, BG 5.

Aşama 2'de dışlananlar:
- MBM 96, PDE 44 (bu ikisi grup varsayılanı olarak dışlandı, "(default)" notuyla işaretli)
- FPAPP 37, APP 28, SPACE 19, OFF 19, VFD 18, THEORY 15, DUP 2

## Sınırlar

- Crossref alaka sıralaması Scopus/WoS'tan zayıf; sorgu başına 100 kayıt sınırı var ve Crossref'te özetlerin çoğu yok. Bu yüzden eleme çoğunlukla başlık üzerinden yapıldı.
- Ana ayrıştırıcı bulgular için tam metin okundu (SENTEZ.md, "Kanıt" sütunu). Diğer kayıtlar yalnızca başlık veya özetle sınıflandırıldı.
- Tek değerlendirici. İkinci bir okuyucuyla rastgele %10'luk alt kümede uyum kontrolü önerilir.
- Kesirli gecikme (VFD) filtreleri "variable fractional" etiketiyle yakalanıyor ama konu dışı; hepsi dışlandı.

## Yeniden çalıştırma

```bash
python3 litreview/search.py          # ham yanıtlar litreview/raw/ altında önbellekli; --refresh yeniden çeker
python3 litreview/screen_stage1.py
python3 litreview/snowball.py
python3 litreview/screening.py       # screening.csv, included.csv, prisma.json
python3 litreview/extraction.py      # extraction.csv
python3 litreview/verify_bib.py      # bib_check.csv
python3 litreview/fulltext.py --download   # fulltext_log.csv; PDF'ler depo dışına (FT_DIR)
```
