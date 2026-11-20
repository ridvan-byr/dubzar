import json

import pytest

from dubzar.cli import main
from dubzar.index import IndexStore
from dubzar.models import Cue
from test_fingerprint import SR, synth_line
from test_scan import FakeTranscriber, PrefixTranslator, write_wav


@pytest.fixture
def audio_dir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    write_wav(d / "a.wav", synth_line(1))
    write_wav(d / "b.wav", synth_line(2))
    return d


def chunks(audio, size=1600):
    for i in range(0, len(audio), size):
        yield audio[i : i + size]


def test_scan_then_match_end_to_end(audio_dir, tmp_path):
    db = str(tmp_path / "game.db")

    code = main(["scan", str(audio_dir), "--index", db],
                transcriber=FakeTranscriber(), translator=PrefixTranslator())
    cues: list[Cue] = []
    run_code = main(["run", "--index", db], audio_chunks=chunks(synth_line(2)[:SR]),
                    on_cue=cues.append, transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert (code, run_code) == (0, 0)
    assert [(c.line_id, c.text_tr) for c in cues] == [("b.wav", "TR:hello")]


def test_scan_missing_folder_returns_error(tmp_path, capsys):
    code = main(["scan", str(tmp_path / "nope"), "--index", str(tmp_path / "g.db")],
                transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert code == 2
    assert "nope" in capsys.readouterr().err


def test_glossary_must_be_a_json_object(audio_dir, tmp_path, capsys):
    glossary = tmp_path / "glossary.json"
    glossary.write_text(json.dumps(["not", "an", "object"]))

    code = main(["scan", str(audio_dir), "--index", str(tmp_path / "g.db"),
                 "--glossary", str(glossary)])

    assert code == 2
    assert "glossary" in capsys.readouterr().err.lower()


def test_run_rejects_an_invalid_screen_setting(tmp_path, capsys):
    db = tmp_path / "game.db"
    store = IndexStore(str(db))
    store.add_line(Cue("a", "x", "y", 1.0), [(1, 1)], "d")
    store.close()

    code = main(["run", "--index", str(db), "--screen", "left"],
                audio_chunks=iter([]), on_cue=lambda c: None)

    assert code == 2
    assert "screen" in capsys.readouterr().err.lower()


def test_scan_retry_skipped_flag_reprocesses_skipped_files(audio_dir, tmp_path):
    from dubzar.asr import Transcription

    db = str(tmp_path / "game.db")
    deaf = FakeTranscriber(result=None)
    main(["scan", str(audio_dir), "--index", db], transcriber=deaf, translator=PrefixTranslator())
    hearing = FakeTranscriber(result=Transcription("hello", "en", 3.0))

    main(["scan", str(audio_dir), "--index", db], transcriber=hearing, translator=PrefixTranslator())
    assert hearing.calls == 0  # remembered as skipped
    main(["scan", str(audio_dir), "--index", db, "--retry-skipped"],
         transcriber=hearing, translator=PrefixTranslator())

    assert hearing.calls == 2


# --- run: live mode -------------------------------------------------------------------------
import numpy as np  # noqa: E402

from dubzar.errors import ModelMissingError  # noqa: E402
from test_fingerprint import synth_line as _line  # noqa: E402


def _line_with_silence(seed: int):
    sil = np.zeros(int(SR * 1.0), dtype=np.float32)
    return np.concatenate([np.zeros(int(SR * 0.3), dtype=np.float32), _line(seed, 1.5), sil])


def test_run_creates_an_empty_index_instead_of_failing(tmp_path):
    db = tmp_path / "new.db"

    code = main(["run", "--index", str(db)], audio_chunks=iter([]), on_cue=lambda c: None,
                transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert code == 0 and db.exists()


def test_run_recognises_an_unknown_line_live_and_shows_the_turkish_subtitle(tmp_path):
    cues: list[Cue] = []

    code = main(["run", "--index", str(tmp_path / "live.db")], audio_chunks=chunks(_line_with_silence(5)),
                on_cue=cues.append, transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert code == 0
    assert [c.text_tr for c in cues] == ["TR:hello"] and cues[0].line_id.startswith("live/")


def test_a_second_run_finds_the_line_learned_by_the_first(tmp_path):
    db = str(tmp_path / "live.db")
    main(["run", "--index", db], audio_chunks=chunks(_line_with_silence(5)), on_cue=lambda c: None,
         transcriber=FakeTranscriber(), translator=PrefixTranslator())
    transcriber = FakeTranscriber()
    cues: list[Cue] = []

    main(["run", "--index", db], audio_chunks=chunks(_line_with_silence(5)), on_cue=cues.append,
         transcriber=transcriber, translator=PrefixTranslator())

    assert len(cues) == 1 and transcriber.calls == 0  # known now: no recognition needed


def test_game_exe_without_audio_dir_is_rejected(tmp_path, capsys):
    code = main(["run", "--index", str(tmp_path / "g.db"), "--game-exe", "GTA5.exe"],
                audio_chunks=iter([]), on_cue=lambda c: None,
                transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert code == 2 and "audio-dir" in capsys.readouterr().err


def test_audio_dir_without_a_game_exe_is_rejected(tmp_path, audio_dir, capsys):
    code = main(["run", "--index", str(tmp_path / "g.db"), "--audio-dir", str(audio_dir)],
                audio_chunks=iter([]), on_cue=lambda c: None,
                transcriber=FakeTranscriber(), translator=PrefixTranslator())

    assert code == 2 and "game-exe" in capsys.readouterr().err


def test_run_reports_a_missing_model_instead_of_downloading_it(tmp_path, monkeypatch, capsys):
    import dubzar.cli as cli

    class Missing:
        def __init__(self, **kwargs):
            pass

        def load(self):
            raise ModelMissingError("Whisper modeli 'tiny' bu bilgisayarda yok. İndirmek için --allow-download")

    monkeypatch.setattr(cli, "WhisperTranscriber", Missing)

    code = main(["run", "--index", str(tmp_path / "g.db")], audio_chunks=iter([]), on_cue=lambda c: None)

    assert code == 2 and "--allow-download" in capsys.readouterr().err


def test_models_are_only_allowed_to_download_when_asked(tmp_path, monkeypatch):
    import dubzar.cli as cli

    seen: list[tuple[str, bool]] = []

    class Recording:
        def __init__(self, **kwargs):
            seen.append((type(self).__name__, kwargs.get("allow_download")))

        def load(self):
            pass

        def transcribe(self, samples):
            return None

        def translate(self, text, context=()):
            return text

    class FakeWhisper(Recording):
        pass

    class FakeOpus(Recording):
        pass

    monkeypatch.setattr(cli, "WhisperTranscriber", FakeWhisper)
    monkeypatch.setattr(cli, "OpusMtTranslator", FakeOpus)

    main(["run", "--index", str(tmp_path / "a.db")], audio_chunks=iter([]), on_cue=lambda c: None)
    main(["run", "--index", str(tmp_path / "b.db"), "--allow-download"], audio_chunks=iter([]), on_cue=lambda c: None)

    assert seen == [("FakeWhisper", False), ("FakeOpus", False), ("FakeWhisper", True), ("FakeOpus", True)]


def test_run_limits_cpu_threads_so_the_game_keeps_its_cores(tmp_path, monkeypatch):
    import dubzar.cli as cli

    seen: dict = {}

    class Fake:
        def __init__(self, **kwargs):
            seen[type(self).__name__] = kwargs

        def load(self):
            pass

        def transcribe(self, samples):
            return None

        def translate(self, text, context=()):
            return text

    class W(Fake):
        pass

    class T(Fake):
        pass

    monkeypatch.setattr(cli, "WhisperTranscriber", W)
    monkeypatch.setattr(cli, "OpusMtTranslator", T)

    main(["run", "--index", str(tmp_path / "a.db")], audio_chunks=iter([]), on_cue=lambda c: None)
    assert seen["W"]["cpu_threads"] == 2 and seen["T"]["threads"] == 2

    main(["run", "--index", str(tmp_path / "b.db"), "--cpu-threads", "4"], audio_chunks=iter([]), on_cue=lambda c: None)
    assert seen["W"]["cpu_threads"] == 4 and seen["T"]["threads"] == 4


def test_scan_uses_all_cores_by_default_because_the_game_is_closed(tmp_path, audio_dir, monkeypatch):
    import dubzar.cli as cli

    seen: dict = {}

    class Fake:
        def __init__(self, **kwargs):
            seen[type(self).__name__] = kwargs

        def load(self):
            pass

        def transcribe(self, samples):
            return None

        def translate(self, text, context=()):
            return text

    class W(Fake):
        pass

    class T(Fake):
        pass

    monkeypatch.setattr(cli, "WhisperTranscriber", W)
    monkeypatch.setattr(cli, "OpusMtTranslator", T)

    main(["scan", str(audio_dir), "--index", str(tmp_path / "s.db")])

    assert seen["W"]["cpu_threads"] == 0 and seen["T"]["threads"] == 0
