# Dubzar: ölçüm, kalite ve performans planı (taslak)

Durum: **onay bekliyor.** Yazan: Claude. Karar verici: ürün sahibi.

## Neden

Kullanıcının tespiti (21 Kasım 2026, kendi kullanımından): ürün kullanılabilir ama satılacak seviyede değil.

1. Metin türlerini ayırma zayıf: görev/hedef, diyalog, iki konuşmacı.
2. Çeviri kalitesi yeterli değil.
3. Donanım kullanımı piyasada kayda değer bir noktada değil.
4. Hızlı diyalogda satır ara sıra kaçıyor (çevrilmiyor ya da gösterilmiyor).

Bugüne kadar ayarları tek tek "his"e göre yaptık. Her iyileştirmeyi bir rakamla görmek için önce ölçmeliyiz.

## Hedefler (bu planın sonunda neyi görmek istiyoruz)

| Alan | Ölçü | Şimdi | Hedef |
|---|---|---|---|
| Çeviri | 120 satırlık kıyas (`experiments/mt_bench.py`), chrF | **66,7** | 75+ ve "ciddi hata" (anlamı bozan) sayısı yarıya |
| Çeviri (insan) | Türkçe konuşan birinin 50 satırlık körlemesine puanı | ölçülmedi | Dubzar ≥ Google Translate düzeyi, tercih oranı ölçülür |
| Tür ayırma | etiketli kare kümesinde doğru ayırma oranı | ölçülmedi | diyalog satırı doğru: %95+; görev/HUD'u diyalog sanma: %2'nin altı |
| Kaçan satır | kayıtlı sahnede göstermeyen/çevrilmeyen satır oranı | ölçülmedi (bilinen: "ara sıra") | %1'in altı |
| Donanım | oyunun ortalama FPS'ine etkisi (Hafif mod) | ölçülmedi | %3'ün altı |
| Gecikme | metin görününce altyazı gelene kadar | ekran: ≈1,0 sn Hafif, ≈0,4 sn Yüksek; **ses: ölçülmedi** | ekran Hafif 0,7 sn'nin altı, ses için ölçüp hedef koy |

## Kapsam dışı

Bulutta çeviri (gizlilik sözümüzü bozar), ses sentezi/dublaj, başka diller.

## Sıra ve çıktılar

### A. Ölçüm düzeneği (önce bu)

- **A1. Çeviri kıyası:** yapıldı. 120 satır, 7 tür (konuşma, argo, görev, arayüz, resmi, kısa, ocr). Referanslar Claude'a ait; **gerçek doğruluk için insan puanı gerekir (A4).**
- **A2. Kaçan satır ve gecikme tekrar oynatma:** kullanıcının `--debug` günlüğü ve bir ekran kaydı. Çıktı: her satır için "göründü, çevrildi, ne zaman, kaçtıysa hangi kural yuttu". Kullanıcıdan: dolu bir diyalog sahnesinde 3-5 dakikalık `--debug` günlüğü + kaçan satırların yaklaşık anı.
- **A3. Tür ayırma kümesi:** kullanıcının kendi ekran görüntüleri klasöründen (yalnızca yerel ölçüm için, yayına girmez) 60-100 kare; her karedeki yazılar türlerine göre etiketlenir (diyalog, konuşmacı adı, görev, HUD, menü). Etiketleri Claude önerir, kullanıcı örneklem olarak doğrular.
- **A4. İnsan puanı:** 50 satır, kaynak gizli (Dubzar / Claude / Google gibi), kullanıcı 1-5 verir. Bu, Claude referanslarının gerçekten "iyi" olup olmadığını da test eder.
- **A5. Donanım ölçümü:** kullanıcı bir oyunda Dubzar kapalı/açık (Hafif, Yüksek) FPS ve işlemci kullanımını kaydeder (MSI Afterburner ya da NVIDIA overlay). Betik ve talimat hazırlanır.

### B. Kaçan satırlar (A2'den sonra)

Günlükten nedeni bul, o kuralı düzelt, kayıtlı sahnede yeniden ölç. Muhtemel nedenler: meşgulken gelen satırın atılması, ekran okumanın "oturma" beklemesi, hızlı değişen satırın aynı sanılması.

