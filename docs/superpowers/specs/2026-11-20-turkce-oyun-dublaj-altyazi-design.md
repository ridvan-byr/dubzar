# Evrensel Türkçe Altyazı ve Dublaj Aracı — Tasarım

Tarih: 2026-11-20 · Durum: onay bekliyor

## Amaç ve neden
Oyunculara, hangi oyunu oynarlarsa oynasınlar, doğal Türkçe dublaj ve altyazı seçeneği sunan, uygun fiyatlı ücretli bir Windows aracı. Fiyatın düşük olması önemli: amaç Türk oyunculara iyilik yapmak.

Başarı ölçütü: karakter konuşmaya başladığı anda Türkçe ses (ve altyazı) başlar. Geriden gelmez.

## Hedefler
- Tek araç, mümkün olan her oyunda çalışır (oyun dosyalarına dokunmadan).
- Altyazı ve dublaj ayrı ayrı açılıp kapanabilir.
- Dublaj doğal duyulur: karaktere tutarlı ses, doğru ton, orijinal replik süresine sığan çeviri.
- Dublaj, replik başladığı anda başlar.
- Her karakterin sesi, orijinal karaktere (cinsiyet, yaş, ton, duygu) uyar ve oyun boyunca tutarlı kalır. Saçma çıkacak replik yerine altyazı gösterilir.
- Oyun sırasında ekran kartına ve işlemciye anlamlı yük bindirmez (ağır işler oyun dışında yapılır).
- Geliştirme ücretsiz: açık kaynak, ticari lisansı uygun, yerel modeller.

## Hedef olmayanlar
- Gerçek dudak şekli uyumu (viseme). Yalnızca zamanlama uyumu hedeflenir.
- Sinematik videolarda AI dudak senkronu (ileride düşünülür).
- Çok oyunculu / rekabetçi oyunlarda anti-cheat ile uğraşmak.

## Anti-hedefler (teknik olarak çalışsa bile başarısızlık sayılır)
- Dublajın repliğin gerisinden gelmesi.
- Robot gibi, tek tip ses.
- Anti-cheat'in aracı tehdit sayıp kullanıcıyı banlaması. Bu yüzden oyuna kanca atmak yerine ses yakalama + ekran üstü katman tercih edilir.
- Oyunun ses/metin dosyalarının dağıtılması (aşağıda hukuki kısıt).

