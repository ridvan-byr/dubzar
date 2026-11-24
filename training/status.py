"""Progress reporting for the training pipeline: every step writes training/status.json, the page served by progress_server.py shows it.

    from status import stage, log
    stage("egitim", "Eğitim", percent=40, detail="tur 2 / 5")
    log("kayıp 1.23")
"""

import json
import time
from pathlib import Path

PATH = Path(__file__).parent / "status.json"

STAGES = [("arastirma", "Deyim ve argo araştırması"), ("kaynak", "İngilizce kaynak satırlar"), ("hedef", "Türkçe hedef çeviriler"),
          ("egitim", "İnce ayar (eğitim)"), ("cevirme", "CT2 int8'e çevirme"), ("olcum", "Yeni satırlar ve puan sayfası")]


def _read() -> dict:
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"stages": {k: {"title": t, "percent": 0, "state": "bekliyor", "detail": ""} for k, t in STAGES}, "log": [], "updated": 0}


def _write(data: dict) -> None:
    data["updated"] = time.time()
    temp = PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(PATH)


def stage(key: str, title: str | None = None, percent: float | None = None, detail: str | None = None, state: str | None = None) -> None:
    data = _read()
    item = data["stages"].setdefault(key, {"title": title or key, "percent": 0, "state": "bekliyor", "detail": ""})
    if percent is not None:
        item["percent"] = max(0, min(100, percent))
        item["state"] = "bitti" if item["percent"] >= 100 else "sürüyor"
    if detail is not None:
        item["detail"] = detail
    if state:
        item["state"] = state
    _write(data)


def log(message: str) -> None:
    data = _read()
    data["log"] = (data["log"] + [f"{time.strftime('%H:%M:%S')}  {message}"])[-40:]
    _write(data)
