"""Speech-edge detection and conservative cleanup for Continuous Voice Mode.

1.5.2 switches from single-sample near-zero detection to short-window RMS speech
activity.  This is much less likely to keep low-level TTS/codec tails that sound
like silence to the listener.  The detector is still deliberately conservative:
it keeps guards around the detected speech and never edits the text or SRT start.
"""
from __future__ import annotations

import numpy as np

# Roughly -50 dBFS absolute, with a small peak-relative component. TTS output is
# normally far above this threshold while synthetic/noise tails are below it.
ABS_RMS_FLOOR = 10 ** (-50.0 / 20.0)
RELATIVE_RMS = 0.008
MAX_RMS_THRESHOLD = 0.010
FRAME_MS = 20
HOP_MS = 5


def _frame_rms(audio: np.ndarray, rate: int):
    window = max(1, round(rate * FRAME_MS / 1000))
    hop = max(1, round(rate * HOP_MS / 1000))
    if len(audio) <= window:
        starts = np.array([0], dtype=np.int64)
    else:
        starts = np.arange(0, len(audio) - window + 1, hop, dtype=np.int64)
        last = len(audio) - window
        if starts[-1] != last:
            starts = np.append(starts, last)
    squared = audio.astype(np.float64) ** 2
    prefix = np.concatenate(([0.0], np.cumsum(squared)))
    stops = np.minimum(starts + window, len(audio))
    energy = prefix[stops] - prefix[starts]
    lengths = np.maximum(1, stops - starts)
    return starts, stops, np.sqrt(energy / lengths)


def active_bounds(samples, rate: int):
    """Return detected speech bounds ``(start, stop, threshold)``.

    ``stop`` is exclusive. If a valid non-silent signal cannot be detected,
    the whole input is returned. The detector is intended for TTS edges, not
    general VAD or removal of pauses inside a sentence.
    """
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not len(audio) or rate <= 0 or not np.isfinite(audio).all():
        return 0, len(audio), 0.0
    peak = float(np.max(np.abs(audio)))
    if peak <= 1e-7:
        return 0, len(audio), 0.0
    threshold = max(ABS_RMS_FLOOR, min(MAX_RMS_THRESHOLD, peak * RELATIVE_RMS))
    starts, stops, rms = _frame_rms(audio, rate)
    active = np.flatnonzero(rms >= threshold)
    if not len(active):
        # Fallback for unusually quiet but valid TTS. Do not destroy it.
        return 0, len(audio), threshold

    first, last = int(active[0]), int(active[-1])
    # Frame RMS becomes active slightly before a hard speech edge because the
    # analysis window overlaps it. Use the frame centre as the edge estimate;
    # preserve a true edge at sample zero/end when the boundary frame is active.
    first_width = int(stops[first] - starts[first])
    last_width = int(stops[last] - starts[last])
    start = 0 if first == 0 else int(starts[first] + first_width // 2)
    stop = len(audio) if last == len(rms) - 1 else int(stops[last] - last_width // 2)
    if stop <= start:
        return 0, len(audio), threshold
    return start, stop, threshold


def trim_edge_silence(samples, rate: int, enabled: bool, *, keep_lead_ms: int = 30,
                      keep_tail_ms: int = 45):
    """Return ``(audio, leading_seconds, trailing_seconds)``.

    Only edge material outside the RMS-detected speech region is removed. A
    short attack/release guard is retained so consonants and natural releases
    are not clipped. Internal pauses remain untouched.
    """
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not enabled or not len(audio) or rate <= 0 or not np.isfinite(audio).all():
        return audio.copy(), 0.0, 0.0
    start_active, stop_active, _ = active_bounds(audio, rate)
    if start_active == 0 and stop_active == len(audio):
        return audio.copy(), 0.0, 0.0
    keep_lead = round(rate * max(0, keep_lead_ms) / 1000)
    keep_tail = round(rate * max(0, keep_tail_ms) / 1000)
    start = max(0, start_active - keep_lead)
    stop = min(len(audio), stop_active + keep_tail)
    # Ignore microscopic trims; they add no audible continuity benefit.
    if start + (len(audio) - stop) < round(rate * 0.012):
        return audio.copy(), 0.0, 0.0
    return audio[start:stop].copy(), start / rate, (len(audio) - stop) / rate


def audible_end(samples, rate: int):
    """Return the exclusive last audible sample index using the same detector."""
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not len(audio):
        return 0
    _, stop, _ = active_bounds(audio, rate)
    return int(min(max(stop, 0), len(audio)))