### C. Tür ayırma (A3'ten sonra)

Kuralları A3 kümesinde ölç. Kurallar yetmezse küçük bir sınıflandırıcı (konum, boyut, renk, kalınlık, ekranda kalma süresi gibi özelliklerle; önce basit, gerekirse hafif bir model).

### D. Çeviri kalitesi (A1/A4 ile paralel başlar)

Opus-MT kıyasında görülen hata türleri ve çözümü:

| Hata türü | Örnek (kıyas) | Çözüm |
|---|---|---|
| Oyun terimi | "Low health" → "Düşük sağlık" (olması gereken: Can azaldı), "Do you want to quit without saving?" → "Tasarruf etmeden…" | **Oyun terimi sözlüğü** (save=kaydet, health=can, cover=siper, ride=araba, safehouse=sığınak…) |
| Deyim, argo | "son of a gun" → "silahın oğlu", "freaking awesome" → "müthişti" ama "Adamım" | Deyim listesi + hitap kuralı ("man", "dude" → "dostum") |
| Ekran okuma gürültüsü | "n0w", "Y0u'll": anlam kayboluyor | Okuma sonrası düzeltme (harf içindeki 0→o, 1/l→I gibi), çeviriden **önce** |
| Üslup (siz/sen) | "Saklanın", "Çekilin" (nezaket çoğul) | Oyunda genelde "sen": üslup ayarı (kural ya da eğitim) |
| Bağlam | Kısa satırlar ("Not now.") | Önceki satırları bağlam olarak vermek |

Aşamalar:

1. **Eğitimsiz iyileştirmeler** (kural katmanı: sözlük, ekran okuma düzeltme, hitap, bağlam). Her adım A1'de ölçülür.
2. **Yüksek modda ikinci aşama:** Gemma 4 12B yerel (GPU), sadece zor satırlarda ya da arkadan düzeltme; zaten tasarlandı.
3. **Model eğitimi** (karar noktası aşağıda).

### E. Donanım optimizasyonu (A5'ten sonra)

Bekleyen fikirler (A5 ölçümüne göre sıralanır): bekleme okumasını 6-8 sn'ye çıkarmak, DXGI/WGC ile yakalama, altyazı varken uyarlanır tarama sıklığı, yalnızca yazı satırlarını okuma. Hedef: Hafif mod oyunun FPS'ine %3'ten az etki.

### F. Ekrandaki her yazıyı yerinde çevirme (kullanıcı önerisi, 21 Kasım 2026)

**Fikir:** altyazı dışındaki yazılar da (görev, menü, tabela, eşya açıklaması) çevrilsin ve **özgün yazının üstünde ya da hemen yanında** Türkçe görünsün; altyazıya binmesin.

**Neden iyi:** tür ayırma sorununun (görev mi, diyalog mu) büyük kısmını çözer, çünkü her çeviri kendi yazısının yanında durur ve konum anlamı taşır. Menüler, envanter ve görev listesi gibi altyazısı olmayan yerleri de kapsar. Rakip araçların (Translumo, RSTGameTranslation) en çok beğenilen özelliği de bu.

**Zorlukları (gerçekçi olmak için):**

| Zorluk | Çözüm yönü |
|---|---|
| **Yük:** tüm ekranı okumak, bir şerit okumaktan çok daha pahalı (şerit: GPU 0,09 sn / işlemci 0,5 sn) | Modlara böl: Hafif = şimdiki gibi (şerit ve köşeler); Orta = istek üzerine tüm ekran; Yüksek = GPU ile sürekli. Yalnızca **değişen** bölgeleri okumak: şimdiki metin-değişim izleyicisi şerit yerine karo ızgarası üzerinde çalışır. |
| **Türkçe daha uzun** (İngilizcenin ~%20-30 fazlası) | Kutuya sığdırma: yazıyı küçült, iki satıra böl ya da kutunun yanına/altına koy; ekran kenarını ve altyazı şeridini aşma |
| **Titreme:** kamera döner, dünya yazıları (tabela) kayar | Kutuları kareler arasında eşleştir, çeviriyi önbellekten ver, hareket eden yazıyı sabitlemeye çalışma |
| **Gürültü:** her sayı, skor, mermi sayacı çevrilmesin | Yalnızca harf içeren, anlamlı uzunlukta yazıyı çevir; sabit HUD'u bir kez çevirip önbelleğe al; kullanıcı "yok say" listesi (oyun profiliyle birlikte) |
| **Kısa, bağlamsız yazı** ("Options") kötü çevrilir | Menü sözlüğü (sık menü kelimeleri sabit çevrilir), önbellekli |
| **Oyunu kapatmak:** çevirinin oyunun arayüzünü örtmesi | Üç sunum: yanında etiket (varsayılan), özgün yazının üstüne yerleştirme (arka plan rengini örnekleyerek), ya da yalnızca bir tuşa basılı tutunca göster |

