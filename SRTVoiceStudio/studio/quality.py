"""Automatic post-render quality control for measurable production defects."""
from __future__ import annotations

import math
import tempfile
from pathlib import Path
import numpy as np


def measure_master(samples, chunk_samples: int = 1_000_000) -> dict:
    """Measure a disk-backed or in-memory mono float master without copying it."""
    n = int(len(samples))
    if n <= 0:
        return dict(peak=0.0, rms=0.0, dc=0.0, clipping_samples=0)
    peak = 0.0
    total = 0.0
    squares = 0.0
    clipped = 0
    for start in range(0, n, chunk_samples):
        x = np.asarray(samples[start:start + chunk_samples], dtype=np.float64)
        if not np.isfinite(x).all():
            return dict(peak=float("inf"), rms=float("inf"), dc=float("inf"),
                        clipping_samples=n, non_finite=True)
        if len(x):
            peak = max(peak, float(np.max(np.abs(x))))
            total += float(np.sum(x))
            squares += float(np.sum(x * x))
            clipped += int(np.count_nonzero(np.abs(x) >= .995))
    return dict(
        peak=peak,
        rms=math.sqrt(max(0.0, squares / n)),
        dc=abs(total / n),
        clipping_samples=clipped,
        non_finite=False,
    )


def analyze_render(summary: dict) -> dict:
    """Return PASS/WARN/FAIL and machine-readable issues from a render summary."""
    issues = []
    severe = []

    overlaps = int(summary.get("overlaps", 0) or 0)
    if overlaps:
        severe.append(dict(code="OVERLAP", count=overlaps,
                           message=f"{overlaps} vị trí chồng tiếng."))

    metrics = dict(summary.get("master_metrics") or {})
    if metrics.get("non_finite"):
        severe.append(dict(code="NON_FINITE_AUDIO", count=1,
                           message="Master có mẫu audio không hợp lệ."))
    clipping = int(metrics.get("clipping_samples", 0) or 0)
    if clipping:
        severe.append(dict(code="CLIPPING", count=clipping,
                           message=f"Phát hiện {clipping} sample clipping trong master."))
    if float(metrics.get("dc", 0.0) or 0.0) > .004:
        issues.append(dict(code="DC_OFFSET", count=1,
                           message="DC offset master cao hơn ngưỡng khuyến nghị."))

    encoded = dict(summary.get("encoded_metrics") or {})
    if encoded:
        if encoded.get("non_finite"):
            severe.append(dict(code="ENCODE_NON_FINITE", count=1,
                               message="MP3 decode kiểm tra có mẫu audio không hợp lệ."))
        encoded_fraction = float(encoded.get("clipping_fraction", 0.0) or 0.0)
        encoded_peak = float(encoded.get("peak", 0.0) or 0.0)
        if encoded_peak > 1.20 or encoded_fraction > .005:
            severe.append(dict(code="ENCODE_CLIPPING", count=int(encoded.get("clipping_samples", 0) or 0),
                               message="MP3 cuối có mức overshoot/clipping vượt ngưỡng an toàn."))
        if float(encoded.get("max_step", 0.0) or 0.0) > .85:
            issues.append(dict(code="ENCODE_CLICK_SPIKE", count=1,
                               message="MP3 cuối có bước nhảy sample lớn; nên nghe kiểm tra click/rẹt."))
        expected = float(summary.get("duration_ms", 0) or 0) / 1000.0
        actual = float(encoded.get("duration_seconds", 0.0) or 0.0)
        drift = abs(actual - expected)
        if expected > 0 and drift > .20:
            severe.append(dict(code="ENCODE_DURATION_DRIFT", count=1,
                               message=f"Thời lượng MP3 lệch {drift:.3f}s so với timeline SRT."))

    trimmed = int(summary.get("safely_trimmed", 0) or 0)
    if trimmed:
        issues.append(dict(code="TRIMMED_CAPTIONS", count=trimmed,
                           message=f"{trimmed} caption đã phải cắt an toàn."))

    short = int(summary.get("underfilled_after_hard_minimum", 0) or 0)
    if short:
        issues.append(dict(code="SHORT_SCRIPT", count=short,
                           message=f"{short} caption vẫn thiếu voice ở tốc độ tối thiểu."))

    long_gaps = int(summary.get("transitions_over_08", 0) or 0)
    if long_gaps:
        issues.append(dict(code="LONG_TRANSITIONS", count=long_gaps,
                           message=f"{long_gaps} chuyển câu có khoảng lặng > 0.8 giây."))

    rejected = int(summary.get("sfx_rejected", 0) or 0)
    planned = int(summary.get("sfx_planned", 0) or 0)
    mixed = int(summary.get("sfx_mixed", 0) or 0)
    if rejected:
        issues.append(dict(code="SFX_REJECTED", count=rejected,
                           message=f"{rejected} SFX bị QA loại."))
    if bool(summary.get("auto_sfx")) and planned and mixed == 0:
        issues.append(dict(code="SFX_INAUDIBLE_OR_REJECTED", count=planned,
                           message="Auto SFX bật nhưng không có cue nào được trộn."))

    all_issues = severe + issues
    status = "FAIL" if severe else ("WARN" if issues else "PASS")
    return {
        "status": status,
        "issues": all_issues,
        "issue_count": len(all_issues),
        "severe_count": len(severe),
    }


