# Literatür taraması: sentez ve makaleye etkisi

Protokol: [`PROTOKOL.md`](PROTOKOL.md). Dahil edilen 129 kayıt: `included.csv`. Çekirdek karşılaştırma: `extraction.csv` (22 satır).

## Kısa sonuç

Taramada üç önemli öncül çıktı. Üçü de makalede açıkça atıf almalı ve katkı iddiaları buna göre daraltılmalı:

1. **VO için dereceden bağımsız üsler zaten var (sayısal PDE literatürü).**
   - Zhang, Fang ve Sun (JAMC 2021; NMTMA 2022; AMC 2022) VO Caputo türevini, üsleri ve terim sayısı zaman adımından bağımsız bir üstel toplamla yaklaşıyor. Yalnızca ağırlıklar t'ye bağlı.
   - Derece güncel zamanda değerlendiriliyor; yani bu, sürekli zamanda Caputo formunda A-tipi.
   - Huang ve ark. (NMTMA 2022) sabit ve değişken derece için birleşik bir SOE çerçevesi veriyor.
   - Dolayısıyla **"VO için sabit kutup fikri" tek başına yenilik değil.**
2. **Yapı ile tanım arasındaki bağ analog alanda kısmen kurulmuş.**
   - Sierociuk ve ark. (AMM 2015, Theorem 1): her anahtarlamada öne tamamlayıcı-derece bloğu eklenen seri yapı B-tipine (2. tip) eşdeğer.
   - D-tipi için dualiteye dayalı anahtarlama stratejileri var (CSSP 2015, ECC/ICCC 2016).
   - B ailesinde seri şema pratikte kurulamadığı için paralel şema geliştirilmiş (AMC 2018).
   - Electronics 2020: D-tipini analog olarak doğrudan gerçeklemek "pratikte imkânsız", çünkü iki ideal zıt-dereceli operatörün seri bağlantısı kurulamıyor.
   - Bu çalışmaların hepsi sabit dereceli blokların sınırlı sayıda anahtarlamasına dayanıyor. Blok sayısı anahtarlama sayısıyla büyüyor.
3. **mBm'de A/B ayrımı literatürde var.**
   - Wang ve ark. (PRR 2023) memory-multi-FBM'i X(t) = ∫ √α(s)(t−s)^{(α(s)−1)/2} dB(s) olarak tanımlıyor. Üs artışın kendi zamanında değerlendiriliyor; bu, normalizasyon dışında bizim B-tipi varyantımız.
   - Sıçramada daha sürekli davrandığını da gösteriyorlar. Lim'in RL-mBm'i (A-tipi) ile farkı açıkça tartışıyorlar.
   - Benzer fikirler: Ślęzak–Metzler (J. Phys. A 2023, incremental mBm), Sly (J. Appl. Prob. 2007), Surgailis (SPA 2008), Ryvkina (JTP 2015).

## Bulunan boşluk (yenilik iddialarının yeni hali)

Taramada aşağıdakileri yapan bir çalışma bulamadım:

