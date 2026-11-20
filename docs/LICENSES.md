# Kullanılan modellerin lisansları

Dubzar ücretli satılacağı için her model ticari kullanıma uygun lisanslı olmalı.
Her satır, ilgili kaynaktan doğrulandığı tarihle yazılır. Lisansı doğrulanmamış model kullanılmaz.

| Bileşen | Lisans | Ticari kullanım | Kaynak | Doğrulama tarihi |
|---|---|---|---|---|
| faster-whisper (kod) | MIT | Evet | https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE | 2026-11-20 |
| openai/whisper (orijinal kod) | MIT | Evet | https://github.com/openai/whisper/blob/main/LICENSE | 2026-11-20 |
| Systran/faster-whisper-tiny (ağırlıklar) | MIT | Evet | https://huggingface.co/Systran/faster-whisper-tiny | 2026-11-20 |
| Systran/faster-whisper-small (ağırlıklar) | MIT | Evet | https://huggingface.co/Systran/faster-whisper-small | 2026-11-20 |

| Helsinki-NLP/opus-mt-tc-big-en-tr (çeviri ağırlıkları) | CC-BY-4.0 | Evet, kaynak belirtme şartıyla | https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-en-tr | 2026-11-20 |

**Kaynak belirtme zorunluluğu (CC-BY-4.0):** Ürünle birlikte dağıtılan bir NOTICE/Hakkında ekranında
"Helsinki-NLP / OPUS-MT, CC-BY-4.0" belirtilmeli ve model kartına bağlantı verilmeli. Bu, paketleme
aşamasında (Task 9 sonrası) yapılacak bir iştir.

Kullanılmayan modeller: NLLB-200 (CC-BY-NC, ticari kullanıma kapalı) ve XTTS (Coqui Public Model License,
ticari kullanıma kapalı) bilerek seçilmedi.

Doğrulama yöntemi: GitHub lisans API'si (`gh api repos/<repo>/license`) ve Hugging Face model API'sinin `license` alanı.
Bu bir hukuki görüş değildir; ürün satışa çıkmadan önce lisans metinleri bir kez de elle okunmalıdır.
