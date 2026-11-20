import pytest

from dubzar.fingerprint import Matcher, fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from test_fingerprint import LINES, SR


@pytest.fixture
def store(tmp_path):
    s = IndexStore(str(tmp_path / "game.db"))
    yield s
    s.close()


def test_add_and_get_cue(store):
    cue = Cue("a1", "hello", "merhaba", 1.5, speaker="npc")

    added = store.add_line(cue, [(10, 1), (11, 2)], content_digest="d1")

    assert added is True
    assert store.get_cue("a1") == cue
    assert store.get_cue("missing") is None


def test_duplicate_digest_is_indexed_once(store):
    # Review Focus 3: the same audio under two names must not produce two lines.
    first = Cue("a1", "hello", "merhaba", 1.5)
    second = Cue("a2", "hello", "merhaba", 1.5)

    assert store.add_line(first, [(10, 1)], content_digest="same") is True
    assert store.add_line(second, [(10, 1)], content_digest="same") is False

    assert store.has_digest("same")
    assert store.get_cue("a2") is None
    assert [r[0] for r in store.lookup([10])] == ["a1"]


def test_lookup_returns_line_anchor_and_query_index(store):
    store.add_line(Cue("a1", "x", "y", 1.0), [(10, 5), (11, 7)], "d1")
    store.add_line(Cue("b1", "x", "y", 1.0), [(10, 9)], "d2")

    rows = store.lookup([11, 10, 10, 99])

    assert sorted(rows) == [
        ("a1", 5, 1), ("a1", 5, 2),
        ("a1", 7, 0),
        ("b1", 9, 1), ("b1", 9, 2),
    ]


def test_lookup_handles_more_hashes_than_sqlite_variable_limit(store):
    store.add_line(Cue("a1", "x", "y", 1.0), [(5, 0)], "d1")

    rows = store.lookup(list(range(5, 5 + 5000)))

    assert rows == [("a1", 0, 0)]


def test_data_survives_reopening_the_file(tmp_path):
    path = str(tmp_path / "game.db")
    first = IndexStore(path)
    first.add_line(Cue("a1", "x", "y", 1.0), [(10, 1)], "d1")
    first.close()

    second = IndexStore(path)

    assert second.get_cue("a1") is not None
    assert second.has_digest("d1")
    second.close()


def test_matcher_works_on_top_of_the_store(store):
    for line_id, samples in LINES.items():
        store.add_line(Cue(line_id, "x", "y", 3.0), fingerprint(samples), f"digest-{line_id}")
    matcher = Matcher(store.lookup)

    result = matcher.feed(LINES["B"][: int(0.3 * SR)])

    assert result is not None and result.line_id == "B"


def test_count_lines(store):
    assert store.count_lines() == 0

    store.add_line(Cue("a1", "x", "y", 1.0), [(10, 1)], "d1")
    store.add_line(Cue("a2", "x", "y", 1.0), [(10, 1)], "d1")  # duplicate, ignored

    assert store.count_lines() == 1


def test_store_can_be_used_from_another_thread(store):
    # `run` opens the index on the main thread but matches on a worker thread.
    import threading

    store.add_line(Cue("a1", "x", "y", 1.0), [(10, 1)], "d1")
    seen: list = []

    def worker():
        seen.append(store.lookup([10]))
        seen.append(store.get_cue("a1"))

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert seen[0] == [("a1", 1, 0)]
    assert seen[1] is not None


def test_skipped_digests_are_remembered_across_reopening(tmp_path):
    path = str(tmp_path / "game.db")
    first = IndexStore(path)
    assert not first.is_skipped("grunt")
    first.add_skipped("grunt")
    first.add_skipped("grunt")  # recording twice is harmless
    first.close()

    second = IndexStore(path)

    assert second.is_skipped("grunt")
    assert not second.has_digest("grunt")  # skipped is not the same as indexed
    assert second.count_lines() == 0
    second.close()


def test_remove_line_deletes_the_cue_its_hashes_and_frees_the_digest(store):
    store.add_line(Cue("a1", "x", "y", 1.0), [(10, 1)], "d1")
    store.add_line(Cue("b1", "x", "y", 1.0), [(10, 2)], "d2")

    assert store.remove_line("a1") is True

    assert store.get_cue("a1") is None
    assert [r[0] for r in store.lookup([10])] == ["b1"]
    assert not store.has_digest("d1")  # the same audio can be indexed again later
    assert store.remove_line("a1") is False  # already gone