**Aşamalar:**
1. **F1: "Ekranı çevir" kısayolu.** Bir tuşa basınca tüm ekran bir kez okunur, çeviriler birkaç saniye yerinde gösterilir. En az yük, en çok değer; menüler ve görev listeleri için yeter. Zaten bekleyen listede vardı (Ctrl+Shift+T gibi bir kısayol, çakışmayan bir tuşla).
2. **F2: otomatik, durağan ekranlar.** Menü ve envanter gibi ekran sabitken kendiliğinden çevir, değişince yenile. Karo ızgarası değişim izleyicisi burada gelir.
3. **F3: canlı (Yüksek mod).** Oyun sürerken sürekli, GPU ile. Titreme ve yük ölçümüyle.

**Ölçüt:** (a) çeviri etiketi altyazı şeridiyle çakışmıyor (0 çakışma), (b) tam ekran okuma Yüksek modda 0,3 sn'nin altı, (c) etiket yazısı kutudan taşmıyor (sığdırma testi: ölçüm kümesindeki gerçek menü karelerinde), (d) Hafif modun FPS maliyeti değişmiyor.

**Karar (kullanıcı, 21 Kasım 2026): yer seçilebilir olsun.** Panelde "Çeviri yeri" ayarı: **Yanında** (özgün yazının yanında/altında etiket, yazıyı örtmez), **Üstünde** (özgün yazının üstüne, arka plan rengi örneklenerek) ve istenirse **Basılı tutunca** (yalnızca bir tuşa basılıyken). Ayar oyun profiline de girer (oyun başına farklı seçilebilir). Varsayılan: Yanında. Sığmadığında "Yanında" yeri yazıyı kutuya sığdırır; "Üstünde" yeri yazıyı küçültür ve gerekirse taşan kısmı yanına alır. Ölçüt: iki yerleşim de ölçüm kümesindeki gerçek karelerde taşma ve altyazıyla çakışma testinden geçer.

**Kullanıcıdan gereken:** 5-10 örnek menü/görev ekran görüntüsü (test için).

### G. Model adayları (21 Kasım 2026, model kartlarından okundu; **hiçbiri denenmedi**)

ChatGPT'nin önerdiği listenin kartlardan doğrulanan hâli. Hiçbirinde İngilizce→Türkçe skoru yok; bu yüzden hepsi aynı 120 satırlık kıyasta (`experiments/mt_bench.py`) ve hızda denenmeden bir şey söylenmez.

