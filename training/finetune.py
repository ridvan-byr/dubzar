"""Fine-tune Opus-MT (English to Turkish) on game-style sentence pairs, and measure before/after.

python training/finetune.py training/pairs_001.txt --epochs 5 --lr 3e-5

Pairs files hold one "English ||| Türkçe" per line. 10% of the pairs are held out as a dev set. The 40 hard lines
(experiments/translation_testset.py, never trained on) are the test set; a small general-conversation set shows
whether the model forgot ordinary Turkish. The tuned model is saved to models_ft/ (git-ignored).
"""

import argparse
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from translation_eval import chrf  # noqa: E402
from translation_refs import REFS  # noqa: E402
from translation_testset import TESTSET  # noqa: E402

from dubzar.textsplit import split_pieces  # noqa: E402

GENERAL = [
    ("Good morning, how are you?", "Günaydın, nasılsın?"),
    ("I would like a cup of coffee, please.", "Bir fincan kahve istiyorum, lütfen."),
    ("The weather is nice today.", "Bugün hava güzel."),
    ("Where is the nearest train station?", "En yakın tren istasyonu nerede?"),
    ("She has been studying for three hours.", "Üç saattir ders çalışıyor."),
    ("We are going to the beach tomorrow.", "Yarın plaja gidiyoruz."),
    ("Can you help me carry these bags?", "Bu çantaları taşımama yardım edebilir misin?"),
    ("He forgot his keys at home.", "Anahtarlarını evde unuttu."),
    ("The movie starts at eight o'clock.", "Film saat sekizde başlıyor."),
    ("My brother works at a hospital.", "Kardeşim bir hastanede çalışıyor."),
    ("Thank you for your help.", "Yardımın için teşekkür ederim."),
    ("It's very cold outside.", "Dışarısı çok soğuk."),
]


def read_pairs(paths) -> list[tuple[str, str]]:
    pairs = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if " ||| " in line:
                en, tr = line.split(" ||| ", 1)
                pairs.append((en.strip(), tr.strip()))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--freeze-encoder", action="store_true", help="train only the decoder (gentler, less forgetting)")
    ap.add_argument("--out", default=str(ROOT / "models_ft" / "opus-mt-en-tr-games"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--replay", help="English-only file; the untuned model translates it and those pairs are mixed "
                                     "in, so ordinary Turkish is not forgotten")
    ap.add_argument("--save", action="store_true", help="write the tuned model to --out")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--final-only", action="store_true", help="measure only before and after training (faster)")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    from dubzar.translate import MODEL_NAME, UNNEEDED_FILES

    folder = snapshot_download(MODEL_NAME, local_files_only=True, ignore_patterns=UNNEEDED_FILES)
    tok = AutoTokenizer.from_pretrained(folder)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForSeq2SeqLM.from_pretrained(folder, dtype=torch.float32).to(device)  # the checkpoint is float16: training in it overflows

    seen, pairs = set(), []
    for en, tr in read_pairs(args.pairs):
        key = "".join(c for c in en.lower() if c.isalnum())
        if key not in seen:
            seen.add(key)
            pairs.append((en, tr))
    random.shuffle(pairs)
    dev, train = pairs[: len(pairs) // 10], pairs[len(pairs) // 10:]
    probe = [l.strip() for l in (ROOT / "training" / "probe_en.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

    @torch.inference_mode()
    def translate(sentence: str) -> str:
        model.eval()
        inputs = tok(sentence, return_tensors="pt", truncation=True, max_length=256).to(device)
        out = model.generate(**inputs, max_length=256, num_beams=4)
        return tok.decode(out[0], skip_special_tokens=True)

    def pipeline(text: str) -> str:  # the same per-sentence path the app uses
        return " ".join((f"{p.speaker}: " if p.speaker else "") + translate(p.text) for p in split_pieces(text))

    base_probe = [translate(s) for s in probe]          # what the untuned model says: the yardstick for forgetting
    if args.replay:
        replay_src = [l.strip() for l in Path(args.replay).read_text(encoding="utf-8").splitlines() if l.strip()]
        train += [(s, translate(s)) for s in replay_src]
    print(f"{len(train)} eğitim ({len(train) - (len(replay_src) if args.replay else 0)} oyun + "
          f"{len(replay_src) if args.replay else 0} tekrar), {len(dev)} doğrulama, cihaz: {device}", flush=True)

    def score(name, items, refs, show=()):
        outs = [pipeline(e) for e in items]
        value = sum(chrf(o, r) for o, r in zip(outs, refs)) / len(refs)
        for i in show:
            if not args.quiet:
                print(f"      {items[i]}  ->  {outs[i]}")
        return value

    def report(label):
        t = score("test", [l for _, l, _ in TESTSET], REFS, show=(0, 1, 3, 4, 22, 38))
        d = score("dev", [e for e, _ in dev], [t_ for _, t_ in dev])
        g = score("general", [e for e, _ in GENERAL], [t_ for _, t_ in GENERAL])
        kept = sum(chrf(translate(s), b) for s, b in zip(probe, base_probe)) / len(probe)   # 100 = unchanged
        print(f"[{label}] zor satırlar (test) {t:5.1f} | doğrulama {d:5.1f} | genel konuşma {g:5.1f} | "
              f"eski davranışı koruma {kept:5.1f}", flush=True)

    report("eğitimsiz")

    if args.freeze_encoder:
        for p in model.model.encoder.parameters():
            p.requires_grad = False
        model.model.shared.weight.requires_grad = False
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(train) + args.batch - 1) // args.batch)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: min(1.0, (s + 1) / 10) * max(0.0, 1 - s / steps))

    for epoch in range(1, args.epochs + 1):
        model.train()
        random.shuffle(train)
        total, started = 0.0, time.time()
        for i in range(0, len(train), args.batch):
            batch = train[i:i + args.batch]
            enc = tok([e for e, _ in batch], text_target=[t for _, t in batch], return_tensors="pt", padding=True,
                      truncation=True, max_length=128).to(device)
            enc["labels"][enc["labels"] == tok.pad_token_id] = -100
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                loss = model(**enc).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            optimizer.step(); scheduler.step(); optimizer.zero_grad()
            total += loss.item() * len(batch)
        print(f"-- tur {epoch}: eğitim kaybı {total / len(train):.3f} ({time.time() - started:.0f} sn)", flush=True)
        if not args.final_only or epoch == args.epochs:
            report(f"tur {epoch}")

    if args.save:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(args.out)
        tok.save_pretrained(args.out)
        print("kaydedildi:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
