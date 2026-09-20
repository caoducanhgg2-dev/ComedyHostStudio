"""Manual SFX cue overrides for SRT Voice Studio 1.7."""
from __future__ import annotations

from dataclasses import dataclass
from .sfx import KIND_LABELS, KIND_DURATION_MS


@dataclass(frozen=True)
class EditedSfxEvent:
    caption_index: int
    start_ms: int
    kind: str
    score: int
    reason: str
    gain_scale: float = 1.0
    manual: bool = False


def _normalise_override(value):
    if not isinstance(value, dict):
        return None
    try:
        caption = int(value.get("caption"))
    except (TypeError, ValueError):
        return None
    if caption < 1:
        return None
    enabled = bool(value.get("enabled", True))
    kind = value.get("kind")
    if kind is not None:
        kind = str(kind)
        if kind not in KIND_LABELS:
            return None
    try:
        offset_ms = max(-1500, min(1500, int(value.get("offset_ms", 0))))
        gain_scale = max(.25, min(2.0, float(value.get("gain_scale", 1.0))))
    except (TypeError, ValueError):
        return None
    return dict(caption=caption, enabled=enabled, kind=kind,
                offset_ms=offset_ms, gain_scale=gain_scale)


def apply_sfx_overrides(events, captions, overrides, language=None):
    """Apply per-caption disable/replace/offset/level edits after auto planning."""
    by_caption = {c.index: c for c in captions}
    edits = {}
    for raw in tuple(overrides or ()):
        value = _normalise_override(raw)
        if value is not None and value["caption"] in by_caption:
            edits[value["caption"]] = value

    out = []
    seen = set()
    for event in events:
        edit = edits.get(event.caption_index)
        if edit and not edit["enabled"]:
            seen.add(event.caption_index)
            continue
        caption = by_caption[event.caption_index]
        kind = edit["kind"] if edit and edit["kind"] else event.kind
        start = int(event.start_ms + (edit["offset_ms"] if edit else 0))
        earliest = int(caption.start + 20)
        latest = int(caption.end - KIND_DURATION_MS[kind] - 20)
        start = earliest if latest < earliest else max(earliest, min(latest, start))
        out.append(EditedSfxEvent(
            caption_index=event.caption_index,
            start_ms=start,
            kind=kind,
            score=event.score,
            reason=("manual:" + event.reason) if edit else event.reason,
            gain_scale=edit["gain_scale"] if edit else 1.0,
            manual=bool(edit),
        ))
        seen.add(event.caption_index)

    # A manual cue may intentionally add SFX where the conservative auto planner
    # found no lexical cue.
    for caption_index, edit in edits.items():
        if caption_index in seen or not edit["enabled"] or not edit["kind"]:
            continue
        caption = by_caption[caption_index]
        kind = edit["kind"]
        earliest = int(caption.start + 20)
        latest = int(caption.end - KIND_DURATION_MS[kind] - 20)
        base = int(caption.start + 120 + edit["offset_ms"])
        start = earliest if latest < earliest else max(earliest, min(latest, base))
        out.append(EditedSfxEvent(
            caption_index=caption_index,
            start_ms=start,
            kind=kind,
            score=99,
            reason="manual",
            gain_scale=edit["gain_scale"],
            manual=True,
        ))
    out.sort(key=lambda e: (e.start_ms, e.caption_index))
    return out
