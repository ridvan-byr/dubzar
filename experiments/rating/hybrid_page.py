"""Builds hybrid.html: the second model's translations of the routed lines, rated with the same rubric (own storage key)."""

import json
from pathlib import Path

from build_page import SINGLE

HERE = Path(__file__).parent
rows = [r for r in json.loads((HERE / "hybrid_lines.json").read_text(encoding="utf-8")) if r["routed"]]
data = [{"id": r["id"], "category": r["category"], "context": r["context"], "en": r["en"], "tr": r["hy"]} for r in rows]
page = (SINGLE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("rating_final", "rating_hybrid").replace("Son kontrol", "İkinci model").replace("(son kontrol)", "(ikinci model)"))
(HERE / "hybrid.html").write_text(page, encoding="utf-8")
print(len(data), "lines ->", HERE / "hybrid.html")
