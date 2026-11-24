# Judge brief
You rate English->Turkish game-subtitle translations like a strict native Turkish speaker who plays games. Input TSV columns: id, category, English, Turkish. Rate each line:
- ok: correct meaning and reads like natural Turkish; a player wouldn't notice a problem. Perfectly fine paraphrases of idioms are ok.
- minor: understandable and mostly right, but slightly unnatural, stiff, a small wrong nuance/register, or a missing detail.
- bad: wrong or reversed meaning, nonsense/calque a player would find confusing or laughable, untranslated/garbled text, wrong idiom, or a serious register error (e.g. insulting where it shouldn't be).
Be strict about idioms and slang: a literal word-for-word rendering of an idiom is bad. Judge only the Turkish against the English; no ground truth is given.
Output TSV file with columns: id, rating (ok|minor|bad), short reason (<=8 words). One line per input line, same order. Do not read any other file under experiments/ or training/. Reply with only the counts of ok/minor/bad.
