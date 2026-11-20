# Canlı Mod ve İlerleyen Tarama Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcı kurup beklemeden altyazı görsün: oyun sesi canlı tanınıp çevrilir ve indekse öğrenilir; çıkarılmış ses dosyaları oyun kapalıyken arka planda taranıp indeksi büyütür.

**Architecture:** `SpeechSegmenter` oyun sesini konuşma parçalarına böler. `LiveEngine` her parça için önce indeksi dener (hızlı yol), bulamazsa küçük modelle tanır, çevirir, altyazı gösterir ve güvenilirse indekse öğrenir. `BackgroundScanner` mevcut `scan_folder`'ı duraklatılabilir ve ilerleme bildiren bir iş parçacığında çalıştırır.

**Tech Stack:** Mevcut yığın (Python, numpy, faster-whisper, Opus-MT, SQLite, PySide6). Yeni bağımlılık: `psutil` (BSD-3, oyun sürecini bulmak için).

**Spec:** `docs/superpowers/specs/2026-11-20-turkce-oyun-dublaj-altyazi-design.md` (Aşama 1b)

## Global Constraints

- Oyuna kanca atılmaz; yalnızca loopback ses yakalama ve ayrı pencere.
- Canlı mod varsayılan olarak yalnızca işlemcide küçük model kullanır; ekran kartı ayardan açılır.
- Hedef canlı gecikme ≤ 2 sn; kurulumdan ilk altyazıya ≤ 2 dakika.
- Yanlış altyazı göstermektense altyazı göstermemek tercih edilir; düşük güvenli tanıma ne gösterilir ne öğrenilir.
- Arka plan taraması, ayarlı oyun süreci çalışırken duraklar.
- Ticari lisans kuralı değişmez; yeni model eklenmez.

## Review Focus

1. **Yalnızca müzik/ortam sesi (konuşma yok):** altyazı çıkmaz, indekse çöp öğrenilmez. (Task 3)
2. **Aynı replik ikinci kez gelir:** tanıma modeli ikinci seferde çağrılmaz, indeks kullanılır. (Task 3)
3. **Canlıdan öğrenilen replik, sonradan taramayla gelen aynı dosya:** çift kayıt ve çift altyazı olmaz. (Task 4)
4. **Konuşma/müzik kesintisiz uzar (parça sınırı yok):** parça azami sürede zorla kesilir, gecikme sınırlı kalır. (Task 2)
5. **Oyun kapanıp açılır, tarama yarıda kesilir:** tarama kaldığı yerden devam eder, kayıp yok. (Task 5)

---

### Task 1: Konuşma parçalayıcı

**Files:**
- Create: `dubzar/segmenter.py`, `tests/test_segmenter.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) Segment(samples: np.ndarray, start_s: float, end_s: float)`; `class SpeechSegmenter: __init__(self, threshold_db: float = -40.0, min_speech_s: float = 0.25, end_silence_s: float = 0.45, max_segment_s: float = 12.0)`; `feed(self, chunk: np.ndarray) -> list[Segment]` (16 kHz mono float32); `flush(self) -> list[Segment]`.

- [ ] **Step 1: Failing tests** (sentetik "konuşma benzeri" sesle, `tests/test_fingerprint.py::synth_line` kullanılır): `test_splits_two_lines_separated_by_silence` (1.5 sn konuşma, 1 sn sessizlik, 2 sn konuşma → iki parça, süreleri ±0.2 sn); `test_ignores_blips_shorter_than_min_speech` (0.1 sn tıkırtı → parça yok); `test_force_cuts_continuous_audio_at_max_segment_s` (30 sn kesintisiz ses → her parça ≤ 12 sn, toplam ses kaybı yok); `test_silence_only_returns_nothing`; `test_flush_returns_the_unfinished_segment`; `test_chunk_boundaries_do_not_change_the_result` (aynı ses 1600 ve 733 örneklik parçalarla beslenince aynı parça sayısı).
- [ ] **Step 2:** `pytest tests/test_segmenter.py -v` → FAIL.
- [ ] **Step 3: Implement `SpeechSegmenter`** in `dubzar/segmenter.py`. 10 ms çerçevelerde RMS dB; konuşma başlangıcı eşik üstü ≥ `min_speech_s`; bitiş `end_silence_s` sessizlik; `max_segment_s`'te zorla kes. Parçaya konuşmanın önünden 0.15 sn bağlam ekle.
- [ ] **Step 4:** PASS. Commit: `feat: streaming speech segmenter`.

### Task 2: Tanımaya güven puanı

**Files:**
- Modify: `dubzar/asr.py`, `tests/test_asr.py`

**Interfaces:**
- Produces: `Transcription(text: str, language: str, duration_s: float, confidence: float = 1.0)`; `WhisperTranscriber.transcribe` güveni `exp(ortalama avg_logprob) * (1 - ortalama no_speech_prob)` ile hesaplar (0..1).

