"""Can a second opinion pick better translations out of Opus-MT's own n-best list? (No tuning on the benchmark: fixed rules.)

    python experiments/mt_rerank.py --hy C:/Users/hp/hf_models/Hy-MT2-1.8B

Per line: Opus-MT (int8) gives its 8 best candidates (beam 8). Then
  top1       the first one (what the app does)
  mbr        the candidate most similar to all the others (minimum Bayes risk with chrF; needs no second model)
  hy         the candidate Hy-MT2-1.8B finds most likely as a translation of the line (mean token log-probability)
  mbr+hy     rank by the sum of the two ranks (lower is better)
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from mt_bench import BENCH  # noqa: E402
from translation_eval import chrf  # noqa: E402

PROMPT = "Translate the following text into Turkish. Note that you should only output the translated result without any additional explanation:\n\n{text}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hy", default="C:/Users/hp/hf_models/Hy-MT2-1.8B")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--nbest", type=int, default=8)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    import ctranslate2
    import sentencepiece
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from dubzar.translate import ct2_model_dir

    directory = ct2_model_dir()
    opus = ctranslate2.Translator(str(directory), device="cpu", compute_type="int8", intra_threads=args.threads)
    source, target = sentencepiece.SentencePieceProcessor(), sentencepiece.SentencePieceProcessor()
    source.Load(str(directory / "source.spm"))
    target.Load(str(directory / "target.spm"))

    tokenizer = AutoTokenizer.from_pretrained(args.hy)
    hy = AutoModelForCausalLM.from_pretrained(args.hy, dtype=torch.bfloat16).to("cuda").eval()

    def nbest(text: str) -> list[str]:
        pieces = source.encode(text, out_type=str)[:255] + ["</s>"]
        result = opus.translate_batch([pieces], beam_size=args.nbest, num_hypotheses=args.nbest, max_decoding_length=256)[0]
        out = []
        for hypothesis in result.hypotheses:
            sentence = target.decode_pieces([p for p in hypothesis if p not in ("</s>", "<pad>")])
            if sentence not in out:
                out.append(sentence)
        return out

    def hy_scores(text: str, candidates: list[str]) -> list[float]:
        messages = [{"role": "user", "content": PROMPT.format(text=text)}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True)["input_ids"][0].tolist()
        sequences = [prompt + tokenizer(c, add_special_tokens=False)["input_ids"] for c in candidates]
        width = max(len(s) for s in sequences)
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
        ids = torch.tensor([s + [pad] * (width - len(s)) for s in sequences], device="cuda")
        mask = torch.tensor([[1] * len(s) + [0] * (width - len(s)) for s in sequences], device="cuda")
        with torch.no_grad():
            logits = hy(input_ids=ids, attention_mask=mask).logits.float()
        logprobs = torch.log_softmax(logits[:, :-1], dim=-1).gather(-1, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
        scores = []
        for i, s in enumerate(sequences):
            span = logprobs[i, len(prompt) - 1:len(s) - 1]
            scores.append(float(span.mean()) if len(span) else -99.0)
        return scores

    def rank(values: list[float]) -> list[int]:
        order = sorted(range(len(values)), key=lambda i: -values[i])
        ranks = [0] * len(values)
        for place, i in enumerate(order):
            ranks[i] = place
        return ranks

    picks = {"top1": [], "mbr": [], "hy": [], "mbr+hy": []}
    began = time.perf_counter()
    for category, english, reference in BENCH:
        cands = nbest(english)
        if len(cands) == 1:
            chosen = {k: cands[0] for k in picks}
        else:
            mbr = [sum(chrf(c, o) for o in cands if o is not c) / (len(cands) - 1) for c in cands]
            h = hy_scores(english, cands)
            combined = [a + b for a, b in zip(rank(mbr), rank(h))]
            chosen = {"top1": cands[0], "mbr": cands[mbr.index(max(mbr))], "hy": cands[h.index(max(h))],
                      "mbr+hy": cands[combined.index(min(combined))]}
        for k, v in chosen.items():
            picks[k].append((category, chrf(v, reference)))
    print(f"{len(BENCH)} satır, {time.perf_counter() - began:.0f} sn")
    cats = sorted({c for c, _ in picks["top1"]})
    print("| Seçim | chrF | " + " | ".join(cats) + " |")
    print("|---|---|" + "---|" * len(cats))
    for k, values in picks.items():
        mean = sum(s for _, s in values) / len(values)
        per = {c: sum(s for cc, s in values if cc == c) / sum(1 for cc, _ in values if cc == c) for c in cats}
        print(f"| {k} | {mean:.1f} | " + " | ".join(f"{per[c]:.1f}" for c in cats) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
