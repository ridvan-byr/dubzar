"""The same 120-line benchmark as mt_bench.py, for a translation language model run with transformers (default: Hy-MT2-1.8B).

    python experiments/mt_bench_llm.py --model tencent/Hy-MT2-1.8B --out experiments/mt_bench_hymt2_report.md

Scores each line with chrF against the references in mt_bench.BENCH and times every line (warm, GPU). The Opus-MT column
comes from the same run of OpusMtTranslator so both columns see the same lines. Decoding is greedy (no sampling) so the run
can be repeated; the model card recommends sampling (temperature 0.7), which is somewhat noisier.
"""

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from mt_bench import BENCH  # noqa: E402
from translation_eval import chrf  # noqa: E402

PROMPT = "Translate the following text into Turkish. Note that you should only output the translated result without any additional explanation:\n\n{text}"

# generic video-game terms (written from general knowledge; several appear in the benchmark lines, so a score with this
# list shows that the mechanism works, not how well it generalises)
GLOSSARY = {"save": "kaydet", "saving": "kaydetme", "health": "can", "cover": "siper", "ride": "araba", "safehouse": "sığınak",
            "objective": "görev", "ammo": "cephane", "reload": "doldur", "checkpoint": "kontrol noktası", "inventory": "envanter",
            "difficulty": "zorluk", "skill": "yetenek", "wanted level": "aranma seviyesi", "man (as a form of address)": "dostum"}
STYLE = "informal video-game subtitles; address the listener with the informal singular (sen), imperatives in the singular (not -in/-ın forms)"


def build_prompt(text: str, mode: str) -> str:
    if mode == "default":
        return PROMPT.format(text=text)
    parts = []
    if "terms" in mode:
        parts.append("Reference the following translations:\n" + "\n".join(f"{k} translates to {v}" for k, v in GLOSSARY.items()) + "\n")
    if "style" in mode:
        parts.append(f"Please translate the following text into Turkish. Note that the translation style must strictly conform to [{STYLE}]. Only output the translation:\n\n{text}")
    else:
        parts.append(f"Translate the following text into Turkish. Note that you must ONLY output the translated result without any additional explanation:\n\n{text}")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="tencent/Hy-MT2-1.8B")
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--mode", default="default", help="default, terms, style or terms+style")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from dubzar.translate import OpusMtTranslator

    opus = OpusMtTranslator(threads=args.threads)
    opus.load()

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    began = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(args.device).eval()
    print(f"model loaded in {time.perf_counter() - began:.1f} s; "
          f"GPU memory {torch.cuda.memory_allocated() / 1e9:.1f} GB" if args.device == "cuda" else "model loaded", flush=True)

    def translate(text: str) -> str:
        messages = [{"role": "user", "content": build_prompt(text, args.mode)}]
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        inputs = {k: v.to(args.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=128, do_sample=False, repetition_penalty=1.05)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

    for _, english, _ in BENCH[:3]:
        translate(english)                                   # warm-up
    rows = []
    for category, english, reference in BENCH:
        t0 = time.perf_counter()
        llm = translate(english)
        llm_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        base = opus.translate(english)
        base_s = time.perf_counter() - t0
        rows.append((category, english, reference, base, chrf(base, reference), base_s, llm, chrf(llm, reference), llm_s))

    def mean(values):
        values = list(values)
        return sum(values) / len(values)

    by_category = defaultdict(list)
    for r in rows:
        by_category[r[0]].append(r)
    name = args.model.replace("\\", "/").split("/")[-1] + ("" if args.mode == "default" else f" ({args.mode})")
    lines = [f"# Opus-MT ile {name}: 120 satırlık kıyas", "",
             f"chrF ortalaması: Opus-MT **{mean(r[4] for r in rows):.1f}**, {name} **{mean(r[7] for r in rows):.1f}**", "",
             f"Satır başına süre (sıcak): Opus-MT {1000 * mean(r[5] for r in rows):.0f} ms, "
             f"{name} {1000 * mean(r[8] for r in rows):.0f} ms ({args.device})", "",
             f"| Tür | satır | Opus-MT | {name} |", "|---|---|---|---|"]
    for category, items in by_category.items():
        lines.append(f"| {category} | {len(items)} | {mean(r[4] for r in items):.1f} | {mean(r[7] for r in items):.1f} |")
    wins = sum(1 for r in rows if r[7] > r[4] + 5)
    losses = sum(1 for r in rows if r[4] > r[7] + 5)
    lines += ["", f"{name}, Opus-MT'den 5+ puan iyi: {wins} satır; 5+ puan kötü: {losses} satır; geri kalan {len(rows) - wins - losses} yakın.",
              "", "## Tüm satırlar", "", f"| tür | İngilizce | Opus-MT | {name} | referans |", "|---|---|---|---|---|"]
    for category, english, reference, base, base_score, _, llm, llm_score, _ in rows:
        lines.append(f"| {category} | {english} | {base} ({base_score:.0f}) | {llm} ({llm_score:.0f}) | {reference} |")
    report = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print("\n".join(lines[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
