import sqlite3
import threading
from collections import defaultdict

from dubzar.models import Cue

_LOOKUP_CHUNK = 500  # stays well under SQLite's bound-variable limit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lines (
    line_id    TEXT PRIMARY KEY,
    digest     TEXT NOT NULL UNIQUE,
    text_src   TEXT NOT NULL,
    text_tr    TEXT NOT NULL,
    duration_s REAL NOT NULL,
    speaker    TEXT
);
CREATE TABLE IF NOT EXISTS hashes (
    hash    INTEGER NOT NULL,
    line_id TEXT NOT NULL REFERENCES lines(line_id),
    anchor  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hashes_hash ON hashes(hash);
CREATE TABLE IF NOT EXISTS skipped (digest TEXT PRIMARY KEY);
"""


class IndexStore:
    """SQLite store of subtitle cues and their audio fingerprints.

    Safe to share between threads (``run`` opens it on the main thread and
    matches on a worker thread): every operation holds one lock.
    """

    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def has_digest(self, digest: str) -> bool:
        with self._lock:
            row = self._db.execute("SELECT 1 FROM lines WHERE digest = ?", (digest,)).fetchone()
        return row is not None

    def add_line(self, cue: Cue, hashes: list[tuple[int, int]], content_digest: str) -> bool:
        """Store a line and its ``(hash, anchor_frame)`` pairs.

        Returns False without storing anything when audio with the same
        ``content_digest`` is already indexed.
        """
        with self._lock:
            if self.has_digest(content_digest):
                return False
            with self._db:  # one transaction: a line never exists without its hashes
                self._db.execute(
                    "INSERT INTO lines VALUES (?, ?, ?, ?, ?, ?)",
                    (cue.line_id, content_digest, cue.text_src, cue.text_tr,
                     cue.duration_s, cue.speaker),
                )
                self._db.executemany(
                    "INSERT INTO hashes VALUES (?, ?, ?)",
                    [(h, cue.line_id, anchor) for h, anchor in hashes],
                )
        return True

    def add_skipped(self, digest: str) -> None:
        """Remember audio that had no usable speech so a re-run does not transcribe it again."""
        with self._lock, self._db:
            self._db.execute("INSERT OR IGNORE INTO skipped VALUES (?)", (digest,))

    def is_skipped(self, digest: str) -> bool:
        with self._lock:
            row = self._db.execute("SELECT 1 FROM skipped WHERE digest = ?", (digest,)).fetchone()
        return row is not None

    def count_lines(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM lines").fetchone()[0]

    def get_cue(self, line_id: str) -> Cue | None:
        with self._lock:
            row = self._db.execute(
                "SELECT line_id, text_src, text_tr, duration_s, speaker FROM lines WHERE line_id = ?",
                (line_id,),
            ).fetchone()
        return Cue(*row) if row else None

    def lookup(self, hashes: list[int]) -> list[tuple[str, int, int]]:
        """Return ``(line_id, line_anchor_frame, query_hash_index)`` for each hit."""
        positions: dict[int, list[int]] = defaultdict(list)
        for qi, h in enumerate(hashes):
            positions[h].append(qi)
        distinct = list(positions)
        found: list[tuple[str, int, int]] = []
        with self._lock:
            for start in range(0, len(distinct), _LOOKUP_CHUNK):
                chunk = distinct[start:start + _LOOKUP_CHUNK]
                marks = ",".join("?" * len(chunk))
                rows = self._db.execute(
                    f"SELECT hash, line_id, anchor FROM hashes WHERE hash IN ({marks})", chunk
                ).fetchall()
                for h, line_id, anchor in rows:
                    found.extend((line_id, anchor, qi) for qi in positions[h])
        return found
