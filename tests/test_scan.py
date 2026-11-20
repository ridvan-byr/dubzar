import numpy as np
import pytest
from scipy.io import wavfile

from dubzar.asr import Transcription
from dubzar.fingerprint import Matcher
from dubzar.index import IndexStore
from dubzar.scan import ScanReport, scan_folder
from test_fingerprint import SR, synth_line


class FakeTranscriber:
    def __init__(self, result: Transcription | None = Transcription("hello", "en", 3.0)):
        self.result = result
        self.calls = 0

    def transcribe(self, samples):
        self.calls += 1
        return self.result


class FakeTranslator:
    def __init__(self, output: str):
        self.output = output

    def translate(self, text, context=()):
        return self.output


class PrefixTranslator:
    def translate(self, text, context=()):
        return "TR:" + text


@pytest.fixture
def audio_dir(tmp_path):
    d = tmp_path / "audio"
    (d / "sub").mkdir(parents=True)
    return d


@pytest.fixture
def store(tmp_path):
    s = IndexStore(str(tmp_path / "game.db"))
    yield s
    s.close()


def write_wav(path, samples):
    wavfile.write(str(path), SR, samples.astype(np.float32))


def test_indexes_each_file_with_cue_and_hashes(audio_dir, store):
    write_wav(audio_dir / "a.wav", synth_line(1))
    write_wav(audio_dir / "b.wav", synth_line(2))
    write_wav(audio_dir / "sub" / "c.wav", synth_line(3))

    report = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator())

    assert report == ScanReport(indexed=3, skipped_duplicate=0, skipped_no_speech=0, failed=0)
    cue = store.get_cue("a.wav")
    assert (cue.text_src, cue.text_tr, cue.duration_s) == ("hello", "TR:hello", 3.0)
    assert store.get_cue("sub/c.wav") is not None
    result = Matcher(store.lookup).feed(synth_line(2)[: int(0.3 * SR)])
    assert result is not None and result.line_id == "b.wav"


def test_resume_does_not_duplicate(audio_dir, store):
    # Review Focus 4: an interrupted scan is simply run again.
    write_wav(audio_dir / "a.wav", synth_line(1))
    write_wav(audio_dir / "b.wav", synth_line(2))
    transcriber = FakeTranscriber()
    scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())

    second = scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())

    assert second.indexed == 0
    assert second.skipped_duplicate == 2
    assert transcriber.calls == 2  # nothing was transcribed twice


def test_same_audio_in_two_files_is_indexed_once(audio_dir, store):
    # Review Focus 3
    write_wav(audio_dir / "a.wav", synth_line(1))
    write_wav(audio_dir / "copy_of_a.wav", synth_line(1))

    report = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator())

    assert (report.indexed, report.skipped_duplicate) == (1, 1)


def test_silence_and_non_english_are_skipped_without_cue(audio_dir, store):
    # Review Focus 5
    write_wav(audio_dir / "silent.wav", np.zeros(SR, dtype=np.float32))
    write_wav(audio_dir / "turkish.wav", synth_line(4))

    report = scan_folder(str(audio_dir), store, FakeTranscriber(result=None), PrefixTranslator())

    assert report == ScanReport(indexed=0, skipped_duplicate=0, skipped_no_speech=2, failed=0)
    assert store.get_cue("silent.wav") is None
    assert store.get_cue("turkish.wav") is None


def test_empty_translation_is_not_indexed(audio_dir, store):
    write_wav(audio_dir / "a.wav", synth_line(1))

    report = scan_folder(str(audio_dir), store, FakeTranscriber(), FakeTranslator(output=""))

    assert (report.indexed, report.skipped_no_speech) == (0, 1)
    assert store.get_cue("a.wav") is None


def test_corrupt_file_counts_as_failed_and_continues(audio_dir, store):
    (audio_dir / "bad.wav").write_bytes(b"this is not audio")
    write_wav(audio_dir / "good.wav", synth_line(1))

    report = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator())

    assert (report.indexed, report.failed) == (1, 1)


def test_transcriber_crash_counts_as_failed_and_continues(audio_dir, store):
    write_wav(audio_dir / "a.wav", synth_line(1))
    write_wav(audio_dir / "b.wav", synth_line(2))

    class FlakyTranscriber(FakeTranscriber):
        def transcribe(self, samples):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("model crashed")
            return self.result

    report = scan_folder(str(audio_dir), store, FlakyTranscriber(), PrefixTranslator())

    assert (report.indexed, report.failed) == (1, 1)


def test_progress_callback_reaches_total_and_ignores_non_audio(audio_dir, store):
    write_wav(audio_dir / "a.wav", synth_line(1))
    write_wav(audio_dir / "sub" / "b.wav", synth_line(2))
    (audio_dir / "notes.txt").write_text("not audio")
    calls: list[tuple[int, int]] = []

    scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator(),
                on_progress=lambda done, total: calls.append((done, total)))

    assert calls == [(1, 2), (2, 2)]


@pytest.mark.parametrize("ext", [".flac", ".ogg", ".mp3"])
def test_reads_compressed_formats(audio_dir, store, ext):
    import soundfile as sf

    sf.write(str(audio_dir / f"voice{ext}"), synth_line(1), SR)

    report = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator())

    assert (report.indexed, report.failed) == (1, 0)
    assert store.get_cue(f"voice{ext}") is not None


def test_no_speech_files_are_not_transcribed_again_on_rerun(audio_dir, store):
    write_wav(audio_dir / "grunt.wav", synth_line(1))
    transcriber = FakeTranscriber(result=None)
    scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())

    second = scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())

    assert transcriber.calls == 1
    assert second.skipped_no_speech == 1


def test_retry_skipped_transcribes_them_again(audio_dir, store):
    write_wav(audio_dir / "grunt.wav", synth_line(1))
    transcriber = FakeTranscriber(result=None)
    scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())
    transcriber.result = Transcription("hello", "en", 3.0)  # e.g. a better model now hears speech

    report = scan_folder(str(audio_dir), store, transcriber, PrefixTranslator(), retry_skipped=True)

    assert transcriber.calls == 2
    assert report.indexed == 1
    assert store.get_cue("grunt.wav") is not None


def test_failed_files_are_retried_on_rerun(audio_dir, store):
    write_wav(audio_dir / "a.wav", synth_line(1))

    class FlakyOnce(FakeTranscriber):
        def transcribe(self, samples):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("model crashed")
            return self.result

    transcriber = FlakyOnce()
    first = scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())
    second = scan_folder(str(audio_dir), store, transcriber, PrefixTranslator())

    assert (first.failed, second.indexed) == (1, 1)
