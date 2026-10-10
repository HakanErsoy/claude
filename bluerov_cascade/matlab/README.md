# T200 yeniden tanımlama (MATLAB Student + System Identification Toolbox)

JESTECH makalesindeki T200 modeli (Denk. 1, 4 kutup / 2 sıfır) MathWorks'ün "Robotics Arena: From Data
to Model" paketindeki betikle aynı yoldan çıktı: ortalama çıkarılıyor, filtreleniyor ve **tek bir
kayda** (`T200_Square_0-10_Hz_1600-1900_us`) `tfest(…, 4, 2)` uyduruluyor. Sorunlar:

- Doğrusal model: ölü bant, asimetri ve itkinin hızla karesel artışı yok; ortalaması çıkarılmış veride
  çalışma noktası bilgisi kayboluyor.
- Paketteki diğer 11 kayıt (üç genlik seviyesi: 1600–1900, 1650–1850, 1700–1800 µs; kare ve sinüs;
  0–10 ve 0–100 Hz) doğrulamada kullanılmamış.
- −0.245'teki kutup ile −0.358'deki sıfır neredeyse sadeleşiyor: saniyeler mertebesinde, büyük olasılıkla
  fiziksel olmayan bir "sürünme" modu.
- CSV başlığı kuvveti "lb" diyor (çerçeveye bağlı yük hücresi); JESTECH'te birim N. Ölçek kalibre
  edilmeli.

`t200_reident.m` bunları ele alıyor: 12 kaydın hepsini yükler, kuvvet ölçeğini üreticinin bollard
eğrisine göre kalibre eder (ölçek + ofset, en uygun voltaj), aynı tahmin kaydında dört model uydurur ve
hepsini kalan 11 kayıtta mutlak seviyede doğrular:

| Model | Yapı |
|---|---|
| M0 | Doğrusal `tfest(4,2)`, ortalaması çıkarılmış veri (JESTECH modeli) |
| M1 | Hammerstein: T200 statik eğrisi → 1. derece + gecikme |
| M2 | Hammerstein: T200 statik eğrisi → 2. derece + gecikme |
| M3 | Wiener (fiziksel): hız komutu → 1. derece + gecikme → itki ∝ hız² |

## Çalıştırma

Aynı klasöre koy:
1. `t200_reident.m` (bu dosya)
2. `T200_Dataset/` klasörü — File Exchange #65919 paketinden
   (<https://www.mathworks.com/matlabcentral/fileexchange/65919>)
3. `T200-Public-Performance-Data-10-20V-September-2019.xlsx` —
   <https://cad.bluerobotics.com/T200-Public-Performance-Data-10-20V-September-2019.xlsx>

MATLAB'da `t200_reident` yaz. R2021b veya yenisi ve System Identification Toolbox gerekir.

## Bana geri gönderilecekler

- `t200_reident_fits.csv` — her model ve kayıt için NRMSE uyum yüzdesi
- `t200_reident_params.csv` — zaman sabiti, kazanç, gecikme, voltaj, kuvvet ölçeği
- `t200_reident.png` — üç kaydın karşılaştırma grafiği
- Komut penceresi çıktısı (voltaj/ölçek kalibrasyonu, M0 kutupları ve sıfırları, M2 sönümü)

Bu değerlerle simülatördeki itici gecikmesi (şu an varsayım: τ_m = 0.1 s, 30 ms) tanımlanmış değerlere
çekilecek; tasarımdaki belirsizlik aralığı da tanımlamanın doğrulama hatasına göre seçilecek.

**Lisans:** File Exchange paketinin lisansı kullanımı MathWorks ürünleriyle sınırlıyor; bu yüzden
tanımlama MATLAB'da yapılıyor ve veri depoda tutulmuyor. Depoya yalnızca tanımlanan parametreler ve
uyum tabloları girecek.
