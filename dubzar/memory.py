"""Translation memory: a line translated once is never translated again (instant, no model, no processor load)."""

import re
import sqlite3
import threading
from pathlib import Path
from typing import Sequence

from dubzar.translate import Translator


def normalize_key(text: str) -> str:
    """What makes two readings of the same subtitle equal: OCR mixes up I, l, 1 and |, and punctuation, case and
    spacing differ between frames."""
    text = re.sub(r"[il1|]", "l", text.lower())   # lower first: a capital I read as l must equal a real i
    return re.sub(r"[\W_]+", " ", text).strip()


class TranslationMemory:
    """SQLite-backed, thread-safe. ``namespace`` ties entries to the model and glossary that produced them, so a
    better model later does not serve old translations."""

    def __init__(self, path: str | Path, namespace: str):
        self._namespace = namespace
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS translations (ns TEXT NOT NULL, key TEXT NOT NULL, "
                         "source TEXT NOT NULL, translated TEXT NOT NULL, PRIMARY KEY (ns, key))")
        self._db.commit()

    def get(self, text: str) -> str | None:
        key = normalize_key(text)
        if not key:
            return None
        with self._lock:
            row = self._db.execute("SELECT translated FROM translations WHERE ns = ? AND key = ?",
                                   (self._namespace, key)).fetchone()
        return row[0] if row else None

    def put(self, text: str, translated: str) -> None:
        key = normalize_key(text)
        if not key or not translated.strip():
            return
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO translations (ns, key, source, translated) VALUES (?, ?, ?, ?)",
                             (self._namespace, key, text.strip(), translated.strip()))
            self._db.commit()

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM translations WHERE ns = ?", (self._namespace,)).fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._db.close()


class MemoizedTranslator:
    def __init__(self, inner: Translator, memory: TranslationMemory):
        self._inner = inner
        self._memory = memory

    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        remembered = self._memory.get(text)
        if remembered is not None:
            return remembered
        translated = self._inner.translate(text, context)
        self._memory.put(text, translated)
        return translated
