"""Conservative edge-silence cleanup for Continuous Voice Mode.

Only digital/near-digital silence outside the spoken region is removed.  The
function deliberately keeps a short guard before and after speech so consonant
attacks and natural releases are not clipped.  It never changes the SRT start
position and never time-stretches audio; timeline fitting remains the single
source of truth for duration.
"""
from __future__ import annotations

import numpy as np


def trim_edge_silence(samples, rate: int, enabled: bool):
    """Return ``(audio, leading_seconds, trailing_seconds)``.

    The threshold follows the signal peak but is capped low enough to preserve
    quiet phonemes.  All-silent/invalid inputs are returned unchanged so the
    existing renderer can raise its normal TTS validation error.
    """
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not enabled or not len(audio) or rate <= 0 or not np.isfinite(audio).all():
        return audio.copy(), 0.0, 0.0
    peak = float(np.max(np.abs(audio)))
    if peak <= 1e-7:
        return audio.copy(), 0.0, 0.0
    threshold = max(1e-5, min(7.5e-4, peak * 0.0015))
    active = np.flatnonzero(np.abs(audio) >= threshold)
    if not len(active):
        return audio.copy(), 0.0, 0.0
    keep_lead = round(rate * 0.030)
    keep_tail = round(rate * 0.045)
    start = max(0, int(active[0]) - keep_lead)
    stop = min(len(audio), int(active[-1]) + 1 + keep_tail)
    # Ignore microscopic trims; they add no audible continuity benefit and can
    # create needless cache invalidations.
    if start + (len(audio) - stop) < round(rate * 0.012):
        return audio.copy(), 0.0, 0.0
    return audio[start:stop].copy(), start / rate, (len(audio) - stop) / rate