## Kısıtlar
- Windows 10/11, ilk sürümde yalnızca Windows.
- **Hukuki:** Ücretli satılan pakette oyunun kendi ses veya metin dosyası bulunmaz. Çeviri ve ses, kullanıcının bilgisayarında, kendi oyun kopyasından üretilir. Satılan şey araçtır.
- Maliyet: yerel çalışma (kullanıcının GPU'su) mı, bulut mu kararı açık (aşağıya bakın).

## Yaklaşımlar
| | A. Canlı çeviri | B. Oyun başına hazır paket | C. Hibrit |
|---|---|---|---|
| Her oyunda çalışır | Evet | Hayır, oyun başına emek | Evet |
| Dublaj gecikmesi | 1–3 sn (yetersiz) | Yok | Yok (indekslenen oyunlarda) |
| Doğallık | Orta | Yüksek | Yüksek |
| Telif riski | Düşük | Yüksek (dağıtılırsa) | Düşük (yerelde üretilir) |

**Seçilen: C (hibrit).** Kullanıcı onayladı. Canlı çeviri (A) ana dublaj yolu olmaz, çünkü cümle bitmeden çeviremez ve dublajı geç getirir. A, altyazı için ve taranamayan oyunlarda yedek olarak kalır.

## Tasarım


### Temel ilke: ağır iş oyundan önce, oyun sırasında yalnızca hafif katman
Kullanıcı oyun oynarken ekran kartı zaten dolu. Bu yüzden ses tanıma, çeviri ve ses üretimi oyun açıkken çalıştırılmaz. Bunlar "tarama" adımında, oyun kapalıyken bir kez yapılır. Oyun sırasında yalnızca ses parmak izi eşleştirmesi (işlemcide, çok hafif) ve hazır klibin / altyazının gösterilmesi çalışır.

### Aşama 1 — Altyazı (önce bu yapılacak, kullanıcı isteği)
Altyazı, dublajla aynı tarama altyapısından çıkar:
1. **Tarama (oyun kapalıyken, bir kez):** Oyunun ses dosyaları çıkarılır. Her replik tanınır (Whisper türevi), bağlamıyla Türkçeye çevrilir (karakter/terim sözlüğü ile tutarlı), zamanlamasıyla ve ses parmak iziyle indekslenir.
2. **Oyun sırasında:** Çıkış sesinin ilk 200–300 ms'si indeksle eşleştirilir ve altyazı anında gösterilir. Oyuna ek yük binmez, gecikme yoktur.
3. Şeffaf, oyun üstünde duran, tıklanamayan bir katman altyazıyı gösterir. Boyut, konum, renk ayarlanabilir. Anti-cheat riskini azaltmak için oyuna kanca atılmaz.

**Yedek canlı mod:** Taranamayan oyunlar için oyun sesi yakalanır (WASAPI loopback), küçük modeller düşük öncelikle çalışır. 1–2 sn altyazı gecikmesi kabul edilir. Dublaj bu modda yapılmaz.

### Aşama 2 — Dublaj
Aynı indekse Türkçe ses klipleri eklenir:
1. **Tarama sırasında:** Her karakter için bir ses profili çıkarılır (aşağıda), replikler o sesle üretilir, çeviri orijinal süreye sığdırılır.
2. **Oyun sırasında:** Replik başladığı anda klip çalınır, orijinal ses kısılır/bastırılır.
3. **Premium mod (oyuna özel):** Desteklenen motorlarda dosya değiştirme ile kusursuz zamanlama.

Zamanlama kuralları: çeviri orijinal süreye sığar; gerekirse ses en fazla %10–15 hızlandırılır; ses, orijinal repliğin başladığı anda başlar.

#### Karakter sesi uyumu (gereksinim: "saçma çıkmamalı")
- **Konuşmacıyı bul:** Ses dosyası adı/klasörü ve ses benzerliği (speaker diarization / embedding) ile her karakterin repliklerini grupla.
- **Ses profili çıkar:** Her karakter için orijinal sesten cinsiyet, yaklaşık yaş, perde (pitch), tını ve konuşma hızı çıkarılır. Profil, uygun Türkçe sese eşlenir (ücretsiz/ticari lisanslı bir ses havuzundan seçim, ya da lisansı uygunsa ses uyarlama).
- **Tutarlılık:** Bir karakter oyun boyunca hep aynı sesle konuşur. Aynı karakter bölümler arasında farklı sesle çıkmaz.
- **Ton ve duygu:** Her replik için duygu/ton (fısıltı, bağırış, alay, üzüntü) orijinal sesin enerji ve perdesinden ve bağlamdan (LLM etiketi) çıkarılır, TTS'e ipucu olarak verilir.
- **Kalite kapısı:** Üretilen klip süre, anlaşılırlık ve ses benzerliği kontrolünden geçer. Kalite eşiğinin altında kalanlar yeniden üretilir; olmazsa o replik için yalnızca altyazı gösterilir (saçma dublaj yerine altyazı).
- Gürültü/efekt: Efektli sesler (robot, canavar, telsiz) için orijinaldeki efekt zinciri kabaca taklit edilir; yapılamıyorsa o replik altyazıya düşer.

### Aşama 3 — Yedekler ve genişleme
Sesi olmayan oyunlar için metin yakalama / OCR altyazısı; ek motorlar için dosya değiştirme; sinematikler için lip-sync araştırması.

## Karar notları (benim kararlarım, itiraz edebilirsin)
- Altyazı da tarama tabanlı çıkar (canlı mod yalnızca yedek). Gerekçe: kullanıcı oyun oynarken GPU zaten dolu, ağır modelleri oyun sırasında çalıştırmak oyunu bozar. Kullanıcı bu yönü onayladı.
- Tamamen açık kaynak, yerel modeller: geliştirme ücretsiz, kullanıcıya bulut faturası yok.
- **Ticari lisans:** Ürün satılacağı için her model lisansı ticari kullanıma uygun olmalı. Hatırladığıma göre NLLB (çeviri) ve XTTS (ses klonlama) ticari kullanıma kapalı. Bunlar seçilmeyecek. Whisper, Opus-MT, Piper gibi adaylar seçilmeden önce lisansları tek tek doğrulanacak.
- İlk sürüm Windows.

## Açık kararlar (builder'a / kullanıcıya kalan)
- Hangi çeviri / TTS / ses uyarlama motorları (Türkçe kalitesi ve lisans için test edilerek seçilecek; karakter ses uyumu için kritik).
- Tarama süresi hedefi (büyük oyunlarda saatler sürebilir) ve kullanıcıya nasıl gösterileceği.
- Hazır indeksleri (çeviri metni + parmak izi) paylaşmak taramayı kısaltır ama telif açısından gri alandır; ilk sürümde yapılmaz, sonra karar verilir.
- Fiyatlandırma modeli.
- Uygulama teknolojisi (masaüstü uygulama için öneri: Python çekirdek + Electron/Tauri arayüz; builder netleştirir).

