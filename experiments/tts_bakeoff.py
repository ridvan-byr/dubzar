"""TTS bake-off: same Turkish lines, several character voices and emotions.

Usage: python experiments/tts_bakeoff.py <base|trendyol> [out_dir]

Voices are described in words (VoxCPM2 "Voice Design"): no reference audio, no cloning.
Writes one wav per clip plus summary.csv (seconds to generate, real-time factor, peak GPU memory).
"""

import csv
import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from voxcpm import VoxCPM

CHARACTERS = {
    "genc_erkek": "A young man in his twenties, energetic, clear and confident voice",
    "yasli_kadin": "An elderly woman, warm voice, slightly raspy",
    "sert_asker": "A middle-aged man, deep gravelly voice, tough veteran soldier",
    "cocuk": "A child around eight years old, bright and curious voice",
}

# (emotion label, English style hint, Turkish line)
LINES = [
    ("notr", "calm and natural", "Kapıyı aç, vakit kaybetmeyelim."),
    ("ofkeli", "angry, shouting", "Bunu bana nasıl yaparsın? Sana güvenmiştim!"),
    ("fisilti", "whispering quietly", "Sessiz ol... Birisi geliyor."),
    ("uzgun", "sad and quiet, heavy hearted", "Onu kurtaramadım. Keşke zamanında yetişseydim."),
    ("heyecanli", "excited and breathless", "Bak, buldum! Hazine tam burada, hemen gel!"),
]

MODELS = {
    "base": ("openbmb/VoxCPM2", 10),
    "trendyol": ("Trendyol/Trendyol-TTS", 16),
}


def main() -> None:
    name = sys.argv[1]
    out = Path(sys.argv[2] if len(sys.argv) > 2 else f"bakeoff_out/{name}")
    out.mkdir(parents=True, exist_ok=True)
    model_id, steps = MODELS[name]

    print(f"loading {model_id} ...", flush=True)
    t0 = time.time()
    model = VoxCPM.from_pretrained(model_id, load_denoiser=False)
    print(f"loaded in {time.time() - t0:.0f}s", flush=True)
    sr = model.tts_model.sample_rate

    rows = []
    for char, description in CHARACTERS.items():
        for emotion, style, line in LINES:
            text = f"({description}, {style}){line}"
            path = out / f"{char}__{emotion}.wav"
            torch.cuda.reset_peak_memory_stats()
            start = time.time()
            try:
                wav = model.generate(text=text, cfg_value=2.0, inference_timesteps=steps)
            except Exception as exc:  # keep going: one bad clip must not stop the comparison
                print(f"FAILED {path.name}: {exc}", flush=True)
                rows.append([path.name, "FAILED", "", "", ""])
                continue
            took = time.time() - start
            sf.write(path, wav, sr)
            seconds = len(wav) / sr
            peak_gb = torch.cuda.max_memory_allocated() / 1e9
            rows.append([path.name, f"{seconds:.1f}", f"{took:.1f}", f"{took / seconds:.2f}", f"{peak_gb:.1f}"])
            print(f"{path.name}: {seconds:.1f}s audio in {took:.1f}s (rtf {took / seconds:.2f}, peak {peak_gb:.1f} GB)", flush=True)

    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["clip", "audio_s", "gen_s", "rtf", "peak_gpu_gb"], *rows])


if __name__ == "__main__":
    main()
