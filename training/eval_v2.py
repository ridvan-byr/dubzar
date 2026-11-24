"""Converts the fine-tuned model to CT2 int8, translates the 200 final lines with the current and the tuned model, and builds a rating page
for the lines where the tuned output differs (the rest keep their earlier rating).

    python training/eval_v2.py models_ft/opus-mt-en-tr-games-v2
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "rating"))
sys.path.insert(0, str(Path(__file__).parent))

from status import log, stage  # noqa: E402


def translate_all(lines, local_app_data=None):
    if local_app_data:
        os.environ["LOCALAPPDATA"] = local_app_data
    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=8)
    translator.load()
    return [translator.translate(en) for en in lines]


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    tuned_dir = Path(sys.argv[1]).resolve()
    from final_set import FINAL

    from dubzar.translate import CT2_FOLDER_NAME

    stage("cevirme", percent=5, detail="model int8 biçimine çevriliyor")
    sandbox = Path(tempfile.mkdtemp(prefix="dubzar_v2_"))
    target = sandbox / "Dubzar" / "models" / CT2_FOLDER_NAME
    target.parent.mkdir(parents=True)
    import ctranslate2

    ctranslate2.converters.TransformersConverter(str(tuned_dir)).convert(str(target), quantization="int8")
    for name in ("source.spm", "target.spm"):
        shutil.copy2(tuned_dir / name, target / name)
    stage("cevirme", percent=100, detail="int8 model hazır")

    lines = [en for _, _, en in FINAL]
    stage("olcum", percent=10, detail="200 satır şimdiki modelle çevriliyor")
    old = translate_all(lines)                       # the current model with the current rules
    stage("olcum", percent=50, detail="200 satır ince ayarlı modelle çevriliyor")
    new = translate_all(lines, str(sandbox))
    rows = [{"id": i, "category": c, "context": ctx, "en": en, "old": o, "tr": n}
            for i, ((c, ctx, en), o, n) in enumerate(zip(FINAL, old, new), 1)]
    out = Path(__file__).parents[1] / "experiments" / "rating"
    tag = sys.argv[2] if len(sys.argv) > 2 else "v2"
    changed = [r for r in rows if r["old"] != r["tr"]]
    if tag != "v2":   # only lines whose output no earlier rating covers need a new rating
        seen = set()
        for earlier in ("v2", "v3"):   # every output an earlier page already covered has a rating
            f = out / f"{earlier}_lines.json"
            if f.exists() and earlier != tag:
                for r in json.loads(f.read_text(encoding="utf-8")):
                    seen |= {(r["id"], r["tr"]), (r["id"], r["old"])}
        changed = [r for r in rows if (r["id"], r["tr"]) not in seen]
    (out / f"{tag}_lines.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    from build_page import SINGLE

    data = [{k: r[k] for k in ("id", "category", "context", "en", "tr")} for r in changed]
    page = (SINGLE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("rating_final", f"rating_{tag}").replace("Son kontrol", "İnce ayarlı model").replace("(son kontrol)", "(ince ayarlı model)"))
    (out / f"{tag}.html").write_text(page, encoding="utf-8")
    stage("olcum", percent=100, detail=f"{len(changed)} / {len(rows)} satır değişti; puan sayfası hazır")
    log(f"{len(changed)} satır değişti; sayfa: http://127.0.0.1:8125/")
    print(len(changed), "changed of", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
