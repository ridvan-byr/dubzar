# Kullanılan modellerin lisansları

Dubzar ücretli satılacağı için her model ticari kullanıma uygun lisanslı olmalı.
Her satır, ilgili kaynaktan doğrulandığı tarihle yazılır. Lisansı doğrulanmamış model kullanılmaz.

| Bileşen | Lisans | Ticari kullanım | Kaynak | Doğrulama tarihi |
|---|---|---|---|---|
| faster-whisper (kod) | MIT | Evet | https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE | 2026-11-20 |
| openai/whisper (orijinal kod) | MIT | Evet | https://github.com/openai/whisper/blob/main/LICENSE | 2026-11-20 |
| Systran/faster-whisper-tiny (ağırlıklar) | MIT | Evet | https://huggingface.co/Systran/faster-whisper-tiny | 2026-11-20 |
| Systran/faster-whisper-small (ağırlıklar) | MIT | Evet | https://huggingface.co/Systran/faster-whisper-small | 2026-11-20 |

Doğrulama yöntemi: GitHub lisans API'si (`gh api repos/<repo>/license`) ve Hugging Face model API'sinin `license` alanı.
Bu bir hukuki görüş değildir; ürün satışa çıkmadan önce lisans metinleri bir kez de elle okunmalıdır.
