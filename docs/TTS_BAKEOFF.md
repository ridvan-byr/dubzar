# TTS motor karşılaştırması (dublaj öncesi ön koşul)

Hedef: robotik olmayan, doğal Türkçe; klonlama YOK (karakter sesine yakın bir ses metinle tarif edilir
veya lisanslı bir sesten seçilir); duygu kontrolü; ticari lisans. Karar kulakla verilir.

## 1. Aday taraması (2026-11-20) — lisanslar resmi API'lerden doğrulandı

| Aday | Lisans (kod / ağırlık) | Türkçe | Klonlamasız ses | Duygu | Not |
|---|---|---|---|---|---|
| **VoxCPM2** (openbmb) | Apache-2.0 / Apache-2.0 | Evet (30 dilden biri) | **Voice Design:** cinsiyet, yaş, ton, duygu, hızı metinle tarif, referans ses gerekmez | Metin tarifiyle | 2B parametre, 48 kHz, GPU gerekir |
| **Trendyol-TTS** | MIT | Evet (Türkçe ince ayar, VoxCPM2 tabanlı) | VoxCPM2 üzerinden | Duyguya dair bilgi model kartından doğrulanacak | Ahenk'in kendi tablosunda en yüksek puan |
| **Ahenk** (ozgurguler) | Kod Apache-2.0 / ağırlık **CC-BY-4.0** (kaynak belirtme şart) | Evet (Türkçe LoRA) | VoxCPM2 üzerinden | 6 duygu + kahkaha, soru tonlaması | 2B + 36M LoRA, GPU |
| **Ahenk Cep** | CC-BY-4.0 | Evet | Sabit tek ses | Sınırlı | 8,6M, 34 MB, işlemcide çalışır; daha düşük kalite, yedek aday |
| **Chatterbox** (Resemble AI) | MIT / MIT | Çok dilli sürümde Türkçe iddiası var, doğrulanacak | Referans ses ister, sesi sabit bir lisanslı örnekle sınırlı | "Exaggeration" ayarı | Çıktılara Perth filigranı ekliyor |

Elenenler: XTTS-v2 (ticari kullanıma kapalı), Fish Speech S1-mini (CC-BY-NC), MMS-TTS (ticari değil),
Kokoro (Türkçe yok), Piper Türkçe sesi (eğitim verisinin ticari lisansı belirsiz; ses kalitesi de eski nesil).

Kaynaklar: Hugging Face model API'leri (`ozgurguler/ahenk-tts-tr`, `Trendyol/Trendyol-TTS`, `openbmb/VoxCPM2`,
`ResembleAI/chatterbox`) ve GitHub lisans API'leri. Blog yazılarına dayanan iddialar bu tabloda yoktur.

## 2. Test düzeneği

- Bilgisayar: NVIDIA GeForce RTX 4060 Laptop, 8 GB VRAM (2B modeller sığmalı; sığmazsa bf16/yarım hassasiyet).
- Ortak metin: aynı ~20 Türkçe replik; her biri nötr, öfkeli, fısıltı, üzgün tonla.
- Ortak ses profili: genç erkek / yaşlı kadın / çocuk / kalın sesli asker (Voice Design ile).
- Ölçütler: Türkçe doğallık (robotik mi?), duygu aktarımı, ses tutarlılığı (aynı karakter), hız, VRAM.
- Sonuç: sana dinletilir, motor seçimi senin kulağınla yapılır.

## 3. Sonuçlar
(Henüz çalıştırılmadı.)
