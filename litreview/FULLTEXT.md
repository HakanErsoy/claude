# Tam metin kontrolleri

Tarih: 2026-10-06. Amaç: SENTEZ.md ve makalede yalnızca özetten, web özetinden veya başka bir makalenin ifadesinden sınıflandırılan kayıtları birincil kaynaktan doğrulamak.

**Erişim.** Açık erişim yerleri Unpaywall ve arXiv ile arandı (`fulltext.py`, `fulltext_log.csv`). PDF'ler depo dışında geçici klasörde okundu; depoya yalnızca notlar girdi.
- **Erişilemeyenler:** Springer ve ScienceDirect, açık erişimli makalelerde bile JavaScript doğrulaması istiyor. Bu ortamdan açılamadı.
- **Denenen ve bırakılan yol:** headless tarayıcıyla erişim izin denetiminde reddedildi ve bırakıldı.
- **Kapalı erişim:** yayıncı paywall'u, metne ulaşılamadı.

## Sonuçlar

| Kayıt | Kaynak | Kontrol edilen | Bulgu | Etkisi |
|---|---|---|---|---|
| Sierociuk, Podlubny, Petráš 2013 (TCST) | arXiv:1107.2575 (tam metin) | Anahtarlamalı gerçekleme mi? | **Hayır.** Domino ve iç içe merdiven gibi pasif, sabit devreler. Frekans bölgesinde 0.5 ve 0.25 dereceli; zaman bölgesinde dereceleri ~0.5'ten ~1'e değişiyor. Değişken derece davranışı gösteren ilk pasif devre örnekleri | **Hatalı atıf düzeltildi:** taslakta "2–3 sabit derece arasında anahtarlayan gerçeklemeler" arasında sayılmıştı |
| Ryvkina 2015 (JTP) | arXiv:1306.2870 (tam metin) | H değişimi yalnızca yeni artışları mı etkiliyor? | **Hayır.** Süreç kovaryansla tanımlı, çekirdekte güncel H(t) var, H ∈ (1/2, 1). Önerme 3.2.4: H'de sıçrama varsa yollar hemen hemen kesin süreksiz | **Hatalı sınıflama düzeltildi.** B-tipi değil, A-tipine benzer davranıyor |
| Yu, Pu, He, Yuan 2022 (Fractal Fract.) | MDPI (tam metin) | Derece değişirken analiz var mı, hangi tanım? | **Var.** Programlanabilir R/C ile fraktal merdiven; eleman değerleri dereceyle değişiyor, yani kutuplar hareketli. Dinamik deneyde derece 50 Hz'de −0.33 ↔ −0.66 atlıyor; bir deneyde de sürekli −0.3 → −0.7. Referans denk. (65–67): ağırlıklar u(t−jh) için μ(t−jh) derecesiyle (B-tipi), ölçek 1/F^{(μ(t))} güncel zamanda. Devre teorisi ile GL "örtüşüyor", deneyde sıçrama parazitik etkilerle yumuşuyor | "Davranış analiz edilmemiş" ifadesi bu çalışma için **yanlıştı**. Ayrı satır eklendi: hareketli kutuplu bir B-tipi yaklaşımı; Teorem 5'e göre yalnızca yaklaşık olabilir |
| Oziablo, Mozyrska, Wyrwas 2020 (Entropy) | MDPI (tam metin) | Hangi VO farkı, maliyet | FVOGLD: tüm katsayılar güncel derece ν_k ile (yazarlar "type A" ile karşılaştırıyor). Adım başına k+1 çarpma; derece her adımda değişirse katsayı vektörü baştan hesaplanıyor. Tamponun sınırlandırılması yazarlara göre açık problem | Atıf mozyrska2019'dan (kapalı) oziablo2020'ye taşındı; "A-tipi, maliyet zamanla büyüyor" doğrulandı |
| Philippe, Surgailis, Viano 2006 (CRAS) ve 2008 (TVP) | Comptes Rendus (açık erişim PDF) | **Yeni öncül** | Zamanla değişen kesirli filtreler A(d) ve B(d). Katsayılar aradaki zamanların d_u değerlerinin çarpımı. Sabit d'de ikisi de (I−L)^{−d}. **B(−d)A(d) = A(−d)B(d) = I** | Yeni atıf. GL tiplerinden farklı bir aile ama tam ters ilişkisi dualiteye benziyor. Tanımlar bölümüne ve ilgili çalışmalara eklendi |
| Surgailis 2008 (SPA) | Kapalı (ScienceDirect); Bardet–Surgailis 2013 (arXiv tam metin) ve web özeti | B-tipi mi? | Philippe ve ark. filtrelerinin sürekli zamana genişletilmesi; homojen olmayan kesirli integrasyonla iki süreç (X ve Y). Kovaryansları mBm'deki gibi H(t), H(t′)'nin yerel fonksiyonu değil; dekorelasyon özellikleri daha iyi. "Yalnızca yeni artışlar" niteliği **doğrulanamadı** | İfade doğrulanan bilgiyle sınırlandı |
| Sly 2007 (J. Appl. Prob.) | Kapalı; yalnızca özet | Tanım | Özet: mBm, H'deki değişimlere çok duyarlı ve büyüklüğü aşırı değişiyor; integrated fractional white noise bunu önlüyor. Tanım **doğrulanamadı** | İfade özetle sınırlandı |
| Huang ve ark. 2022 (NMTMA) | Kapalı; yayıncı sayfası yalnızca özet | VO SOE düğümleri dereceden bağımsız mı? | **Doğrulanamadı.** Özet yalnızca "VO çekirdekleri için birkaç SOE" ve birleşik çerçeveden söz ediyor | Tablo 1'de "sabit üs, A-tipi" satırından çıkarıldı; metinde yalnızca özetteki ifade kaldı |
| Wei ve ark. 2019 (ISA Trans.) | UTS OPUS (özet; tam metin kapalı) | Kutuplar dereceden bağımsız mı? | Özet: "the poles keep constant for different α"; α = 0 çevresi için iki iyileştirme; sabit derece | Doğrulandı (özet düzeyinde) |
| Tolba ve ark. 2020 (NoDy) | Kapalı | Hangi VO tanımı? | **Doğrulanamadı.** Özet: GL donanımı, çalışma anında yapılandırılabilen derece, zamanla değişen dereceli kaotik osilatör | Metindeki çıkarım koşullu hale getirildi: "ağırlıklar güncel dereceyle hesaplanıyorsa A-tipi" |
| Sierociuk, Malesza, Macias 2015 (CSSP) | Açık erişim ama Springer JS doğrulaması nedeniyle açılamadı | D-tipi anahtarlama yapısı | Tam metin okunamadı. Electronics 2020'deki (tam metin) ifadeler destekliyor | Değişiklik yok |
| Charef ve Ladaci 2024 (IFAC-PapersOnLine) | Açık erişim ama ScienceDirect JS doğrulaması nedeniyle açılamadı | Tanım ve yapı | **Doğrulanamadı** | Makalede atıf yok; extraction.csv'de "erişilemedi" |
| Huang ve ark. 2018 (iki CCC bildirisi) | Kapalı (IEEE) | Yapı | **Doğrulanamadı** | Makalede atıf yok |
| Valério ve Sá da Costa 2011 (Signal Process.) | Kapalı | Tanımlar | Doğrudan okunamadı. Electronics 2020 (tam metin) bu çalışmayı "en az altı ana tip" ifadesinin kaynakları arasında sayıyor | Makaledeki "ek varyantlar" atfı bu ikincil ifadeyle destekli |
| Tseng 2006/2008; Charef–Bensouici 2012 | Kapalı | Yapı | Doğrulanamadı; yalnızca başlıklar | Makalede yalnızca başlık düzeyinde iddia ("derece ayarlanabilir parametre") bırakıldı |
| Zhou ve ark. 2019; Macias ve ark. 2020 | Kapalı | 2–3 derece arasında anahtarlama | İki bağımsız ikincil kaynak destekliyor: Arıcıoğlu 2025 ve Yu ve ark. 2022 ("switching strategy to switch between two or three-order types") | Değişiklik yok |
| Lim 2001 | Kapalı | A-tipi tanım | MMFBM makalesi (tam metin) MFBM'in α(s) yerine α(t) kullandığını ve Lim'e atıf verdiğini yazıyor | Değişiklik yok |

