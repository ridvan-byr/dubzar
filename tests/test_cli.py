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
                    on_cue=cues.append)

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


def test_run_requires_an_existing_index_file(tmp_path, capsys):
    missing = tmp_path / "missing.db"

    code = main(["run", "--index", str(missing)], audio_chunks=iter([]), on_cue=lambda c: None)

    assert code == 2
    assert not missing.exists()  # must not silently create an empty index
    assert "scan" in capsys.readouterr().err


def test_run_with_empty_index_tells_user_to_scan_first(tmp_path, capsys):
    db = tmp_path / "empty.db"
    IndexStore(str(db)).close()

    code = main(["run", "--index", str(db)], audio_chunks=iter([]), on_cue=lambda c: None)

    assert code == 2
    assert "scan" in capsys.readouterr().err


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
