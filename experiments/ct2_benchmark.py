"""PyTorch float32 vs CTranslate2 int8 for Opus-MT: speed, memory, and whether the translations stay the same.

python experiments/ct2_benchmark.py            # needs models_ct2/ (see ct2 conversion in the commit message of this file)
"""

import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from translation_eval import chrf  # noqa: E402
from translation_refs import REFS  # noqa: E402
from translation_testset import TESTSET  # noqa: E402

from dubzar.textsplit import split_pieces  # noqa: E402

CT2_DIR = ROOT / "models_ct2" / "opus-mt-tc-big-en-tr-int8"


def rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1e6


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    import ctranslate2
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    from dubzar.translate import MODEL_NAME, UNNEEDED_FILES

    folder = snapshot_download(MODEL_NAME, local_files_only=True, ignore_patterns=UNNEEDED_FILES)
    tok = AutoTokenizer.from_pretrained(folder)
    lines = [line for _, line, _ in TESTSET]
    sentences = [p.text for line in lines for p in split_pieces(line)]

    results = {}
    for threads in (2, 8):
        torch.set_num_threads(threads)
        before = rss_mb()
        model = AutoModelForSeq2SeqLM.from_pretrained(folder, dtype=torch.float32).eval()
        torch_mb = rss_mb() - before

        def torch_translate(text: str) -> str:
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
            with torch.inference_mode():
                out = model.generate(**inputs, max_length=256, num_beams=4)
            return tok.decode(out[0], skip_special_tokens=True)

        before = rss_mb()
        ct2 = ctranslate2.Translator(str(CT2_DIR), device="cpu", compute_type="int8", intra_threads=threads)
        ct2_mb = rss_mb() - before

        def ct2_translate(text: str) -> str:
            source = tok.convert_ids_to_tokens(tok.encode(text, truncation=True, max_length=256))
            hyp = ct2.translate_batch([source], beam_size=4, max_decoding_length=256)[0].hypotheses[0]
            return tok.decode(tok.convert_tokens_to_ids(hyp), skip_special_tokens=True)

        torch_translate("warm up"); ct2_translate("warm up")
        timings = {}
        outputs = {}
        for name, fn in (("PyTorch float32", torch_translate), ("CTranslate2 int8", ct2_translate)):
            start = time.perf_counter()
            outputs[name] = [fn(s) for s in sentences]
            timings[name] = (time.perf_counter() - start) / len(sentences)
        print(f"\n== {threads} iş parçacığı, {len(sentences)} cümle (beam 4)")
        print(f"   PyTorch float32  : {timings['PyTorch float32']*1000:6.0f} ms/cümle, bellek ~{torch_mb:.0f} MB")
        print(f"   CTranslate2 int8 : {timings['CTranslate2 int8']*1000:6.0f} ms/cümle, bellek ~{ct2_mb:.0f} MB   "
              f"-> {timings['PyTorch float32']/timings['CTranslate2 int8']:.1f}x hızlı")
        results[threads] = outputs
        del model, ct2

    a, b = results[2]["PyTorch float32"], results[2]["CTranslate2 int8"]
    same = sum(x == y for x, y in zip(a, b))
    print(f"\nBirebir aynı çeviri: {same}/{len(a)} cümle")

    def line_scores(outs):
        it = iter(outs)
        return [chrf(" ".join(next(it) for _ in split_pieces(line)), ref) for line, ref in zip(lines, REFS)]
    sa, sb = line_scores(a), line_scores(b)
    print(f"chrF (40 zor satır): PyTorch {sum(sa)/len(sa):.1f} | CTranslate2 int8 {sum(sb)/len(sb):.1f}")
    shown = 0
    for s, x, y in zip(sentences, a, b):
        if x != y and shown < 8:
            shown += 1
            print(f"  {s}\n     PyTorch: {x}\n     int8   : {y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
