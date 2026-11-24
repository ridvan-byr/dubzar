"""Keeps the progress page current while the data batches are written: counts the pairs in training/gen."""
import time
from pathlib import Path

from status import log, stage

GEN = Path(__file__).parent / "gen"
TARGET = 4800
last = -1
while True:
    n = sum(sum(1 for l in p.read_text(encoding="utf-8").splitlines() if "|||" in l)
            for p in GEN.glob("*_p*.txt"))
    if n != last:
        stage("kaynak", percent=min(100, 100 * n / TARGET), detail=f"{n} / ~{TARGET} çift yazıldı (8 yazar ajan)")
        last = n
    time.sleep(20)
