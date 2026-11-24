"""How much quality is free in Opus-MT settings? Same 120-line benchmark, different decoding settings and precision.

    python experiments/mt_variants.py --threads 8

Variants: the app's int8 model with beam 4 (as shipped), beam 8, beam 8 + length penalty, and the same weights as float16
converted from the original checkpoint, run in float32 (no int8 rounding).
"""

import argparse
import glob
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from mt_bench import BENCH  # noqa: E402
from translation_eval import chrf  # noqa: E402


def make_backend(model_dir: Path, compute: str, beam: int, threads: int, length_penalty: float = 1.0):
    import ctranslate2
    import sentencepiece

    translator = ctranslate2.Translator(str(model_dir), device="cpu", compute_type=compute, intra_threads=threads)
    source, target = sentencepiece.SentencePieceProcessor(), sentencepiece.SentencePieceProcessor()
    source.Load(str(model_dir / "source.spm"))
    target.Load(str(model_dir / "target.spm"))

    def translate(text: str) -> str:
        pieces = source.encode(text, out_type=str)[:255] + ["</s>"]
        best = translator.translate_batch([pieces], beam_size=beam, max_decoding_length=256,
                                          length_penalty=length_penalty)[0].hypotheses[0]
        return target.decode_pieces([p for p in best if p not in ("</s>", "<pad>")])

    return translate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    import ctranslate2

    from dubzar.translate import MODEL_NAME, OpusMtTranslator, ct2_model_dir

    int8_dir = ct2_model_dir()
    fp_dir = Path(tempfile.gettempdir()) / "opus_mt_fp16"
    if not (fp_dir / "model.bin").exists():
        hub = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + MODEL_NAME.replace("/", "--")) / "snapshots"
        folder = sorted(hub.glob("*"))[-1]
        shutil.rmtree(fp_dir, ignore_errors=True)
        ctranslate2.converters.TransformersConverter(str(folder)).convert(str(fp_dir), quantization="float16")
        for name in ("source.spm", "target.spm"):
            shutil.copy2(folder / name, fp_dir / name)

    variants = {
        "int8, beam 4 (şimdiki)": (int8_dir, "int8", 4, 1.0),
        "int8, beam 8": (int8_dir, "int8", 8, 1.0),
        "int8, beam 8, uzunluk cezası 1,3": (int8_dir, "int8", 8, 1.3),
        "float32, beam 4": (fp_dir, "float32", 4, 1.0),
        "float32, beam 8": (fp_dir, "float32", 8, 1.0),
    }
    results = {}
    for name, (directory, compute, beam, penalty) in variants.items():
        translator = OpusMtTranslator(backend=make_backend(directory, compute, beam, args.threads, penalty))
        began = time.perf_counter()
        scores = defaultdict(list)
        for category, english, reference in BENCH:
            scores[category].append(chrf(translator.translate(english), reference))
        elapsed = time.perf_counter() - began
        all_scores = [s for values in scores.values() for s in values]
        results[name] = (sum(all_scores) / len(all_scores), elapsed / len(all_scores),
                         {c: sum(v) / len(v) for c, v in scores.items()})
        print(f"{name:36s} chrF {results[name][0]:5.1f}   {1000 * results[name][1]:4.0f} ms/satır", flush=True)
    categories = list(next(iter(results.values()))[2])
    print("\n| Ayar | chrF | ms | " + " | ".join(categories) + " |")
    print("|---|---|---|" + "---|" * len(categories))
    for name, (score, seconds, per) in results.items():
        print(f"| {name} | {score:.1f} | {1000 * seconds:.0f} | " + " | ".join(f"{per[c]:.1f}" for c in categories) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