- [ ] **Step 1: Failing tests:** `test_confidence_is_high_for_a_confident_segment` (sahte segmentler `avg_logprob=-0.1, no_speech_prob=0.01` → ≥ 0.85); `test_confidence_is_low_for_a_doubtful_segment` (`avg_logprob=-1.5, no_speech_prob=0.5` → < 0.2); `test_existing_callers_still_work_without_confidence` (`Transcription("a","en",1.0).confidence == 1.0`).
- [ ] **Step 2:** FAIL doğrula.
- [ ] **Step 3: Uygula** (sahte `FakeWhisperModel` segmentlerine bu alanlar eklenir).
- [ ] **Step 4:** PASS. Commit: `feat: transcription confidence`.

### Task 3: Canlı motor

**Files:**
- Create: `dubzar/live.py`, `tests/test_live.py`
- Modify: `dubzar/index.py` (`remove_line`), `tests/test_index.py`

**Interfaces:**
- Consumes: `Segment` (Task 1), `Transcription.confidence` (Task 2), `fingerprint`, `IndexStore.lookup/add_line/get_cue`, `Transcriber`, `Translator`.
- Produces: `class LiveEngine: __init__(self, store: IndexStore, transcriber: Transcriber, translator: Translator, on_cue: Callable[[Cue], None], min_confidence: float = 0.6)`; `process(self, segment: Segment) -> Cue | None`; `IndexStore.remove_line(self, line_id: str) -> bool`. Canlıdan öğrenilen satırın `line_id` değeri `"live/" + sha256(16 kHz mono örnekler)[:12]`.

- [ ] **Step 1: Failing tests** (sahte transcriber/translator, `tests/test_scan.py` yardımcıları): `test_unknown_segment_is_transcribed_shown_and_learned`; `test_known_segment_uses_the_index_without_transcribing` (Review Focus 2: ikinci `process` çağrısında `transcriber.calls == 1`, cue aynı metin); `test_silence_or_music_without_speech_shows_nothing_and_learns_nothing` (Review Focus 1: transcriber `None` döner → cue yok, `store.count_lines() == 0`); `test_low_confidence_is_neither_shown_nor_learned` (güven 0.3); `test_segment_too_short_or_too_long_is_not_learned` (< 0.8 sn, > 12 sn: gösterilir ama öğrenilmez); `test_remove_line_deletes_the_cue_and_its_hashes` (`tests/test_index.py`).
- [ ] **Step 2:** FAIL doğrula.
- [ ] **Step 3: Uygula.** Sıra: parmak izi → `store.lookup` ile eşleştirme (mevcut `Matcher` mantığı, `min_votes` aynı) → eşleşti ise kayıtlı `Cue`; değilse tanıma, güven kontrolü, çeviri, cue, öğrenme koşulları sağlanırsa `add_line`.
- [ ] **Step 4:** PASS. Commit: `feat: live subtitle engine that learns`.

### Task 4: Canlıdan öğrenilen kayıtla taramayı birleştirme

**Files:**
- Modify: `dubzar/scan.py`, `tests/test_scan.py`

**Interfaces:**
- Consumes: `LiveEngine` kayıt biçimi (`"live/..."`), `Matcher`, `IndexStore.remove_line`.
- Produces: `scan_folder` bir dosyayı indekslemeden önce, sesinin başı bir `live/` satırıyla ≥ `min_votes` oyla eşleşiyorsa o canlı satırı siler ve taranan satırı ekler (taranan kayıt kalıcıdır: tam dosya, doğru zamanlama).

- [ ] **Step 1: Failing tests:** `test_scan_replaces_a_live_learned_line_for_the_same_audio` (Review Focus 3: önce `LiveEngine` ile öğrenilir, sonra `scan_folder` aynı sesi tarar → `store.count_lines() == 1`, `get_cue("a.wav")` var, `live/...` yok); `test_scan_keeps_unrelated_live_lines`.
- [ ] **Step 2:** FAIL doğrula.
- [ ] **Step 3: Uygula** (yalnızca yeni indekslenecek dosyalar için eşleştirme; maliyeti ölç, gerekirse ilk 3 sn ile sınırla).
- [ ] **Step 4:** PASS. Commit: `feat: scan supersedes live-learned lines`.

### Task 5: Arka plan tarayıcı

**Files:**
- Create: `dubzar/background.py`, `tests/test_background.py`
- Modify: `dubzar/scan.py`, `pyproject.toml`, `dubzar/settings.py`

**Interfaces:**
- Produces: `scan_folder(..., should_pause: Callable[[], bool] = lambda: False, natural_order: bool = True)` (dosyalar arasında `should_pause()` doğruysa bekler); `is_process_running(name: str) -> bool` (psutil); `class BackgroundScanner: __init__(self, folder, store_path, make_transcriber, make_translator, game_exe: str | None, on_progress: Callable[[int, int], None])`; `start()`, `stop()`, `progress -> tuple[int, int]`; `Settings.game_exe: str | None` (varsayılan `None`; `None` ise otomatik arka plan taraması yok).