## Makaleye yansıyan düzeltmeler (bu turda yapıldı)

1. **Analog gerçeklemeler.**
   - Sierociuk 2013 TCST artık "zaman bölgesinde değişken derece davranışı gösteren pasif merdivenler" olarak anılıyor.
   - "İki-üç derece arasında anahtarlama" iddiasının kaynakları Arıcıoğlu 2025 ve Yu ve ark. 2022.
2. **Ayarlanabilir dereceli yapılar.**
   - Genel "davranış analiz edilmemiş" ifadesi kaldırıldı.
   - Yu ve ark. 2022'nin dinamik deneyi ve B-tipi referansı ayrıca anlatılıyor; Tablo 1'e ayrı satır olarak eklendi.
3. **FPGA ve kontrolör.**
   - Tolba ve ark. 2020 için çıkarım koşullu hale getirildi.
   - Kontrolör atfı Oziablo ve ark. 2020'ye taşındı; A-tipi ve zamanla büyüyen maliyet doğrulandı.
4. **SOE/ESA.** Tablo 1'deki "sabit üs, A" satırında yalnızca Zhang–Fang–Sun var. Huang ve ark. yalnızca özet düzeyinde anılıyor.
5. **Philippe–Surgailis–Viano** ilgili çalışmalara ve tanım bölümüne eklendi (zaman serisi literatüründeki tam ters ilişki).
6. **mBm bölümü.**
   - Ryvkina A-tipine benzer davranış örneği olarak taşındı.
   - Surgailis ve Sly ifadeleri doğrulanan içerikle sınırlandı.
