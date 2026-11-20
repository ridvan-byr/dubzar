from math import gcd

import numpy as np
from scipy.signal import resample_poly

TARGET_SR = 16000


def to_mono_16k(samples: np.ndarray, sr: int) -> np.ndarray:
    """Convert audio of shape (n,) or (n, channels) to mono float32 at 16 kHz."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if sr != TARGET_SR:
        g = gcd(sr, TARGET_SR)
        x = resample_poly(x, TARGET_SR // g, sr // g).astype(np.float32)
    return x