| Yenilik | Durum | Not |
|---|---|---|
| **Gereklilik teoremi** (tam anahtarlama eşlemesi ⇔ benzer gerçekleme ⇔ aynı kutuplar) | Bulunmadı | Hot-swap literatürü geçiş durumlarını bastırmayı inceliyor (Välimäki–Laakso 1998, Zetterberg–Zhang 1988), tanım tutarlılığını değil. Kesirli başlangıç koşulu literatürü "durum" kavramını tartışıyor (Lorenzo–Hartley 2008, Sabatier ve ark. 2014, Trigeassou ve ark. 2012), anahtarlamada hangi tanımın gerçeklendiğini değil |
| **Tek sabit boyutlu bankada çıkış ağırlığı → A, giriş ağırlığı → B** | Bulunmadı | Her dizide, her örnekte geçerli. ESA çalışmaları yalnızca A-tipini (Caputo) ele alıyor. Hidden-memory (B'ye yakın) tanım için bilinen hızlı yöntem O(N log N) Taylor/hiyerarşik matris kullanıyor (Jia ve ark. 2022); sabit üslü O(K) özyineleme değil |
| **GL ağırlıklarının ayrık zamanda Beta-integral gösterimi** | Bulunmadı | Yalnızca kuadratür hatası kalıyor. ESA/SOE çalışmaları sürekli zamanda L1/L2-1σ ayrıklaştırmasıyla çalışıyor |
| **D ve E tiplerinin aynı bankanın cebirsel tersiyle, tam dualiteyle ve O(K) maliyetle gerçeklenmesi** | Bulunmadı | Analog alanda "pratikte imkânsız" diye nitelenmiş (Sierociuk ve ark. 2020) |
| **Analitik, uydurmasız tasarım kuralı ve mühürlü holdout doğrulaması** | Bulunmadı | Wei ve ark. sabit kutuplu yaklaşımlarında katsayılar uydurma ile bulunuyor. SOE çalışmaları hata sınırı veriyor ama A/B/D/E ve ayrık-zaman GL için değil |
| **Ters kararlılık için işaret testi ve DC tabanı** | Bulunmadı | — |
| **Derece ve tipin her örnekte yalnızca ROM adresiyle değiştiği bit-tam donanım** | Bulunmadı | Tolba ve ark. 2020'nin FPGA çekirdeği derecesi çalışma anında ayarlanabilen doğrudan GL konvolüsyonu (sonlu bellek, örnek başına O(L)); kullandığı tanım belirtilmemiş, bizim önermemize göre A-tipi (çıkarım) |
| **mBm için doğru yerleştirilmiş tamsayı bölme** | Bulunmadı | A: önce integre et, B: sonra integre et. Tek bankayla 0 < H < 1 aralığı ve hem RL-mBm (A) hem MMFBM (B) için O(K) akışlı, bit-tam üretim |

## RQ'lara göre özet

**RQ1 (gerçeklemeler).** Analog VO gerçeklemelerin çoğu iki-üç sabit derece arasında anahtarlamaya dayanıyor:
- Sierociuk grubu (domino merdivenler, 2013–2020)
- Macias ve ark. 2019
- Zhou ve ark. 2019

Arıcıoğlu 2025 düzgün değişen derece için tek bir transfer fonksiyonu kullanıyor, ama yalnızca LTI olan üçüncü Lorenzo–Hartley tanımını gerçekleyebiliyor.

Ayarlanabilir dereceli elemanlar ve filtreler sabit derecede çalışıyor; derece yeniden ayar parametresi. Örnekler:
- analog: OTA (Tsirimokou ve ark. 2016), Charef ve Idiou 2012, DAC'li fraktal merdiven (Yu ve ark. 2022)
- dijital: Tseng 2006/2008, Charef ve Bensouici 2011

Bu yapılarda derece değişince ne olduğu analiz edilmemiş. Bizim Önerme 2'ye göre, katsayıları güncel dereceyle değiştirilen bir FIR, uzunluğu kadar belleği olan bir A-tipi operatör (çıkarım). Kutupları dereceye bağlı olan analog yapılar ise Teorem 5 kapsamında.

**RQ2 (tanımlar).**
- Tanım ailesi: Lorenzo–Hartley 2002, Coimbra 2003, Valério–Sá da Costa 2011, Ramirez–Coimbra 2010 (seçim ve anlam), Sun ve ark. 2009/2011, Ortigueira–Valério–Machado 2019.
- A/B/C (1./2./3. tip) ve D/E ile dualite: Sierociuk ve ark. 2013–2020; Sierociuk–Twardy 2014; Malesza ve ark. 2019 (analitik çözüm).
- Tanıma bağlılık sonraki çalışmalarda da vurgulanıyor (Khalid ve Taha 2026, Lyapunov tahminleri).

**RQ3 (dereceden bağımsız düğümler).**
- Sabit derecede geniş bir aile var:
  - difüzif gösterim: Montseny 1998, Diethelm 2023, Diethelm ve ark. 2022
  - sonsuz durum gösterimi: Trigeassou ve ark., ISR derlemesi 2024
  - çekirdek sıkıştırma: Baffet–Hesthaven 2017, Baffet 2018
  - SOE: Jiang ve ark. 2017, Guo ve ark. 2023, Guglielmi–Hairer 2025
  - sabit kutup: Wei ve ark. 2016/2019/2021
- VO tarafında yalnızca ESA/SOE (Zhang–Fang–Sun 2021–2022, Huang ve ark. 2022) bulundu; hepsi PDE çözücüsü bağlamında ve A-tipi Caputo.
- Dağılmış dereceli çekirdek sıkıştırma da dereceler arasında ortak düğüm kullanıyor (2025, arXiv). Çok dereceli ortak düğüm fikrine bir başka örnek.

**RQ4 (her örnekte derece değişen donanım).** Tolba ve ark. 2020 (FPGA, çalışma anında yapılandırılabilen derece, değişken dereceli kaotik osilatör) dışında örnek bulunmadı. O çalışmada da tanım ve bellek uzunluğu doğrudan GL konvolüsyonuyla sınırlı.

**RQ5 (operatör düzeyinde VO yaklaşımları).** Tamsayı türevli seri açılımları (Almeida–Torres 2013; Tavares ve ark. 2016), polinom uydurma (Huang ve ark. 2018, iki CCC bildirisi; özetlere erişilemedi), genişletilmiş algoritmalar (Moghaddam–Machado 2017). Hiçbiri gerçekleme yapısı ile tanım arasındaki ilişkiyi ele almıyor.

**RQ6 (mBm).**
- A-tipi: RL-mBm (Lim 2001).
- B-tipi ya da ona yakın:
  - MMFBM (Wang ve ark. 2023)
  - IMFBM (Ślęzak–Metzler 2023)
  - integrated fractional white noise (Sly 2007)
  - nonhomogeneous fractional integration (Surgailis 2008)
- Tanımların denk olmadığı: Stoev–Taqqu 2006.
- VO operatörlerle mGn sentezi: Sheng ve ark. 2010, 2011.
- Sentez yöntemleri: Chan–Wood 1998, dalgacık tabanlı (Wang ve ark. 2008).
- Yerel Hurst kestirimi: Istas–Lang 1997, Coeurjolly 2005, Bardet–Surgailis 2013.

## Makalede yapılacak değişiklikler (bu turda yapıldı)

1. **Giriş:**
   - Gerçekleme paragrafı yeniden yazıldı (anahtarlamalı analog çalışmalar, ayarlanabilir dereceli elemanlar, dijital VO diferansiyatörler, FPGA).
   - **Arıcıoğlu 2025 atfı düzeltildi.** Önceki taslak bu çalışmayı "hot swap" örneği diye anıyordu; yanlıştı.
2. **Yeni bölüm "Related work"** ve karşılaştırma tablosu (yapı, tanım, kutuplar, derece değişimi, tipler, maliyet).
3. **Katkılar revize edildi.**
   - ESA çalışmaları öncül olarak anılıyor.
   - Yenilik şu noktalara taşındı: yapı–tanım bağı, A ve B tek bankada, ayrık-zaman GL tamlığı, D/E terslemesi, kural, kararlılık, donanım.
4. **mBm bölümü:** B-tipi süreç MMFBM ile ilişkilendirildi; per-increment normalizasyon giriş ön kazancı olarak bankaya katılıyor. "Hangi tanım" vurgusu Wang ve ark. ile paylaşılıyor.
5. **Hot-swap tartışması:** değişken özyinelemeli filtrelerde geçiş durumu bastırma ve kesirli başlangıç koşulu literatürüne atıf eklendi.
6. **refs.bib:** yeni girdiler Crossref künyesiyle eklendi. `montseny1998` doğrulandı.

## Açık kalanlar

- Scopus/WoS'ta aynı dizgelerle tekrar (PROTOKOL.md).
- Tam metin kontrolü gerekenler:
  - Tseng 2006 (yapı)
  - Huang ve ark. 2018 (iki CCC bildirisi, polinom uydurma)
  - Charef ve Ladaci 2024 (IFAC)
  - Valério–Sá da Costa 2011 (hangi tipleri hangi yaklaşımla)
  - Huang ve ark. 2022 (VO SOE'de düğümler dereceden bağımsız mı?)
- İkinci okuyucuyla eleme uyumu.
