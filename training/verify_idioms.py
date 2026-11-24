"""Checks the Turkish idioms named in training pairs against the TDK dictionary, and the English side against the test sets.

Pairs files: "English ||| Türkçe ||| deyim" (third field optional, the idiom's dictionary form).

    python training/verify_idioms.py training/idioms_*.txt
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "rating"))
CACHE = Path(__file__).parent / "tdk_cache.json"


def in_tdk(lemma: str):
    url = "https://sozluk.gov.tr/gts?ara=" + urllib.parse.quote(lemma)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - a network hiccup is reported as unchecked, not as missing
        return None
    return isinstance(data, list) and any(item.get("madde", "").lower() == lemma.lower() for item in data)


def test_sentences() -> list[str]:
    from final_set import FINAL
    from mt_bench import BENCH
    from rating_set import SET
    from translation_testset import TESTSET

    return ([e for _, _, e in FINAL] + [row[1] for row in SET] + [e for _, e, _ in BENCH] + [row[1] for row in TESTSET])


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rows = []
    for name in [a for a in sys.argv[1:] if not a.startswith('--')]:
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            if " ||| " in line:
                parts = [p.strip() for p in line.split(" ||| ")]
                rows.append((name, parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    # 1. idioms named in the data must exist in the Turkish dictionary
    missing = []
    for lemma in sorted({r[3] for r in rows if r[3]}):
        if lemma not in cache:
            cache[lemma] = in_tdk(lemma)
        if cache[lemma] is False:
            missing.append(lemma)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    # 2. no training sentence may share a 4-word run with a test sentence (the test sets must stay unseen)
    grams = set()
    for sentence in test_sentences():
        w = words(sentence)
        grams.update(tuple(w[i:i + 4]) for i in range(len(w) - 3))
    exact = {" ".join(words(s)) for s in test_sentences()}
    overlaps = [(r[1]) for r in rows if " ".join(words(r[1])) in exact] + [(r[1]) for r in rows if any(tuple(w[i:i + 4]) in grams for w in [words(r[1])] for i in range(len(w) - 3))]
    if "--fix" in sys.argv:                                      # drop tags TDK does not know and lines that overlap a test sentence
        bad, overlapped = set(missing), set(overlaps)
        for name in {r[0] for r in rows}:
            kept = []
            for line in Path(name).read_text(encoding="utf-8").splitlines():
                parts = [x.strip() for x in line.split(" ||| ")]
                if parts[0] in overlapped:
                    continue
                if len(parts) > 2 and (parts[2] in bad or not parts[2]):
                    parts = parts[:2]
                kept.append(" ||| ".join(parts))
            Path(name).write_text(chr(10).join(kept) + chr(10), encoding="utf-8")
    print(f"{len(rows)} pairs, {len({r[3] for r in rows if r[3]})} named idioms")
    print("not in TDK:", ", ".join(missing) or "none")
    print("overlap with test sets:", len(overlaps))
    for line in overlaps[:20]:
        print("  ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
