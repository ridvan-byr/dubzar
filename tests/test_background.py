import os
import sys
import threading
import time

import numpy as np
import pytest

from dubzar.background import BackgroundScanner, is_process_running
from dubzar.index import IndexStore
from dubzar.scan import scan_folder
from test_fingerprint import SR, synth_line
from test_scan import FakeTranscriber, PrefixTranslator, write_wav


@pytest.fixture
def audio_dir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    return d


@pytest.fixture
def store(tmp_path):
    s = IndexStore(str(tmp_path / "game.db"))
    yield s
    s.close()


def wait_until(condition, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def three_files(audio_dir):
    for i, seed in enumerate((1, 2, 3)):
        write_wav(audio_dir / f"line{i}.wav", synth_line(seed, 1.5))


def test_scan_pauses_while_should_pause_is_true_and_resumes(audio_dir, store):
    # Review Focus 5 (pause side): the game is running, so the scan must hold back.
    three_files(audio_dir)
    paused = threading.Event()
    paused.set()
    worker = threading.Thread(target=lambda: scan_folder(
        str(audio_dir), store, FakeTranscriber(), PrefixTranslator(),
        should_pause=paused.is_set, pause_poll_s=0.01))
    worker.start()

    time.sleep(0.3)
    assert store.count_lines() == 0  # nothing processed while paused

    paused.clear()
    worker.join(10)

    assert store.count_lines() == 3


def test_natural_order_scans_mission2_before_mission10(audio_dir, store):
    write_wav(audio_dir / "mission10.wav", synth_line(1, 1.5))
    write_wav(audio_dir / "mission2.wav", synth_line(2, 1.0))
    order: list[float] = []

    class Recording(FakeTranscriber):
        def transcribe(self, samples):
            order.append(round(len(samples) / SR, 1))
            return super().transcribe(samples)

    scan_folder(str(audio_dir), store, Recording(), PrefixTranslator())

    assert order == [1.0, 1.5]  # mission2 (1.0 s) first, then mission10 (1.5 s)


def test_stop_event_interrupts_cleanly_and_a_restart_continues(audio_dir, store):
    # Review Focus 5 (restart side): nothing lost, nothing duplicated.
    three_files(audio_dir)
    stop = threading.Event()

    first = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator(),
                        on_progress=lambda done, total: stop.set() if done == 1 else None, stop_event=stop)
    second = scan_folder(str(audio_dir), store, FakeTranscriber(), PrefixTranslator())

    assert first.indexed == 1
    assert second.indexed == 2 and second.skipped_duplicate == 1
    assert store.count_lines() == 3


def make_scanner(audio_dir, tmp_path, game_exe, is_running, progress=None):
    return BackgroundScanner(
        str(audio_dir), str(tmp_path / "game.db"),
        make_transcriber=FakeTranscriber, make_translator=PrefixTranslator,
        game_exe=game_exe, on_progress=progress or (lambda done, total: None),
        is_running=is_running, poll_s=0.01)


def test_background_scanner_does_nothing_without_a_game_exe_setting(audio_dir, tmp_path):
    three_files(audio_dir)
    scanner = make_scanner(audio_dir, tmp_path, None, lambda name: False)

    scanner.start()

    assert not scanner.running
    assert scanner.progress == (0, 0)


def test_background_scanner_waits_while_the_game_is_running_then_finishes(audio_dir, tmp_path):
    three_files(audio_dir)
    game_running = threading.Event()
    game_running.set()
    seen: list[tuple[int, int]] = []
    scanner = make_scanner(audio_dir, tmp_path, "GTA5.exe", lambda name: game_running.is_set() and name == "GTA5.exe",
                           progress=lambda done, total: seen.append((done, total)))

    scanner.start()
    time.sleep(0.3)
    assert scanner.progress[0] == 0 and scanner.running  # waiting, not scanning

    game_running.clear()
    assert wait_until(lambda: scanner.progress == (3, 3))
    scanner.stop()

    assert seen[-1] == (3, 3)
    store = IndexStore(str(tmp_path / "game.db"))
    assert store.count_lines() == 3
    store.close()


def test_stop_ends_the_background_thread_promptly(audio_dir, tmp_path):
    three_files(audio_dir)
    scanner = make_scanner(audio_dir, tmp_path, "GTA5.exe", lambda name: True)  # the game never closes

    scanner.start()
    started = time.monotonic()
    scanner.stop()

    assert time.monotonic() - started < 2.0
    assert not scanner.running


def test_is_process_running_finds_this_python_process():
    assert is_process_running(os.path.basename(sys.executable))
    assert not is_process_running("definitely-not-a-running-game-12345.exe")
