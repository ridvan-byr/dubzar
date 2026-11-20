# Aşama 1: Tarama Tabanlı Türkçe Altyazı Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Oyunun ses dosyalarını oyun kapalıyken bir kez tarayıp Türkçe altyazı indeksi çıkaran, oyun sırasında hafif bir ses eşleştirmesiyle altyazıyı replik başladığı anda ekranda gösteren Windows aracı.

**Architecture:** İki ayrı süreç: `scan` (ağır: ASR + çeviri + parmak izi, GPU/CPU serbest) ve `run` (hafif: loopback ses yakalama, yalnızca CPU'da parmak izi eşleştirme, şeffaf altyazı katmanı). İkisi bir SQLite indeksiyle konuşur. Model sarmalayıcıları arayüz arkasında olduğu için testler sahte modellerle çalışır.

**Tech Stack:** Python 3.11, pytest, numpy/scipy, faster-whisper (MIT), Opus-MT (CC-BY 4.0, lisans Task 4'te doğrulanır), SQLite, PyAudioWPatch (WASAPI loopback), PySide6 (altyazı katmanı). Arayüz/paketleme kararı (Electron/Tauri) bu planın dışında; çekirdek ve katman Python'da kalır, builder kararı: tek dil.

**Spec:** `docs/superpowers/specs/2026-11-20-turkce-oyun-dublaj-altyazi-design.md`

## Global Constraints

- Yalnızca Windows 10/11.
- Tüm modeller yerel ve açık kaynak; bulut API yok. Her model ticari kullanıma uygun lisanslı olmalı (NLLB ve XTTS kullanılmaz).
- Satılan pakete oyunun ses veya metin dosyası girmez; çeviri ve indeks kullanıcının bilgisayarında, kendi kopyasından üretilir.
- Oyun sırasında (`run`) GPU kullanılmaz; ASR/çeviri yalnızca `scan` içinde çalışır.
- Oyuna kanca atılmaz (anti-cheat riski): yalnızca loopback ses yakalama ve ayrı bir şeffaf pencere.
- Eşleştirme hedefi: replikten ilk 300 ms ses geldiğinde altyazı çıkar; yanlış altyazı göstermektense hiç göstermemek tercih edilir.
- Altyazı katmanı tıklanamaz, boyut/konum/renk ayarlanabilir.

## Review Focus

1. **Tam ekran (exclusive) oyun:** katman görünmez. Beklenen: uygulama bunu belgeler/uyarır ve pencereli tam ekran önerir; çökmez. (Task 8)
2. **Müzik/efekt konuşmanın üstüne biniyor:** eşleşme güveni düşer. Beklenen: yanlış altyazı yerine hiç altyazı. (Task 2)
3. **Aynı replik iki dosyada (kopya ses):** tek replik olarak indekslenir, çifte altyazı çıkmaz. (Task 3)
4. **Tarama yarıda kesilir ve yeniden başlatılır:** kaldığı yerden devam eder, kopya kayıt oluşmaz. (Task 6)
5. **Sessiz, konuşma olmayan (homurtu, çığlık) veya İngilizce dışı dosya:** atlanır, çökmez, indekse boş altyazı yazılmaz. (Task 6)

---

## Dosya yapısı

- `dubly/models.py` — `Cue`, `MatchResult` veri sınıfları.
- `dubly/index.py` — SQLite indeks (`IndexStore`).
- `dubly/audio.py` — ses okuma ve 16 kHz mono'ya çevirme.
- `dubly/fingerprint.py` — parmak izi çıkarma + akışlı eşleştirici (`Matcher`).
- `dubly/asr.py` — `Transcriber` arayüzü + faster-whisper uygulaması.
- `dubly/translate.py` — `Translator` arayüzü + Opus-MT uygulaması, sözlük desteği.
- `dubly/scan.py` — tarama hattı.
- `dubly/capture.py` — WASAPI loopback yakalama.
- `dubly/overlay.py` — altyazı zamanlama modeli (`SubtitleTimeline`) + PySide6 penceresi.
- `dubly/__main__.py` — `scan` ve `run` komutları.
- `docs/LICENSES.md` — kullanılan modellerin doğrulanmış lisansları.
- `tests/` — her modül için `test_<modül>.py`.

### Task 1: Proje iskeleti ve veri modeli

**Files:**
- Create: `pyproject.toml`, `dubly/__init__.py`, `dubly/models.py`, `tests/test_models.py`

**Interfaces:**
- Produces: `Cue(line_id: str, text_src: str, text_tr: str, duration_s: float, speaker: str | None = None)` (frozen dataclass); `MatchResult(line_id: str, offset_frames: int, votes: int)`.

- [ ] **Step 1:** `git init`, `pyproject.toml` (Python ≥3.11, pytest dev bağımlılığı), boş `dubly/__init__.py`.
- [ ] **Step 2: Failing test** `test_cue_is_immutable_and_roundtrips`: `Cue("a1","hi","selam",1.2)` oluştur, `dataclasses.replace(cue, text_tr="x").text_tr == "x"`, orijinal değişmez; alan atamak `FrozenInstanceError` fırlatır.
- [ ] **Step 3:** `pytest tests/test_models.py -v` → FAIL (ImportError).
- [ ] **Step 4:** `dubly/models.py` içinde iki veri sınıfını yaz.
- [ ] **Step 5:** Test PASS. Commit: `feat: project skeleton and data models`.

### Task 2: Parmak izi ve akışlı eşleştirici

**Files:**
- Create: `dubly/audio.py`, `dubly/fingerprint.py`, `tests/test_fingerprint.py`

**Interfaces:**
- Consumes: `MatchResult` (Task 1).
- Produces: `to_mono_16k(samples: np.ndarray, sr: int) -> np.ndarray`; `fingerprint(samples: np.ndarray) -> list[tuple[int, int]]` (16 kHz mono girdi; `(hash, anchor_frame)` çiftleri; spektrogram tepe noktası tabanlı landmark hash); `class Matcher: __init__(self, lookup: Callable[[list[int]], list[tuple[str, int, int]]], min_votes: int = 8)` — `lookup(hashes)` her hash için `(line_id, line_anchor_frame, query_hash_index)` döndürür; `feed(self, samples: np.ndarray) -> MatchResult | None` yeni ses ekler, tutarlı zaman farkı oyu `min_votes`'u geçerse sonuç döndürür.

- [ ] **Step 1: Failing tests** (`tests/test_fingerprint.py`, sentetik sesle: sabit tohumlu 3 sn beyaz gürültü "replik"):
  - `test_matches_line_from_first_300ms`: replik indekslenir, ilk 300 ms `Matcher.feed` edilir → `result.line_id` doğru.
  - `test_matches_with_music_at_10db`: aynı 300 ms'ye 10 dB SNR ek gürültü → hâlâ doğru id (gerekirse 600 ms'ye kadar beslenerek).
  - `test_returns_none_for_unrelated_audio`: farklı tohumlu gürültü → `None`.
  - `test_low_snr_returns_none_not_wrong_line` (Review Focus 2): 0 dB SNR'da sonuç ya doğru id ya `None`; asla başka replik id'si.
- [ ] **Step 2:** `pytest tests/test_fingerprint.py -v` → FAIL.
- [ ] **Step 3:** `audio.to_mono_16k` (scipy `resample_poly`, kanalları ortala) ve `fingerprint` uygulamasını yaz: STFT, frekans bandı başına yerel tepe noktaları, anchor→hedef çiftlerinden hash.
- [ ] **Step 4:** `Matcher` uygulaması: biriken ses üzerinde `fingerprint`, `lookup` sonuçlarında `(line_id, line_anchor - query_anchor)` farkına oy, en çok oy ≥ `min_votes` ve ikinci en iyiden belirgin büyükse döndür.
- [ ] **Step 5:** Testler PASS. Commit: `feat: audio fingerprint and streaming matcher`.

### Task 3: İndeks deposu

**Files:**
- Create: `dubly/index.py`, `tests/test_index.py`

**Interfaces:**
- Consumes: `Cue` (Task 1).
- Produces: `class IndexStore: __init__(self, path: str)`; `add_line(self, cue: Cue, hashes: list[tuple[int, int]], content_digest: str) -> bool` (aynı `content_digest` zaten varsa kaydetmez, `False` döner); `get_cue(self, line_id: str) -> Cue | None`; `has_digest(self, digest: str) -> bool`; `lookup(self, hashes: list[int]) -> list[tuple[str, int, int]]` (Task 2'deki `Matcher` ile aynı biçim).

- [ ] **Step 1: Failing tests:** `test_add_and_get_cue`; `test_duplicate_digest_is_indexed_once` (Review Focus 3: aynı `content_digest` ile ikinci `add_line` `False`, `get_cue` tek replik); `test_lookup_returns_line_and_anchor`.
- [ ] **Step 2:** FAIL doğrula.
- [ ] **Step 3:** SQLite şeması (`lines`, `hashes` tablosu, `hash` üzerinde indeks); `IndexStore` uygulaması.
- [ ] **Step 4:** PASS. Commit: `feat: sqlite index store`.

### Task 4: Konuşma tanıma sarmalayıcı

**Files:**
- Create: `dubly/asr.py`, `tests/test_asr.py`, `docs/LICENSES.md`

**Interfaces:**
- Produces: `class Transcriber(Protocol): transcribe(self, samples: np.ndarray) -> Transcription | None`; `@dataclass Transcription(text: str, language: str, duration_s: float)`; `class WhisperTranscriber(model_size: str = "small", device: str = "auto")` faster-whisper kullanır; konuşma bulunmazsa veya dil `en` değilse `None` döner.

- [ ] **Step 1:** Whisper (faster-whisper) lisansını resmi kaynaktan doğrula, sonucu ve kaynak bağlantısını `docs/LICENSES.md`'ye yaz.
- [ ] **Step 2: Failing tests** (sahte `WhisperModel` enjekte edilerek): `test_returns_none_for_silence`; `test_returns_none_for_non_english`; `test_returns_text_and_duration`.
- [ ] **Step 3:** FAIL → `WhisperTranscriber` uygula (model enjekte edilebilir) → PASS.
- [ ] **Step 4:** Yavaş duman testi `tests/test_asr_slow.py` (`@pytest.mark.slow`): gerçek model ile kısa bir İngilizce örnek. Commit: `feat: whisper transcriber wrapper`.

### Task 5: Çeviri sarmalayıcı

**Files:**
- Create: `dubly/translate.py`, `tests/test_translate.py`
- Modify: `docs/LICENSES.md`

**Interfaces:**
- Produces: `class Translator(Protocol): translate(self, text: str, context: list[str] = ()) -> str`; `class OpusMtTranslator(glossary: dict[str, str] | None = None)`; sözlük terimleri çeviride sabit karşılığıyla kullanılır.

- [ ] **Step 1:** Opus-MT İngilizce→Türkçe modelinin (Helsinki-NLP) lisansını model kartından doğrula, `docs/LICENSES.md`'ye ekle. Ticari kullanıma uygun değilse dur ve kullanıcıya sor.
- [ ] **Step 2: Failing tests** (sahte model): `test_glossary_term_is_enforced` ("Vault" → "Kasa" sözlükteyse çıktıda "Kasa"); `test_empty_text_returns_empty`.
- [ ] **Step 3:** FAIL → uygula (terimleri çeviriden önce yer tutucuya, sonra karşılığına çevir) → PASS. Commit: `feat: translator wrapper with glossary`.

### Task 6: Tarama hattı

**Files:**
- Create: `dubly/scan.py`, `tests/test_scan.py`

**Interfaces:**
- Consumes: `Transcriber`, `Translator`, `IndexStore.add_line/has_digest`, `fingerprint`, `to_mono_16k`.
- Produces: `scan_folder(folder: str, store: IndexStore, transcriber: Transcriber, translator: Translator, on_progress: Callable[[int, int], None] = lambda done, total: None) -> ScanReport`; `@dataclass ScanReport(indexed: int, skipped_duplicate: int, skipped_no_speech: int, failed: int)`; desteklenen uzantılar `.wav .ogg .mp3 .flac`. Oyun motoru arşivlerinden çıkarma bu planın dışında (kullanıcı çıkarılmış klasörü verir).

- [ ] **Step 1: Failing tests** (sahte transcriber/translator, `tmp_path` ile sentetik wav dosyaları): `test_indexes_each_file_with_cue_and_hashes`; `test_resume_does_not_duplicate` (Review Focus 4: iki kez çalıştır, ikincide `indexed == 0`, depoda tek kayıt); `test_silence_and_non_english_are_skipped_without_cue` (Review Focus 5: `skipped_no_speech` artar, indekse kayıt yok, çökme yok); `test_corrupt_file_counts_as_failed_and_continues`; `test_progress_callback_reaches_total`.
- [ ] **Step 2:** FAIL → uygula: dosyayı oku, içerik özetini (`sha256`) çıkar, `has_digest` ise atla, ASR → çeviri → `fingerprint` → `add_line`. Bozuk dosya yakalanıp sayılır.
- [ ] **Step 3:** PASS. Commit: `feat: resumable scan pipeline`.

### Task 7: Loopback yakalama ve çalışma anı döngüsü

**Files:**
- Create: `dubly/capture.py`, `tests/test_capture.py`

**Interfaces:**
- Consumes: `Matcher` (Task 2), `IndexStore.get_cue`.
- Produces: `class LoopbackCapture: __init__(self, on_chunk: Callable[[np.ndarray], None], device: str | None = None)` ile `start()`/`stop()`; varsayılan çıkış cihazı değişirse yeniden bağlanır; `run_matching(chunks: Iterable[np.ndarray], matcher: Matcher, store: IndexStore, on_cue: Callable[[Cue], None]) -> None` (aynı replik art arda iki kez tetiklenmez; eşleşince `Matcher` sıfırlanır).

- [ ] **Step 1: Failing tests** `run_matching` için (yakalama cihazı olmadan, sentetik parçalarla): `test_emits_cue_once_per_line`; `test_no_cue_for_unmatched_audio`; `test_two_different_lines_emit_two_cues`.
- [ ] **Step 2:** FAIL → `run_matching` uygula → PASS.
- [ ] **Step 3:** `LoopbackCapture`'ı PyAudioWPatch ile uygula; cihaz değişikliğinde yeniden bağlanma ve hata günlüğü. Elle doğrulama: bir ses çalarken `python -m dubly run` ile parçaların geldiğini gör (otomatik test yok, donanım gerektirir).
- [ ] **Step 4:** Commit: `feat: loopback capture and matching loop`.

### Task 8: Altyazı zamanlaması ve katman penceresi

**Files:**
- Create: `dubly/overlay.py`, `tests/test_overlay.py`

**Interfaces:**
- Consumes: `Cue`.
- Produces: `class SubtitleTimeline: show(self, cue: Cue, now: float) -> None; current(self, now: float) -> str | None` (yeni replik gelince öncekini hemen değiştirir; `cue.duration_s + 0.5` sn sonra kaybolur); `class OverlayWindow(settings: OverlaySettings)` PySide6, çerçevesiz, her zaman üstte, `WS_EX_TRANSPARENT | WS_EX_LAYERED` ile tıklanamaz; `@dataclass OverlaySettings(font_size: int = 28, position: str = "bottom", color: str = "#ffffff")`; `detect_exclusive_fullscreen() -> bool` (ön plandaki pencere monitörü kaplıyor ve kenarlıksız değilse `True`).

- [ ] **Step 1: Failing tests** yalnızca `SubtitleTimeline` için: `test_text_visible_until_duration_plus_tail`; `test_new_cue_replaces_old_immediately`; `test_returns_none_before_any_cue`. Pencere testi otomatik değil.
- [ ] **Step 2:** FAIL → `SubtitleTimeline` uygula → PASS.
- [ ] **Step 3:** `OverlayWindow` uygula ve elle doğrula: kenarlıksız pencereli bir oyun/video üstünde altyazı görünüyor, fare tıklamaları alttaki pencereye geçiyor.
- [ ] **Step 4:** `detect_exclusive_fullscreen` için test: sahte pencere dikdörtgeni verip `True/False` döndüğünü doğrula (Review Focus 1: `True` ise `run` komutu kullanıcıya "pencereli tam ekran kullanın" uyarısı basar, çökmez).
- [ ] **Step 5:** Commit: `feat: subtitle timeline and overlay window`.

### Task 9: Komut satırı ve uçtan uca duman testi

**Files:**
- Create: `dubly/__main__.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1–8'in tümü.
- Produces: `python -m dubly scan <ses_klasörü> --index <dosya.db> [--glossary <json>]` ve `python -m dubly run --index <dosya.db>`; `main(argv: list[str]) -> int`.

- [ ] **Step 1: Failing test** `test_scan_then_match_end_to_end`: sentetik klasör + sahte model ile `scan`, ardından aynı sesi `run_matching`'e besle → beklenen Türkçe metin `on_cue` ile gelir.
- [ ] **Step 2:** FAIL → komutları bağla (`scan`: model yükle, ilerleme çubuğu; `run`: yakalamayı + katmanı başlat, Ctrl+C ile temiz kapan) → PASS.
- [ ] **Step 3:** Gerçek bir oyunla elle duman testi: bir oyunun çıkarılmış ses klasörünü tara; oyunu pencereli tam ekranda aç; altyazının gecikmesiz çıktığını ve müzik altında yanlış altyazı göstermediğini gözle kontrol et; sonuçları `docs/LICENSES.md` yanına `docs/SMOKE_TEST.md` olarak yaz (hangi oyun, eşleşme oranı, gözlenen sorunlar).
- [ ] **Step 3:** Commit: `feat: cli and end-to-end smoke test`.

---

## Self-review

- **Spec kapsamı:** altyazı tarama tabanlı (Task 6), oyun sırasında hafif eşleştirme (2, 7), katman (8), lisans doğrulama (4, 5), GPU'suz çalışma anı (Global Constraints, 7). Karakter sesi, TTS, dosya değiştirme ve canlı yedek mod bu planın dışında: Aşama 2/3 ve ayrı planlar.
- **Bilinen boşluk:** oyun motoru arşivlerinden ses çıkarma (Wwise/FMOD/Unity/Unreal) bu planda yok; kullanıcı çıkarılmış klasör verir. Çıkarma bağdaştırıcıları ayrı plan.
- **İmzalar tutarlı:** `lookup` biçimi Task 2 ve 3'te aynı; `Cue`/`MatchResult` Task 1'de tanımlı.

