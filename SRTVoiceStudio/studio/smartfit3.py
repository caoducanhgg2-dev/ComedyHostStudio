"""Neighbor-aware speed smoothing used by Smart Fit 3.0."""
from __future__ import annotations

MAX_NEIGHBOR_DELTA = 0.10


def smooth_speed(candidate: float, previous: float | None, needed: float,
                 classification: str, minimum: float, maximum: float):
    """Limit avoidable speed jumps without ever creating a known overflow.

    A speed-up is smoothed only when the lower smoothed value is still at or
    above the speed required to fit the slot. Underfill slow-down decisions are
    left untouched because filling the requested transition gap has priority.
    """
    candidate = max(minimum, min(maximum, float(candidate)))
    if previous is None:
        return candidate, False
    previous = max(minimum, min(maximum, float(previous)))
    if candidate > previous + MAX_NEIGHBOR_DELTA:
        safe = previous + MAX_NEIGHBOR_DELTA
        if float(needed) <= safe + 1e-6:
            return max(minimum, min(maximum, safe)), True
    return candidate, False