- [ ] **Step 1: Failing tests:** `test_scan_pauses_while_should_pause_is_true_and_resumes` (Review Focus 5); `test_natural_order_scans_mission2_before_mission10`; `test_background_scanner_does_nothing_without_a_game_exe_setting`; `test_background_scanner_waits_while_the_game_is_running` (sahte `is_process_running`); `test_stop_interrupts_cleanly_and_a_restart_continues` (yarım kalan taramayı yeniden başlatınca `indexed` toplamı doğru, kopya yok); `test_is_process_running_finds_this_python_process`.
- [ ] **Step 2:** FAIL doğrula.
- [ ] **Step 3: Uygula.** Her tarayıcı kendi SQLite bağlantısını açar (iş parçacığı güvenli indeks zaten kilitli ama ayrı bağlantı daha güvenli).
- [ ] **Step 4:** PASS. Commit: `feat: pausable background scanner`.

### Task 6: Panelde durum ve ilerleme

**Files:**
- Modify: `dubzar/ui/controller.py`, `dubzar/ui/Panel.qml`, `tests/test_ui.py`

**Interfaces:**
- Produces: `SettingsController.set_status(text)` zaten var; durum metinleri: `"Canlı"`, `"Öğreniyor 34%"`, `"Dinleniyor"` (tarama yok, indeks dolu).

- [ ] **Step 1: Failing tests:** `test_status_shows_scan_percentage` (`set_scan_progress(34, 100)` → `status == "Öğreniyor 34%"`); `test_status_falls_back_to_live_when_nothing_is_scanned`.
- [ ] **Step 2–4:** Uygula, PASS. Commit: `feat: scan progress in the panel status`.

### Task 7: Uygulamaya ve komut satırına bağla

**Files:**
- Modify: `dubzar/app.py`, `dubzar/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `SpeechSegmenter`, `LiveEngine`, `BackgroundScanner`, `Settings`.
- Produces: `python -m dubzar run --index oyun.db [--audio-dir <klasör>] [--game-exe <GTA5.exe>] [--live-device cpu|gpu]`. İndeks yoksa/boşsa `run` artık hata vermez, yeni indeks açar (canlı mod). `--audio-dir` ve `--game-exe` verilirse arka plan taraması etkinleşir.

- [ ] **Step 1: Failing tests:** `test_run_creates_an_empty_index_instead_of_failing` (eski `test_run_requires_an_existing_index_file` ve `test_run_with_empty_index_tells_user_to_scan_first` yeni davranışa göre güncellenir); `test_run_wires_live_engine_to_cues` (enjekte edilmiş ses parçaları → `on_cue` ile Türkçe altyazı); `test_game_exe_without_audio_dir_is_rejected`.
- [ ] **Step 2–4:** Uygula, PASS. Commit: `feat: run uses live mode with background scan`.

### Task 8: Gerçek oyun denemesi (elle)

**Files:**
- Modify: `docs/SMOKE_TEST.md`

- [ ] **Step 1:** Çeviri modelini (Opus-MT) ve istenirse Whisper `small`'u indir (kullanıcı onayı).
- [ ] **Step 2:** Gerçek bir oyunda (GTA 5 hikâye modu, pencereli tam ekran) canlı modu çalıştır; ölç: ilk altyazıya kadar süre, canlı gecikme, doğru/yanlış/eksik altyazı örnekleri, oyunun akıcılığına etkisi (kullanıcı gözlemi, mümkünse FPS göstergesi).
- [ ] **Step 3:** Sonuçları ve gözlenen sorunları dürüstçe `docs/SMOKE_TEST.md`'ye yaz; gerçek ölçümlerle eşikleri güncelle.
- [ ] **Step 4:** Commit: `docs: live mode real-game smoke test`.

---

## Self-review

- **Spec kapsamı:** canlı mod (Task 1–3, 7), öğrenme (3), birleştirme (4), arka plan tarama ve duraklama (5), ilerleme (6), gerçek oyun ölçümü (8). Ekran kartı kurulumu (CUDA kütüphanesi) bu planın dışında, açık karar olarak spec'te duruyor.
- **Bilinen boşluklar:** hikâye sırasına göre önceliklendirme yalnızca doğal dosya sırası; "yanlış öğrenilmiş repliği unutma" aracı yok; canlı çeviri kalitesi (bağlam, sözlük) iyileştirilmedi.
- **İmzalar:** `Segment`, `Transcription.confidence`, `LiveEngine.process`, `remove_line`, `scan_folder(should_pause, natural_order)` görevler arasında tutarlı.
- **Oran:** plan, spec'in Aşama 1b bölümünü karşılayan 8 görev; kod gövdeleri yok, yalnızca imzalar ve testler.
