"""Performance modes. Light is what Dubzar always did (Opus-MT on the processor). High reads the screen with the graphics
card, looks more often and lets a large model (Gemma) re-translate the lines Opus-MT is unsure about: better subtitles for
more processor, graphics-card and memory use."""

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
    quality_model: bool = False   # a large model re-translates the lines the fast one is unsure about


PROFILES: dict[str, Profile] = {
    "light": Profile("light", "Hafif", "Az işlemci kullanır; oyunun yanında en güvenlisi.",
                     0.12, 0.30, 0.5, 4, False),
    "high": Profile("high", "Yüksek", "Daha iyi çeviri: Opus-MT'nin emin olmadığı satırları büyük bir model yeniden çevirir. "
                    "Okumayı ekran kartı yapar; ekran kartı belleğini (yaklaşık 8 GB) ve işlemciyi daha fazla kullanır. "
                    "Oyun başka cihazdaysa ya da güçlü bir kartın varsa önerilir.",
                    0.06, 0.12, 0.3, 2, True, True),
}
ORDER = ("light", "high")


def profile_for(name: str) -> Profile:
    return PROFILES.get(name, PROFILES["light"])