| Model | Lisans (etiket) | Türkçe | Boyut | Not |
|---|---|---|---|---|
| tencent/Hy-MT2-1.8B | Apache-2.0 | listede var | 4 GB (daha küçük GGUF/2-bit sürümleri ayrı depoda) | Terim sözlüğü, bağlam, üslup talimatı destekliyor. **İlk aday.** Çalıştırma: transformers ≥5.6, vLLM, SGLang. |
| tencent/Hy-MT2-7B | Apache-2.0 | listede var | ~8B parametre | GGUF'u llama.cpp'nin ayrı bir yamasına (PR #22836) bağlı. 8 GB ekran kartında sıkışır. İkinci aşama adayı. |
| google/madlad400-3b-mt | Apache-2.0 | adı geçmiyor (419 dil) | 11,8 GB | **Elendi:** 40 satırlık testimizde chrF 42,7 (Opus-MT 59,7), tekrar sorunu. |
| IndexTeam/Index-Translate-9B | Apache-2.0 | doğrulanmadı | 19 GB, ~24 GB bellek | Kendi raporundaki skorlar çok dilin ortalaması. Ağır; Türkçe belirsiz. Şimdilik ertelendi. |
| google/translategemma-12b-it | "gemma" | doğrulanmadı | 24 GB | Kapılı (hesapla şart kabul), kısıt politikası okunmadı. TranslateGemma 4B'yi daha önce denemiştik. Şimdilik ertelendi. |

**Değerlendirme ölçütleri (her aday için):**
1. 120 satırlık kıyasta chrF ve ciddi hata sayısı (terim, deyim, üslup), Opus-MT ile yan yana.
2. Hız: satır başına süre, ekran kartı (RTX 4060) ve işlemcide; ekran kartında OCR ile birlikte çalışırken.
3. Bellek: VRAM/RAM, oyunun yanında sığıyor mu.
4. Lisans metninin **elle okunması** (Tencent `LICENSE.txt`, Gemma şartları, Index'in GitHub lisansı): ücretli üründe kullanıma, dağıtıma, bölge/kullanıcı sınırına izin veriyor mu.
5. Rolü: Hafif modda Opus-MT kalır; aday ancak Yüksek modda ikinci aşama ya da düzeltici olabilir, hızı Opus-MT'yi geçmedikçe varsayılan olamaz.

**Sıra:** önce Hy-MT2 1.8B (4 GB indirme, **kullanıcı izni gerekir**), iyi çıkarsa 7B. Lisans okuması ilk adımda.

## Model eğitimi: ne, nasıl, riskler

**Ne eğitilir:** Opus-MT (tc-big, ~230 milyon parametre) oyun diyaloğuna ince ayar (fine-tune). 8 GB'lık RTX 4060'ta mümkün; veri 20-100 bin satır ise birkaç saat. Sonra CTranslate2 int8 biçimine çevrilir (şimdiki gibi), çalışma hızı aynı kalır.

**Veri sorunu (asıl engel, karar gerekir):**
- **Telif/lisans:** OpenSubtitles gibi altyazı derlemeleri araştırma amaçlı paylaşılır, **ücretli üründe kullanımı belirsiz**. Kullanmadan önce lisans metni okunmalı. Tatoeba (CC-BY) güvenli ama kısa ve oyun diline uzak.
- **Sentetik veri (Claude ile üretilmiş çeviriler):** Anthropic'in kullanım koşulları, çıktıların rakip bir yapay zeka modelini eğitmede kullanımını kısıtlıyor. Küçük bir çeviri modelinin bunu kapsayıp kapsamadığı **belirsiz; koşulları okuyup ya da hukuki görüşle netleştirmeden bunu yapmıyoruz**.
- **Kendi verimiz:** kullanıcının Türkçe düzelttiği satırlar. Yavaş ama temiz. Küçük bir küme bile üslup ve terimde fark yaratır.

**Karar noktası:** A1 sonrası kural katmanı hedefe (chrF 75+, ciddi hata yarıya) yaklaşırsa eğitim gerekmeyebilir. Yaklaşmazsa, veri ve lisans netleştikten sonra ince ayar yapılır; **ölçüm kümesi eğitime hiç katılmaz.**

## Yapılacaklar sırası

1. A1 raporu (hazır) ve kullanıcının A4 puanı için 50 satırlık form.
2. D1: eğitimsiz kural katmanı; her adımda A1.
3. A2 için günlük, B.
4. A3 kümesi, C.
5. A5 ölçümü, E.
6. F1 ("ekranı çevir" kısayolu): ölçüm düzeneği bittikten sonra, en ucuz ve en görünür kazanç; F2 ve F3 donanım ölçümüne göre.
7. G: model adayları (önce Hy-MT2 1.8B), kıyas ve hız ölçümü; sonra D2 ve eğitim karar noktası.

## Kararlar (kullanıcıdan)

1. Kıyasın referansları Claude'dan: kabul mü, yoksa referansları kendin düzeltecek misin? (Düzeltme A4'ten ayrı, ucuz bir yol.)
2. Eğitim için veri kaynağı: önce lisans/koşul okuması mı, yoksa şimdilik eğitimsiz yola mı odaklanalım?
3. A2/A5 için ne zaman bir oyun oturumu ayırabilirsin?