def format_quality(report: dict) -> str:
    status = str(report.get("status", "WARN"))
    issues = list(report.get("issues") or [])
    if not issues:
        return f"QC {status} · không phát hiện lỗi đo được."
    lines = [f"QC {status} · {len(issues)} vấn đề cần chú ý"]
    lines.extend(f"• {item.get('message', item.get('code', 'Issue'))}" for item in issues)
    return "\n".join(lines)


def measure_raw_float_file(path, rate: int = 48000, chunk_samples: int = 1_000_000) -> dict:
    """Chunked metrics for mono f32le without loading the complete file."""
    path = Path(path)
    total_count = 0
    total = 0.0
    squares = 0.0
    peak = 0.0
    clipped = 0
    max_step = 0.0
    previous = None
    with path.open("rb") as stream:
        while True:
            x = np.fromfile(stream, dtype="<f4", count=chunk_samples)
            if not len(x):
                break
            y = x.astype(np.float64, copy=False)
            if not np.isfinite(y).all():
                return dict(peak=float("inf"), rms=float("inf"), dc=float("inf"),
                            clipping_samples=total_count + len(y), clipping_fraction=1.0,
                            non_finite=True, samples=total_count + len(y),
                            duration_seconds=(total_count + len(y)) / rate,
                            max_step=float("inf"))
            total_count += len(y)
            peak = max(peak, float(np.max(np.abs(y))))
            total += float(np.sum(y))
            squares += float(np.sum(y * y))
            clipped += int(np.count_nonzero(np.abs(y) >= .995))
            if previous is not None and len(y):
                max_step = max(max_step, abs(float(y[0]) - previous))
            if len(y) > 1:
                max_step = max(max_step, float(np.max(np.abs(np.diff(y)))))
            previous = float(y[-1])
    if total_count <= 0:
        return dict(peak=0.0, rms=0.0, dc=0.0, clipping_samples=0,
                    clipping_fraction=0.0, non_finite=False, samples=0,
                    duration_seconds=0.0, max_step=0.0)
    return dict(
        peak=peak,
        rms=math.sqrt(max(0.0, squares / total_count)),
        dc=abs(total / total_count),
        clipping_samples=clipped,
        clipping_fraction=clipped / total_count,
        non_finite=False,
        samples=total_count,
        duration_seconds=total_count / rate,
        max_step=max_step,
    )


def measure_encoded_mp3(path, folder, cancel) -> dict:
    """Decode the staged final MP3 to float PCM and verify the encoded result."""
    from .audio import run
    from .paths import executable
    from .timeline import RATE
    fd, raw_name = tempfile.mkstemp(prefix="qc-final-", suffix=".raw", dir=folder)
    import os
    os.close(fd)
    raw = Path(raw_name)
    try:
        run([executable("ffmpeg"), "-nostdin", "-v", "error", "-y",
             "-i", str(path), "-ar", str(RATE), "-ac", "1",
             "-f", "f32le", str(raw)], cancel)
        return measure_raw_float_file(raw, RATE)
    finally:
        raw.unlink(missing_ok=True)
