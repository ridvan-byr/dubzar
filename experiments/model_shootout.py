"""Translation models on the hard game-line test set: chrF against our references, speed, memory.

python experiments/model_shootout.py --models opus madlad-gpu madlad-cpu gemma-gpu
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from translation_eval import chrf  # noqa: E402
from translation_refs import REFS  # noqa: E402
from translation_testset import TESTSET  # noqa: E402

GEMMA_PROMPT = ("Translate the following English video game subtitle into natural spoken Turkish. "
                "Produce only the Turkish translation.\n\n{text}")


def madlad(device: str, threads: int):
    import ctranslate2
    import sentencepiece as spm
    from huggingface_hub import snapshot_download

    folder = snapshot_download("Nextcloud-AI/madlad400-3b-mt-ct2-int8", local_files_only=True)   # never downloads here
    sp = spm.SentencePieceProcessor(model_file=str(Path(folder) / "spiece.model"))
    translator = ctranslate2.Translator(folder, device=device, compute_type="int8_float16" if device == "cuda" else "int8",
                                        inter_threads=1, intra_threads=threads)

    def run(text: str) -> str:
        tokens = sp.encode("<2tr> " + text, out_type=str)
        out = translator.translate_batch([tokens], beam_size=4, max_decoding_length=256)
        return sp.decode(out[0].hypotheses[0])

    return run


def gemma(gpu_layers: int, threads: int):
    from huggingface_hub import snapshot_download
    from llama_cpp import Llama

    folder = snapshot_download("google/gemma-4-12B-it-qat-q4_0-gguf", allow_patterns=["gemma-4-12b-it-qat-q4_0.gguf"],
                               local_files_only=True)
    llm = Llama(model_path=str(Path(folder) / "gemma-4-12b-it-qat-q4_0.gguf"), n_ctx=1024, n_threads=threads,
                n_gpu_layers=gpu_layers, verbose=False)

    def run(text: str) -> str:
        out = llm.create_chat_completion(messages=[{"role": "user", "content": GEMMA_PROMPT.format(text=text)}],
                                         temperature=0.0, max_tokens=200)
        return out["choices"][0]["message"]["content"].strip()

    return run


def opus(threads: int):
    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=threads)
    translator.load()
    return translator.translate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["opus"])
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    makers = {"opus": lambda: opus(args.threads), "madlad-gpu": lambda: madlad("cuda", args.threads),
              "madlad-cpu": lambda: madlad("cpu", args.threads), "gemma-gpu": lambda: gemma(-1, args.threads),
              "gemma-cpu": lambda: gemma(0, args.threads)}
    results = {}
    for name in args.models:
        run = makers[name]()
        run("Hello there, how are you?")                                   # warm up
        hyps, times = [], []
        for _, line, _ in TESTSET:
            began = time.perf_counter()
            hyps.append(run(line).strip())
            times.append(time.perf_counter() - began)
        scores = [chrf(h, r) for h, r in zip(hyps, REFS)]
        results[name] = (hyps, scores, times)
        print(f"{name:11s} chrF {sum(scores) / len(scores):5.1f} | {sum(times) / len(times):5.2f} sn/satır "
              f"(en yavaş {max(times):.2f})", flush=True)
    out = Path(__file__).parent / "model_shootout.md"
    lines = ["# Çeviri modelleri karşılaştırması", "", "| model | chrF | sn/satır |", "|---|---|---|"]
    for name, (_, scores, times) in results.items():
        lines.append(f"| {name} | {sum(scores) / len(scores):.1f} | {sum(times) / len(times):.2f} |")
    lines += ["", "| # | İngilizce | referans | " + " | ".join(results) + " |", "|---|---|---|" + "---|" * len(results)]
    for i, (_, line, _) in enumerate(TESTSET):
        lines.append(f"| {i + 1} | {line} | {REFS[i]} | " + " | ".join(f"{r[0][i]} ({r[1][i]:.0f})" for r in results.values()) + " |")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("yazıldı:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
