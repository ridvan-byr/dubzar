# Writer brief (shared)
Project: Dubzar, a Windows tool that shows Turkish subtitles for English game dialogue/UI. We fine-tune an English->Turkish MT model (Opus-MT) and need NEW training pairs.
Output file format, one pair per line, UTF-8, no numbering, no blank lines:
    English ||| Türkçe ||| tag
`tag` is optional: the dictionary form of a Turkish idiom used (e.g. `nalları dikmek`) so TDK can verify it. Leave it out when no idiom.

Quality rules (the single most important thing):
- Turkish must be natural, fluent, native-sounding, translated BY MEANING. Idioms/slang/phrasal verbs get the idiomatic Turkish equivalent, never word-for-word. If no real equivalent exists, use a plain natural paraphrase; never invent an idiom.
- Commands to the player/one person: singular "sen" imperative (Kapıyı aç, not Kapıyı açın) unless the English clearly addresses a group/crew/formal audience.
- Keep game proper-noun style: names unchanged. Numbers/units kept as digits.
- Each English line is a single natural subtitle line (3-20 words typical, mix lengths, some two-sentence lines). Vary vocabulary, speakers, tense, punctuation; no near-duplicates, no templated repetition of one sentence with swapped nouns.
- Don't reuse any English line from: training/*.txt (existing data), experiments/rating/final_set.py (test set), training/replay*_en.txt. Check with `grep -rF` or the helper `python training/verify_idioms.py <your file>` which reports overlaps with the test sets; fix them.
- Use your own knowledge; where unsure of a Turkish idiom, verify it in TDK (https://sozluk.gov.tr/gts?ara=<lemma> with a "User-Agent: Mozilla/5.0" header; JSON list with `madde`). Do not hammer other sites.
- Write the file in chunks of about 100 lines (create the file with Write, then append with further Write of separate part files named gen/<name>_p1.txt, p2.txt, ...). Final deliverable: all parts together, no duplicates, about 600 pairs total.
- Do not edit any file outside training/gen/. Do not run training. Work in the Windows machine at C:\Users\hp\Desktop\Dubzar.
When done reply with: file names, line count, and any lines you were unsure about (max 10).
