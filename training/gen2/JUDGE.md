# Judge brief
Each line of gen2/<cat>_diff.txt is tab-separated: index, English, translation A, translation B, optional idiom tag (the tag belongs to A).
Two independent translators disagreed strongly. For every line decide the best Turkish subtitle for a game:
- Natural, fluent, native-sounding, faithful in meaning and register (slang stays slang, formal stays formal). Idioms: the real Turkish equivalent, otherwise a plain natural paraphrase. No word-for-word calques, no invented idioms. Commands to one person: singular "sen".
- Choose A or B if one is clearly right (copy it as is), or write your own better version, or mark DROP if the English is odd/ambiguous so no reliable translation exists.
- Verify doubtful Turkish idioms in TDK (https://sozluk.gov.tr/gts?ara=<lemma>, header User-Agent: Mozilla/5.0). Do not hammer.
Output file gen2/<cat>_judged.txt, one line per input line, tab-separated: index, verdict (A, B, NEW or DROP), final Turkish (empty if DROP). Write in chunks of ~60 lines then concatenate if long. Reply only with counts of A/B/NEW/DROP.
Do not open any other training file.
