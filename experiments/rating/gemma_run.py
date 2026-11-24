"""Gemma 4 12B (llama.cpp server on 8099) on the 200 final lines and the 150 hold-out lines. Writes gemma_lines.json."""
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from final_set import FINAL  # noqa: E402

PLAIN = ("Translate the following English video game subtitle into natural spoken Turkish. Translate idioms and slang by meaning "
         "into the natural Turkish equivalent, never word for word. Produce only the Turkish translation.\n\n{text}")


def gemma(text, port=8099):
    body = json.dumps({"messages": [{"role": "user", "content": PLAIN.format(text=text)}], "temperature": 0, "max_tokens": 200,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def main():
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    hold = [l.split(" ||| ") for l in (HERE.parents[1] / "training" / "holdout_v4.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, began = [], time.perf_counter()
    for i, (cat, ctx, en) in enumerate(FINAL, 1):
        rows.append({"set": "final", "id": i, "category": cat, "en": en, "gemma": gemma(en)})
    for i, (en, ref, cat) in enumerate(hold):
        rows.append({"set": "holdout", "id": i, "category": cat, "en": en, "ref": ref, "gemma": gemma(en)})
    (HERE / "gemma_lines.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(rows), "lines,", round((time.perf_counter() - began) / len(rows), 2), "s per line")


main()
