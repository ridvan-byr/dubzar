"""Compares the two independent Turkish translations of each generated English line.
Writes gen2/<cat>_diff.txt with lines where they differ much (candidates for review) and prints counts."""
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

GEN, GEN2 = Path(__file__).parent / "gen", Path(__file__).parent / "gen2"


def norm(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s.lower().replace("İ", "i").replace("I", "ı")).strip()


def first_pairs(cat):
    rows = []
    for f in sorted(GEN.glob(cat + "_p*.txt"), key=lambda p: int(re.search(r"_p(\d+)", p.name).group(1))):
        for l in f.read_text(encoding="utf-8").splitlines():
            if "|||" in l:
                parts = [x.strip() for x in l.split("|||")]
                rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def main(cats):
    for cat in cats:
        a = first_pairs(cat)
        b = [l.strip() for l in (GEN2 / f"{cat}_tr.txt").read_text(encoding="utf-8").splitlines()]
        assert len(a) == len(b), (cat, len(a), len(b))
        same = close = far = 0
        out = []
        for i, ((en, t1, tag), t2) in enumerate(zip(a, b), 1):
            r = SequenceMatcher(None, norm(t1), norm(t2)).ratio()
            if r >= 0.999: same += 1
            elif r >= 0.7: close += 1
            else:
                far += 1
                out.append(f"{i}\t{en}\t{t1}\t{t2}\t{tag}")
        (GEN2 / f"{cat}_diff.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"{cat}: {len(a)} satır, aynı {same}, yakın {close}, ayrışan {far}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arayuz", "konusma", "gorev", "argo1", "argo2", "resmi", "deyim2", "deyim1"])
