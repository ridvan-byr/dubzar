"""How much does each rule layer add on the 120-line benchmark? Same model, same settings; layers switched on one by one.

    python experiments/mt_rules_bench.py

  before       the app before the layers (old speaker-label rule, no prompt template, no memory)
  + labels     interface labels ("Difficulty: Hard") are no longer taken for speakers
  + prompts    "Press E to open the door." put together by rule around the model's purpose clause
  + memory     exact whole-line memory of very common interface strings (several of them are in the benchmark lines, so this
               step is flattered: it shows the mechanism, not the gain on unseen text)
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from mt_bench import BENCH  # noqa: E402
from translation_eval import chrf  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    import dubzar.gameterms as terms
    import dubzar.textsplit as split
    import dubzar.translate as translate

    translator = translate.OpusMtTranslator(threads=8)
    translator.load()

    old_not_speakers = {"note", "warning", "tip", "objective", "hint", "remember", "mission", "goal", "task", "caution",
                        "important", "attention", "press", "hold", "reminder", "update", "new", "quest"}
    new_not_speakers = set(split.NOT_SPEAKERS)
    memory, match_prompt = dict(terms.MEMORY), translate.match_prompt

    def configure(labels: bool, prompts: bool, mem: bool) -> None:
        split.NOT_SPEAKERS.clear()
        split.NOT_SPEAKERS.update(new_not_speakers if labels else old_not_speakers)
        terms.MEMORY.clear()
        if mem:
            terms.MEMORY.update(memory)
        translate.match_prompt = match_prompt if prompts else (lambda text, fn: None)

    steps = [("before", (False, False, False)), ("+ labels", (True, False, False)),
             ("+ labels + prompts", (True, True, False)), ("+ labels + prompts + memory", (True, True, True))]
    table = {}
    for name, flags in steps:
        configure(*flags)
        per = defaultdict(list)
        for category, english, reference in BENCH:
            per[category].append(chrf(translator.translate(english), reference))
        everything = [s for v in per.values() for s in v]
        table[name] = (sum(everything) / len(everything), {c: sum(v) / len(v) for c, v in per.items()})
    categories = list(next(iter(table.values()))[1])
    print("| Katman | chrF | " + " | ".join(categories) + " |")
    print("|---|---|" + "---|" * len(categories))
    for name, (score, per) in table.items():
        print(f"| {name} | {score:.1f} | " + " | ".join(f"{per[c]:.1f}" for c in categories) + " |")
    configure(True, True, True)
    print("\nÖrnekler (hepsi açık):")
    for text in ["Difficulty: Hard", "Optional: Take photos of the wildlife.", "Controls: Move, Aim, Fire", "Press E to open the door.",
                 "Hold F to repair.", "Press R to reload.", "Press any button to continue.", "Brian: But the count was good.",
                 "Wanted level: 3 stars. Evade the pursuit.", "Press E to pick up the weapon.", "Hold Shift to sprint."]:
        print(f"  {text}  ->  {translator.translate(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
