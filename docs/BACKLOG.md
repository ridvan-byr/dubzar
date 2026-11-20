# Yapılacaklar (öncelik sırasıyla)

Öncelik: **altyazı ve dublajın tam çalışması.** Aşağıdaki ayar ve iyileştirmeler ondan sonra gelir.

## Ana hat (önce bunlar)
1. Task 9: komut satırı (`scan`, `run`) ve gerçek bir oyunla altyazı duman testi.
2. Dublaj öncesi TTS motor karşılaştırması (`docs/TTS_BAKEOFF.md`), sonra Aşama 2 planı (karakter sesi, duygu, süre eşleme, dublaj klipleri).
3. Oyun motoru arşivlerinden ses çıkarma bağdaştırıcıları (Wwise, FMOD, Unity, Unreal) için ayrı plan.

## Altyazı katmanı ayarları ve panel
- ~~Altyazı konumunu ayarlama~~ — YAPILDI (panelde mini ekranda sürükle, yön tuşlarıyla da).
- ~~Hangi ekranda görüneceğini seçme~~ — YAPILDI (`auto` = oyunun ekranı, `primary`, 1, 2, ...).
- ~~Ayar paneli, kısayolla açılma, ayarların kaydedilmesi~~ — YAPILDI (Ctrl+Shift+D; boyut, renkler, opaklık, altyazı aç/kapat, varsayılana dön).
- Panelde kısayolu değiştirebilme (şimdilik ayar dosyasından: `%APPDATA%\Dubzar\settings.json`).
- Yazı tiplerini (DM Sans, Instrument Serif) uygulamayla paketlemek. Şimdi Segoe UI ve Georgia yedekleri kullanılıyor. İndirme izni ve OFL lisans doğrulaması gerekir.
- "Dublaj" anahtarı dublaj gelene kadar "yakında" olarak soluk; dublaj bitince `dubbing_available=True` yapılacak.

## Küçük iyileştirmeler ve açık işler
- ~~Konuşma olmayan dosyalar tarama yeniden başlatılınca tekrar tanınıyor~~ — YAPILDI: atlanan dosyalar hatırlanıyor; daha iyi model sonrası `scan --retry-skipped`.
- Gerçek çeviri modeli (Opus-MT) duman testi çalıştırılmadı (`pytest -m slow`; `torch` ve büyük model indirmesi gerekir). Sözlük yer tutucularının gerçek modelde bozulup bozulmadığı bilinmiyor.
- Ses cihazı değişince (hoparlör/kulaklık) yeniden bağlanma elle denenmedi.
- Müzik ve efekt altında eşleşme dayanıklılığı gerçek oyun sesiyle ölçülmedi (10 dB sentetik gürültüde 10 oy, alt sınır 8).
- Ürüne CC-BY-4.0 kaynak belirtmesi (Helsinki-NLP / OPUS-MT) için "Hakkında" ekranı eklenmeli.
- `main` dalındaki ilk commit mesajında hâlâ eski "Dubly" adı var (geçmiş yeniden yazılmadı).
- Resmi marka ve alan adı kontrolü (Dubzar): TÜRKPATENT sorgusu, `.com`/`.io` alınabilirliği.

## Logo
- Açık zeminli sürüm (işaret amber, yazı grafit) henüz üretilmedi.
- ~~Açılış animasyonunu uygulamada oynatmak~~ — YAPILDI (`dubzar/ui/Intro.qml`): oyun açılınca D belirir, harfler D'nin arkasından açılır, sonra kısayol ipucu çıkar.
- Logo için bir tasarımcının optik ince ayarı (köşe yarıçapları, nokta oranı) ürün satışından önce düşünülmeli.
