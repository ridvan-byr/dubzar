"""Translates the 150 hold-out lines with the current and the tuned model and builds one blind rating page with every distinct output
(an output both models give is rated once).

    python training/eval_holdout.py models_ft/opus-mt-en-tr-games-v4 v4
"""
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "rating"))
sys.path.insert(0, str(Path(__file__).parent))
from eval_v2 import translate_all  # noqa: E402
from status import log, stage  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    tuned = Path(sys.argv[1]).resolve()
    tag = sys.argv[2]
    from dubzar.translate import CT2_FOLDER_NAME
    import ctranslate2

    rows = [l.split(" ||| ") for l in (Path(__file__).parent / "holdout_v4.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = [r[0] for r in rows]
    sandbox = Path(tempfile.mkdtemp(prefix="dubzar_ho_"))
    target = sandbox / "Dubzar" / "models" / CT2_FOLDER_NAME
    target.parent.mkdir(parents=True)
    ctranslate2.converters.TransformersConverter(str(tuned)).convert(str(target), quantization="int8")
    for name in ("source.spm", "target.spm"):
        shutil.copy2(tuned / name, target / name)
    old = translate_all(lines)
    new = translate_all(lines, str(sandbox))
    items = []
    for i, (r, o, n) in enumerate(zip(rows, old, new)):
        items.append({"id": 2 * i + 1, "category": r[2], "context": "", "en": r[0], "tr": o, "model": "old"})
        if n != o:
            items.append({"id": 2 * i + 2, "category": r[2], "context": "", "en": r[0], "tr": n, "model": "new"})
    random.Random(5).shuffle(items)
    out = ROOT / "experiments" / "rating"
    (out / f"holdout_{tag}_lines.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    from build_page import SINGLE

    data = [{k: x[k] for k in ("id", "category", "context", "en", "tr")} for x in items]
    page = (SINGLE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("rating_final", f"rating_holdout_{tag}")
            .replace("Son kontrol", "Yeni satırlar").replace("(son kontrol)", "(yeni satırlar)"))
    (out / f"holdout_{tag}.html").write_text(page, encoding="utf-8")
    print(len(items), "outputs to rate;", sum(a != b for a, b in zip(old, new)), "of", len(lines), "differ")
    return 0


raise SystemExit(main())
