"""Translation with scene context: consecutive game subtitle lines (read from real GTA gameplay by Dubzar), translated by
Opus-MT line by line and by Gemma 4 12B (local llama.cpp server) alone and with the three previous lines as context.
No references: the outputs are put side by side for a human (or a reviewer) to judge.

python experiments/scene_eval.py            # needs the Gemma server on port 8099 (see model_shootout.py)
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCENES = {
    "araba": [
        "You said we're going where?", "But why me?",
        "First, I need to get over to North Vice Ave, then after that at Rockridge. You can drive, right?",
        "Why not? Shit, I always wanted a white driver.", "Head to North Vice Ave.",
        "Your girl fresh off the boat, right?", "Nah, born and raised in Liberty City.",
        "Liberty City? Oh, hell nah, man, you can't tell a bitch", "from Liberty City not a goddamn thing.",
        "They confrontational, argumentative, uncooperative.", "She born here too, so that mean that bitch don't need a Green",
        "That ain't player, dog, nah... that's hard work.",
        "You see, a guy like me grew up hard. A real project, ghetto boy.", "So I gotta get like you now?",
        "Man, this car ain't regular. Everything's custom.", "High quality shit.", "With time, anything is possible.",
    ],
    "mahalle": [
        "I been taking care of the hood, nigga.", "I ran with a lotta thugs and hustlers back in the day,",
        "and I learnt everything I know from a guy called Ducky.", "William Ducky Brown.",
        "That nigga was one of Vice City's largest cocaine distributors, nigga.",
        "And he got that way by having a relationship with the Cubans.", "Who, at the time, had a sort of monopoly,",
        "being one of the major, major importers.", "Now, you see, the coke game may done changed,",
        "but the relationships stay the same.", "Cubans fuck with the Haitians,", "See them stairs, pull in-front.",
        "Hey, go on and blow the horn for me.", "Shit, nigga you got motherfuckers hot!",
        "Man, come on down so I can get the fuck up outta here, dog.", "Shit, he got my word, and I got his four.",
        "Matter of fact, go ahead and call him.", "Call him now and tell him come to the club, and I got him.",
    ],
    "kulup": [
        "A'ight, I'll let him know.", "Alright, let's roll, nigga.",
        "A'ight, Big Mikes by the river, Westbrook Drive in Salton. Let's hit the club and drop this munyun.",
        "We really going to another strip club? Isn't that, like, a conflict of interest?",
        "First of all, you in Vice City, nigga..", "Second of all, this ain't no ordinary occasion.", "So what's the occasion?",
        "My dog, Big Mike, opening his new spot.", "He got a whole new concept.",
        "I told him I'd stop by, bless him with a few racks.", "How he talking, he finna bring the whole city out, nigga!",
        "That's why I had to come collect some pocket money", "before we showed up and showed out.",
        "How long we expecting to be out there, man? I'm kinda partied out.",
        "Ahh, you wanna go lay up with yo' woman, huh?", "Got you a fine ass Latina,",
        "gonna get you a body to body massage, lil' head rub, huh?", "Yeah.. I know exactly how that go.",
        "This look like a grand opening to you?", "We can park somewhere up here.",
        "Here you got the stripper poles and you know we gotta have the high ceilings.",
        "You ain't even got no strippers in here, but it smells like ass.",
        "Man, you got the bar, where they gonna be sellin' hookahs and liquor.",
        "And you talkin' 'bout ass; this shit, right here's gon' knock you off yo' ass.",
        "What the fuck? You gon' have niggas out here swimmin'?", "We ain't gon' be swimmin', you dummy, don't you see it?",
        "Imagine boats, yachts, Seasharks, all coming from the water to the club.",
        "Or, you could flip it around and come from the club, to the water.", "This the new wave, baby!",
    ],
}

PLAIN = ("Translate the following English video game subtitle into natural spoken Turkish. "
         "Produce only the Turkish translation.\n\n{text}")
WITH_CONTEXT = ("Translate the LAST line of this video game dialogue into natural spoken Turkish. The earlier lines are "
                "only context (the subtitles are cut into pieces, so a line may continue the one before it); use them to "
                "pick the right meaning of words and slang. Produce only the Turkish translation of the last line.\n\n"
                "Earlier lines:\n{context}\n\nLast line:\n{text}")


def gemma(prompt: str, port: int = 8099) -> str:
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 200,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body,
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as reply:
        return json.load(reply)["choices"][0]["message"]["content"].strip()


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    from dubzar.translate import OpusMtTranslator

    opus = OpusMtTranslator(threads=4)
    opus.load()
    rows, t_opus, t_plain, t_ctx = [], [], [], []
    for scene, lines in SCENES.items():
        for i, line in enumerate(lines):
            context = "\n".join(lines[max(0, i - 3): i])
            began = time.perf_counter(); a = opus.translate(line); t_opus.append(time.perf_counter() - began)
            began = time.perf_counter(); b = gemma(PLAIN.format(text=line)); t_plain.append(time.perf_counter() - began)
            began = time.perf_counter()
            c = gemma(WITH_CONTEXT.format(context=context, text=line)) if context else b
            t_ctx.append(time.perf_counter() - began)
            rows.append((scene, line, a, b, c))
    avg = lambda xs: sum(xs) / len(xs)
    lines_out = ["# Sahne bağlamı testi (GTA altyazıları)", "",
                 f"- Opus-MT {avg(t_opus):.2f} sn, Gemma 4 12B {avg(t_plain):.2f} sn, Gemma 4 + bağlam {avg(t_ctx):.2f} sn (satır başına)", "",
                 "| # | sahne | İngilizce | Opus-MT | Gemma 4 | Gemma 4 + bağlam |", "|---|---|---|---|---|---|"]
    for n, (scene, line, a, b, c) in enumerate(rows, 1):
        lines_out.append(f"| {n} | {scene} | {line} | {a} | {b} | {c} |")
    out = Path(__file__).parent / "scene_eval.md"
    out.write_text("\n".join(lines_out), encoding="utf-8")
    print("\n".join(lines_out[:4]))
    print("yazıldı:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
