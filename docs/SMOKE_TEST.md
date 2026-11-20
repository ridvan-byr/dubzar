# Duman testi sonuçları

## 2026-11-20 — gerçek bileşenlerle, sentetik "oyun" sesi

**Kapsam:** Gerçek bir oyun DEĞİL. Windows'un konuşma sentezleyicisiyle üretilmiş 4 İngilizce cümle.
Gerçek Whisper (`tiny`, işlemci), gerçek parmak izi ve indeks, gerçek WASAPI loopback yakalama.
Çeviri sahte: metnin başına "TR: " eklendi (gerçek Opus-MT çalıştırılmadı).
Müzik ve efekt yok; bu yüzden gürültü altında dayanıklılık hakkında bir şey söylemez.

**Sonuç:**
- Tarama: 4/4 dosya indekslendi (~4 sn, işlemcide). Tanıma bir yerde hafif hatalı: "Old Bridget Midnight" ("old bridge at midnight" yerine).
- Canlı dinleme: 4/4 replik doğru eşleşti, yanlış eşleşme yok.
- Eşleşme gecikmesi (yaklaşık, en yakın önceki yüksek ses başlangıcına göre): ~0, 609, 297, 203 ms.
  Ölçüm kabadır: cümle içi duraklamalar ek "başlangıç" üretir, bu yüzden gerçek gecikme bu rakamlardan büyük olabilir. Hedef ~300 ms.

**Testin yakaladığı gerçek hatalar (hepsi düzeltildi, testleri eklendi):**
1. `WhisperTranscriber` varsayılan `device="auto"` ile ekran kartını seçiyordu; CUDA kütüphanesi (`cublas64_12.dll`) olmayan bilgisayarda her dosya hata veriyordu. Artık işlemciye düşüyor.
2. `run` komutundaki `iter(kuyruk.get, None)` numpy dizisini `None` ile karşılaştırıp çöküyordu. `queue_chunks` ile değişti.
3. `IndexStore` ana thread'de açılıp eşleştirme thread'inde kullanılınca SQLite hatası veriyordu. Artık thread'ler arası kullanım güvenli (kilitli).
Üçü de sahte modelle yazılmış birim testlerde görünmüyordu; ancak gerçek bileşenlerle çalışınca ortaya çıktı.

**Henüz yapılmayan:**
- Gerçek bir oyunun çıkarılmış ses dosyalarıyla tarama ve oyun sırasında canlı test.
- Müzik/efekt altında eşleşme oranı.
- Gerçek Opus-MT çeviri modeliyle tarama.
- `run` komutunun şeffaf pencereyle uçtan uca elle denenmesi (otomatik testte pencere/yakalama yok).
