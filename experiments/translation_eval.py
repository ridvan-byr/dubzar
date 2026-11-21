"""Scores a translator on the hard-line test set with chrF against translation_refs.REFS, and shows what changed.

python experiments/translation_eval.py --threads 8
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from translation_refs import REFS  # noqa: E402
from translation_testset import TESTSET  # noqa: E402


def chrf(hyp: str, ref: str, max_n: int = 6, beta: float = 2.0) -> float:
    """Character n-gram F-score (0..100), spaces ignored, as in the chrF metric."""
    hyp, ref = hyp.replace(" ", ""), ref.replace(" ", "")
    scores = []
    for n in range(1, max_n + 1):
        h = Counter(hyp[i:i + n] for i in range(len(hyp) - n + 1))
        r = Counter(ref[i:i + n] for i in range(len(ref) - n + 1))
        if not h or not r:
            continue
        match = sum((h & r).values())
        p, rec = match / sum(h.values()), match / sum(r.values())
        scores.append(0.0 if p + rec == 0 else (1 + beta ** 2) * p * rec / (beta ** 2 * p + rec))
    return 100 * sum(scores) / len(scores) if scores else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    assert len(REFS) == len(TESTSET)

    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=args.threads)
    translator.load()
    raw = translator._get_backend()          # the model alone: how it was used before sentence splitting
    old = [raw(line) for _, line, _ in TESTSET]
    new = [translator.translate(line) for _, line, _ in TESTSET]
    old_scores = [chrf(h, r) for h, r in zip(old, REFS)]
    new_scores = [chrf(h, r) for h, r in zip(new, REFS)]
    print(f"chrF ortalama: eski {sum(old_scores) / len(old_scores):.1f}  ->  yeni {sum(new_scores) / len(new_scores):.1f}\n")
    for i, (o, n, so, sn) in enumerate(zip(old, new, old_scores, new_scores), 1):
        if o != n:
            print(f"{i:2d}. {TESTSET[i - 1][1]}\n    eski ({so:4.0f}): {o}\n    yeni ({sn:4.0f}): {n}\n    ref        : {REFS[i - 1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
