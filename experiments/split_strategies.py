import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(errors="replace", encoding="utf-8")
from translation_eval import chrf
from translation_refs import REFS
from translation_testset import TESTSET
from dubzar.textsplit import split_pieces, _sentences
from dubzar.translate import OpusMtTranslator

tr = OpusMtTranslator(threads=8); tr.load(); raw = tr._get_backend()
n_sent = lambda t: len(_sentences(t))

def per_sentence(text):                      # A: always split
    return " ".join((f"{p.speaker}: " if p.speaker else "") + raw(p.text) for p in split_pieces(text))

def whole_then_fallback(text):               # B: whole text, split only if sentences vanished
    out = []
    for speaker, group in groups(text, min_words=10**9):
        out.append((f"{speaker}: " if speaker else "") + translate_group(group))
    return " ".join(out)

def chunked(text, min_words=6):              # C: chunks of >= min_words, split only if sentences vanished
    out = []
    for speaker, group in groups(text, min_words):
        out.append((f"{speaker}: " if speaker else "") + translate_group(group))
    return " ".join(out)

def groups(text, min_words):
    result, current, words, speaker = [], [], 0, None
    for p in split_pieces(text):
        if p.speaker and current:
            result.append((speaker, current)); current, words = [], 0
        if p.speaker: speaker = p.speaker
        current.append(p.text); words += len(p.text.split())
        if words >= min_words:
            result.append((speaker, current)); current, words, speaker = [], 0, None
    if current: result.append((speaker, current))
    return result

def translate_group(sentences):
    joined = " ".join(sentences)
    out = raw(joined)
    if n_sent(out) >= len(sentences) or len(sentences) == 1:
        return out
    return " ".join(raw(s) for s in sentences)

strategies = {"önceki (hiç bölme)": lambda t: raw(t), "A her cümle ayrı": per_sentence,
              "B bütün, kayıp olursa böl": whole_then_fallback, "C 6+ kelimelik parçalar": chunked,
              "C' 4+ kelimelik parçalar": lambda t: chunked(t, 4)}
for name, fn in strategies.items():
    outs = [fn(line) for _, line, _ in TESTSET]
    print(f"{name:28s} chrF {sum(chrf(o, r) for o, r in zip(outs, REFS)) / len(REFS):.1f}")
