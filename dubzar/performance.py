"""Performance modes: how often the screen is looked at and what does the reading. Light is what Dubzar always did;
each step trades more processor and graphics-card use for subtitles that appear sooner."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    label: str            # shown in the panel
    hint: str             # what it costs, said plainly
    poll_s: float         # pause between looks at the subtitle strip while a conversation goes on
    idle_poll_s: float    # ... and after a long quiet time
    corner_poll_s: float  # pause between looks at the corners (quest goals)
    ocr_threads: int
    gpu_ocr: bool         # read the text with the graphics card (falls back to the processor when there is none)


PROFILES: dict[str, Profile] = {
    "light": Profile("light", "Hafif", "Az işlemci kullanır; oyunun yanında en güvenlisi.",
                     0.12, 0.30, 0.5, 4, False),
    "medium": Profile("medium", "Orta", "Daha sık bakar: altyazı biraz erken çıkar, işlemci biraz daha çalışır.",
                      0.08, 0.20, 0.4, 4, False),
    "high": Profile("high", "Yüksek", "Okumayı ekran kartı yapar, çok sık bakar: en erken altyazı; ekran kartı ve "
                    "işlemciyi daha fazla kullanır. Oyun başka cihazdaysa (konsol) önerilir.",
                    0.06, 0.12, 0.3, 2, True),
}
ORDER = ("light", "medium", "high")


def profile_for(name: str) -> Profile:
    return PROFILES.get(name, PROFILES["light"])
