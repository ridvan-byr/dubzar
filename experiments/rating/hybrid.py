"""Hybrid experiment: route the lines Opus-MT is least sure about to a second model, then let a person rate the second model's output.

    python experiments/rating/hybrid.py            # scores the 200 final lines, runs Hy-MT2-1.8B on the least confident 40%
    python experiments/rating/build_page.py --hybrid
    python experiments/rating/serve.py --hybrid

Writes experiments/rating/hybrid_lines.json. Opus-MT confidence = total log-probability of the best hypothesis of the whole line.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).parent))

HERE = Path(__file__).parent
HY_DIR = r"C:\Users\hp\hf_models\Hy-MT2-1.8B"
SHARE = 0.4
PROMPT = "Translate the following text into Turkish. Note that you should only output the translated result without any additional explanation:\n\n{text}"


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    from final_set import FINAL

    from dubzar.translate import OpusMtTranslator, ct2_model_dir

    opus = OpusMtTranslator(threads=8)
    opus.load()
    import ctranslate2
    import sentencepiece

    model_dir = ct2_model_dir()
    ct2 = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8", intra_threads=8)
    src, tgt = sentencepiece.SentencePieceProcessor(), sentencepiece.SentencePieceProcessor()
    src.Load(str(model_dir / "source.spm"))
    tgt.Load(str(model_dir / "target.spm"))

    rows = []
    for i, (category, context, en) in enumerate(FINAL, 1):
        pieces = src.encode(en, out_type=str)[:255] + ["</s>"]
        hyp = ct2.translate_batch([pieces], beam_size=4, max_decoding_length=256, return_scores=True)[0]
        tokens = len(hyp.hypotheses[0]) + 1
        total = hyp.scores[0] * tokens                    # CT2 scores are per token; the total is the product
        rows.append({"id": i, "category": category, "context": context, "en": en, "opus": opus.translate(en),
                     "total_logprob": total, "per_token": hyp.scores[0]})
    order = sorted(rows, key=lambda r: r["total_logprob"])
    routed = {r["id"] for r in order[: round(len(rows) * SHARE)]}
    for r in rows:
        r["routed"] = r["id"] in routed

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(HY_DIR)
    model = AutoModelForCausalLM.from_pretrained(HY_DIR, dtype=torch.bfloat16).to("cuda").eval()

    def hy(text: str) -> str:
        inputs = tok.apply_chat_template([{"role": "user", "content": PROMPT.format(text=text)}], add_generation_prompt=True,
                                         return_tensors="pt", return_dict=True)
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=128, do_sample=False, repetition_penalty=1.05)
        return tok.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

    for r in rows:
        if r["routed"]:
            r["hy"] = hy(r["en"])
            print(r["id"], r["en"], "|", r["opus"], "|", r["hy"], flush=True)
    (HERE / "hybrid_lines.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sum(r['routed'] for r in rows)} routed lines -> hybrid_lines.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
