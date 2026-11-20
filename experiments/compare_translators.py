"""Opus-MT vs TranslateGemma 4B on hard game lines: quality side by side, speed, memory.

python experiments/compare_translators.py --threads 8            # full set -> experiments/translation_compare.md
python experiments/compare_translators.py --threads 2 --limit 8  # speed with the few cores a game leaves us
"""

import argparse
import sys
import time
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from translation_testset import TESTSET  # noqa: E402

GGUF_REPO = "bullerwins/translategemma-4b-it-GGUF"
GGUF_FILE = "translategemma-4b-it-Q4_K_M.gguf"
PROMPT = ("You are a professional English (en) to Turkish (tr) translator. Your goal is to accurately convey the "
          "meaning and nuances of the original English text while adhering to Turkish grammar, vocabulary, and "
          "cultural sensitivities.\nProduce only the Turkish translation, without any additional explanations or "
          "commentary. Please translate the following English text into Turkish:\n\n\n{text}")
CONTEXT_PROMPT = ("You are a professional English (en) to Turkish (tr) translator for video game subtitles. "
                  "Translate ONLY the final line into natural spoken Turkish, using the earlier lines of the scene "
                  "to pick the right word meanings. Produce only the Turkish translation of the final line.\n\n"
                  "Earlier lines (context only, do not translate):\n{context}\n\nLine to translate:\n{text}")


def rss_gb() -> float:
    return psutil.Process().memory_info().rss / 1e9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--gpu-layers", type=int, default=0)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    items = TESTSET[: args.limit] if args.limit else TESTSET

    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    from dubzar.translate import OpusMtTranslator

    base = rss_gb()
    opus = OpusMtTranslator(threads=args.threads)
    opus.load()
    opus.translate("warm up")
    after_opus = rss_gb()

    path = hf_hub_download(GGUF_REPO, GGUF_FILE, local_files_only=True)  # never downloads here
    llm = Llama(model_path=path, n_ctx=1024, n_threads=args.threads, n_gpu_layers=args.gpu_layers, verbose=False)
    after_llm = rss_gb()

    def gemma_plain(text: str) -> str:
        """The model's own translation template: the text plus source and target language codes."""
        content = [{"type": "text", "source_lang_code": "en", "target_lang_code": "tr", "text": text}]
        out = llm.create_chat_completion(messages=[{"role": "user", "content": content}], temperature=0.0, max_tokens=160)
        return out["choices"][0]["message"]["content"].strip()

    def gemma_context(prompt: str) -> str:
        """Free-form instruction in Gemma's plain chat format (the translation template has no room for context)."""
        raw = "<start_of_turn>user\n" + prompt + "<end_of_turn>\n<start_of_turn>model\n"
        out = llm.create_completion(raw, temperature=0.0, max_tokens=160, stop=["<end_of_turn>"])
        return out["choices"][0]["text"].strip()

    gemma_plain("Hello there.")  # warm up
    rows, t_opus, t_gem, t_ctx = [], [], [], []
    for previous, line, note in items:
        t = time.perf_counter(); a = opus.translate(line); t_opus.append(time.perf_counter() - t)
        t = time.perf_counter(); b = gemma_plain(line); t_gem.append(time.perf_counter() - t)
        c = ""
        if previous:
            t = time.perf_counter()
            c = gemma_context(CONTEXT_PROMPT.format(context="\n".join(previous), text=line)); t_ctx.append(time.perf_counter() - t)
        rows.append((line, a, b, c, note))
        print(f"{len(rows):2d}/{len(items)}", flush=True)

    def avg(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    lines = [f"# Çeviri karşılaştırması ({args.threads} iş parçacığı, GPU katmanı {args.gpu_layers})", "",
             f"- Opus-MT: ortalama {avg(t_opus):.2f} sn/satır",
             f"- TranslateGemma 4B Q4: ortalama {avg(t_gem):.2f} sn/satır; bağlamlı: {avg(t_ctx):.2f} sn/satır",
             f"- Bellek (RAM): temel {base:.1f} GB → Opus-MT sonrası {after_opus:.1f} GB → +TranslateGemma {after_llm:.1f} GB", "",
             "| # | İngilizce | Opus-MT | TranslateGemma | TranslateGemma + bağlam | zorluk |", "|---|---|---|---|---|---|"]
    for i, (en, a, b, c, note) in enumerate(rows, 1):
        lines.append(f"| {i} | {en} | {a} | {b} | {c or '-'} | {note} |")
    out = Path(__file__).parent / f"translation_compare_t{args.threads}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:6]))
    print("yazıldı:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
