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

**Sonuç 1: Hy-MT2-1.8B (22 Kasım 2026, RTX 4060, transformers, bf16, açgözlü çözümleme).** Lisans: `LICENSE.txt` düz Apache-2.0 (okundu). 120 satırlık kıyas (`experiments/mt_bench_llm.py`, raporlar `mt_bench_hymt2_report.md` ve `mt_bench_hymt2_terms_style_report.md`):

| | chrF | satır başına süre | VRAM |
|---|---|---|---|
| Opus-MT (CPU, int8) | **66,7** | ~110 ms | ~0 |
| Hy-MT2-1.8B | 62,0 | 800 ms | 3,6 GB |
| Hy-MT2-1.8B + sözlük + "sen" üslubu | 62,4 | 660 ms | 3,6 GB |

- Opus-MT'den 5+ puan iyi satır 28, 5+ puan kötü 48, yakın 44.
- **Güçlü yanı:** ekran okuma gürültüsüne dayanıklı ("n0w" → "Şimdi"), argo ("freaking awesome" → "inanılmaz derecede harikaydı"), kısa cümleler ("Not now", "Nice shot"), sözlük ve üslup talimatını gerçekten uyguluyor ("save" → "Kaydetmeden çıkmak istiyor musun?", "Siper bul", emir kipinde "sen").
- **Zayıf yanı:** kısa ünlemlerde ciddi hatalar ("Cover me!" → "Kapıyı kapatın!"/"Siperimi aç!", "Hold your fire!" → "Sakin olun!"), "ride" → "atlı araba", deyim kaçırıyor ("son of a gun"). Sözlük küçük modelde **sızabiliyor**: "Press R to reload." → "Doldur deme, araba." (sözlükteki iki kelime çevirinin içine girmiş).
- **Hüküm:** Opus-MT'nin yerine geçmez (kalite düşük, 6-7 kat yavaş). "Yüksek" modda düzeltici/ikinci aşama olarak şimdilik zayıf aday; önce Opus-MT üstüne kural katmanı daha ucuz ve daha etkili görünüyor. 7B'yi (GGUF/FP8, 8 GB'a sığması için) ve Gemma 4 12B'yi aynı kıyasla denemeden bu karar kesinleşmez.
- **Kısıtlar (dürüstlük):** referanslar Claude'dan; çözümleme açgözlü (kartın önerdiği örnekleme değil); transformers ile ölçüldü, llama.cpp/vLLM ile daha hızlı olabilir ama Opus-MT'yi geçmesi beklenmez; sözlüğün birkaç terimi kıyas satırlarıyla örtüşüyor, yani sözlük sonucu yöntemin çalıştığını gösterir, genelleme başarısını değil.

**Sonuç 2: Opus-MT'yi ayar oynayarak ne kadar iyileştirebiliriz? (22 Kasım 2026, 120 satırlık kıyas; `experiments/mt_variants.py`, `experiments/mt_rerank.py`)**

| Ayar | chrF |
|---|---|
| şimdiki (int8, beam 4) | 66,7 |
| beam 8 | 67,0 |
| beam 8 + uzunluk cezası 1,3 | 67,5 |
| float32 (int8 yuvarlaması yok), beam 4 / 8 | 66,8 / 66,6 |
| 8-en-iyi içinden en benzer olanı seçmek (MBR) | +0,6 |
| 8-en-iyi içinden Hy-MT2-1.8B'nin en olası bulduğunu seçmek | +1,4 |

Hepsi gürültü ile yakın (±1): **kod çözme ayarı, sayısal doğruluk ve yeniden sıralama "belirgin" iyileştirme vermiyor; sınır modelin kendisi.** Bu yüzden kazanç girdi/çıktı işlemede (kurallar, sözlük, şablon) ve model uyarlamasında (ince ayar) aranmalı.

**Bulgu (uygulamadaki sorun, düzeltilecek):** satırı cümlelere bölen ve "Ad: metin" başındaki adı çeviriden ayıran katman, arayüz ve görev yazılarında zarar veriyor: aynı model ham satırla çevrilince "arayuz" türü 58,7 yerine 67,2 çıkıyor. Muhtemel neden: "Difficulty: Hard", "Controls: …", "Optional: …" gibi etiketlerin konuşmacı adı sanılıp çeviriden ayrılması ("Difficulty: Sert"), ve "Low health. Find cover." gibi kısa cümlelerin ayrı ayrı çevrilmesi. Çözüm: konuşmacı adı kuralını sıkılaştırmak (bilinen arayüz etiketleri ve çok kelimeli/küçük harfli adlar hariç) ve ölçmek. Not: kıyasın "ocr" türü uygulamadaki ekran okuma düzeltmesini (`textfix.py`) **atlıyor**, yani gerçekte olduğundan kötü görünüyor.

**Sonuç 3: kural katmanları uygulandı (22 Kasım 2026; `dubzar/gameterms.py`, `dubzar/textsplit.py`, `experiments/mt_rules_bench.py`).**

| Katman | chrF | arayüz | görev |
|---|---|---|---|
| önce | 66,7 | 58,7 | 70,5 |
| + etiket kuralı (arayüz etiketleri konuşmacı sayılmaz) | 68,0 | 65,7 | 73,1 |
| + "Press E to …" şablonu | 68,4 | 68,9 | 73,1 |
| + sık arayüz satırı belleği (**şişirilmiş**: 7 satır kıyasta var) | 69,7 | 77,8 | 73,8 |

Dürüst okuma: etiket kuralı ve şablon gerçek kazanç (+1,7, arayüz ve görev yazılarında); bellek yalnızca birebir satırlarda çalışır, kıyastaki kazancı kıyas satırlarıyla örtüştüğü için abartılı. **Argo, kısa ünlem ve resmi türler hiç değişmedi**: onları bu katmanlar çözmez, ancak model uyarlaması ya da başka bir model.
Şablon, modelin "to X" yapısını doğru çevirmesine dayanır ("to open the door" → "Kapıyı açmak için"); model amaç tümleci vermezse cümle modele bırakılır.

**Sonuç 4: insan puanı, bugünkü gerçek seviye (22 Kasım 2026, 90 yeni satır, kör A/B, puanlayan: ürün sahibi; `experiments/rating/`).**

| | Düzgün | Küçük sorun | Ciddi hata |
|---|---|---|---|
| Dubzar (Opus-MT + kurallar) | **%87** (78/90) | %9 | **%4** (4/90) |
| Claude | %87 (78/90) | %10 | %3 (3/90) |

Tercih: 53 eşit, 23 Claude, 14 Dubzar.
Dubzar türe göre (düzgün / ciddi): konuşma %93 / 0, görev %90 / 0, kısa %100 / 0, bağlamlı %88 / 0, resmi %80 / %10, argo %78 / %11, **arayüz %75 / %13**.

Dubzar'ın 12 sorunlu satırı: 8'i anlam, 6'sı doğallık (bazı satırlar ikisi birden). Ciddi 4'ü: "Hold Shift to sprint" → "Sprint için…" (şablonun koruması bunu kaçırdı: model amaç yerine yabancı kelime verdi), "got jumped" → "bardan atlamış", "ball-buster" → "top avcısı", "accused of treason against the crown" → "Tacına ihanetle…". Küçük sorunlar: "Your game has been saved" → "kurtarıldı" (save = kaydet), "No dice" → "Zar yok", "stirs" → "karışır", "Then we go around" → bağlamsız "Sonra da dolaşacağız", ve resmi çoğul emir ("kurtarın").

Önemli ölçüm notları: (1) Claude'un kendi çevirisi de %87 düzgün: ölçüt "Claude seviyesi" ise Dubzar zaten orada; hedef artık "Claude'dan iyi" olmalı. (2) 90 satırda tek bir oranın hata payı yaklaşık ±3,5 puan; ±7 puandan küçük farklar bu kümeyle ayırt edilemez, takip için en az 200 satırlık yeni küme gerekir. (3) Bu 90 satıra bakarak kural yazarsak küme "geliştirme kümesi" olur; son ölçüm için yeni bir küme yazılacak.

**Sonuç 5: Seviye 1 işleri uygulandı (22 Kasım 2026; `dubzar/rewrites.py`, `dubzar/register.py`, `dubzar/gameterms.py`).**

1. **Şablon koruması ve fiil tablosu:** "to sprint" → "Sprint için" gibi kopya cevaplar reddediliyor; yaygın oyun fiilleri (sprint, aim, take cover, interact, …) tablodan çevriliyor.
2. **"save" anlamı:** oyun/ilerleme/veri/dosya bağlamında "save" → "record" yazılıp çevriliyor ("kurtarıldı" yerine "kaydedildi").
3. **Deyim ve argo yeniden yazımları** (İngilizce tarafta daha sade ifadeye): got jumped, ball-buster, no dice, tip off, tick off, cut the crap, beat it, freaking, son of a gun, "evil stirs", "against the crown", pulling my leg, "this ride", wannabe, "timer expires".
4. **Emir kipi:** tek yüklemli İngilizce emirlerde son sözcük çoğuldan tekile ("kurtarın" → "kurtar", "ateş etmeyin" → "ateş etme"); virgüllü/"and"li cümlelere dokunulmaz.

Etki: puanlanan 12 sorunlu satırdan 8'i düzeldi (jumped, ball-buster, sprint, crown, stirs, save, timer, no dice), 4'ü değişmedi (nerve, falling apart, wannabe→"sahtekar" kısmen, bağlamsız "Then we go around"). Geliştirme kıyası (120 satır) 68,4 → 70,9, **ama bu artış şişirilmiş**: yeniden yazımlar o kıyastaki hatalardan seçildi. Gerçek ölçüm: `experiments/rating/final.html` (200 yeni satır, tek çeviri, insan puanı; satırlar kurallar yazıldıktan sonra, onlara bakmadan yazıldı). Bu küme kullanıldıktan sonra geliştirme kümesi olur.

**Sonuç 6: son kontrol, 200 yeni satır (22 Kasım 2026, tek çeviri, insan puanı; `experiments/rating/final_results.json`).**

| | Düzgün | Küçük sorun | Ciddi hata |
|---|---|---|---|
| Dubzar, Seviye 1 işlerinden sonra | **%62,5** (125) | %20,5 (41) | **%17** (34) |

Türe göre düzgün / ciddi: konuşma %100 / 0, kısa %93 / 0, bağlamlı %93 / 0 (üçü birlikte 65 satır: %97 düzgün, 0 ciddi), arayüz %72 / %18, görev %48 / %16, resmi %47 / %10, **argo %18 / %50**.

Okuma: (1) günlük konuşma çözülmüş durumda; zayıflık deyim/argo, resmi anlatım, görev emirleri ve arayüz etiketleri. (2) İlk 90 satırlık küme (%87 / %4) kolaydı; bu küme bilerek deyim ağırlıklı (argo 40, resmi 30): iki rakam doğrudan kıyaslanamaz. (3) **Seviye 1 hedefi (≥%90 / ≤%2) çok uzak ve kural katmanıyla ulaşılamaz:** yeniden yazım listesindeki deyimlerin hiçbiri bu kümede çıkmadı, deyim açık uçlu; kural yazmak "köstebek vurmaya" dönüyor. (4) Kural katmanında bulunan somut açıklar: "Experience: 1200 / 2000" ve "Fuel: 40%" etiketleri konuşmacı adı sanılıp çevrilmedi (iki nokta sonrası harf içermiyorsa etiket sayılmalı); emir fiili listesi eksik ("Lure" tekile çevrilmedi); "Take out the sniper" → "çıkar"; bir sözcük bozuk üretildi ("bilins").

**Ek ölçümler (aynı 200 satır, yeni):**
- **Güven ile yönlendirme (router):** Opus-MT'nin kendi toplam log-olasılığı hata tahmin ediyor (AUC 0,81; ciddi hata ile düzgün satır ayrımı). En güvensiz %40'ı (80 satır) ikinci modele yollamak 34 ciddi hatanın **25'ini** yakalıyor (rastgele %40 yollamak 12'sini yakalardı); satır uzunluğu tek başına çok daha zayıf (14/34). Eşik henüz ayarlanmadı ve bu kümede doğrulanmadı.
- **İkinci model (Hy-MT2-1.8B, "sen" üslup istemiyle), ciddi hatalı 34 argo/görev/arayüz/resmi satırda (Claude yargısı, ana dili Türkçe olan biri değil):** kabaca yarısında belirgin daha iyi ("kicked the bucket" → "vefat etti", "we're toast" → "mahvoluruz", "rip-off" → "dolandırıcılık", "Fuel: 40%" → "Yakıt: %40"), diğer yarısında hâlâ yanlış ("hotshot" → "senatör", "master volume" → "Usta Ses Seviyesi"). Genel kıyasta ise Opus-MT'den kötüydü (chrF 62,0 / 66,7) ve kısa ünlemlerde ciddi hatalar yapıyordu: yani **ikisini birleştiren melez** mantıklı, tek başına ikisi de yetmez.

**Karar önerisi:** hedefi ve yöntemi değiştir: (a) ucuz kural açıklarını kapat (etiket, fiil listesi); (b) melez: Opus-MT hızlı yol, güveni düşük satırlar GPU'da ikinci modele (Yüksek mod); (c) melezin gerçek kazancı için ikinci modelin çıktısını da insan puanıyla ölçmek (yaklaşık 80 satır); (d) sonra ince ayar.

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
