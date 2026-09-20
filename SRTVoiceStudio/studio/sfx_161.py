"""SRT Voice Studio 1.6.1 Auto SFX audibility patch.

This module deliberately patches the verified 1.6 engine at startup instead of
rewriting the whole renderer. Goals:
- keep the 48 kHz/no-resample/no-time-stretch guarantees;
- make Impact/Suspense audible on laptop and phone speakers by adding controlled
  mid-band energy while preserving the bass character;
- raise in-mix SFX audibility conservatively while never attenuating voice;
- keep the existing fail-closed QA/headroom guards.
"""
from __future__ import annotations

import numpy as np

from . import sfx as base
from .timeline import RATE

_BASE_SYNTHESIZE = base.synthesize_sfx
_BASE_SELF_TEST = base.self_test


def speaker_band_ratio(samples, rate: int = RATE) -> float:
    """Return spectral-energy ratio in a phone/laptop-friendly 250 Hz–6 kHz band."""
    x = np.asarray(samples, dtype=np.float64).reshape(-1)
    if not len(x) or not np.isfinite(x).all():
        return 0.0
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / rate)
    total = float(np.sum(spectrum)) + 1e-18
    return float(np.sum(spectrum[(freqs >= 250) & (freqs <= 6000)]) / total)


def synthesize_sfx(kind: str, seed_text: str = '', rate: int = RATE):
    """1.6.1 SFX synthesis with stronger mid-band audibility for bass-heavy cues."""
    if rate != RATE:
        raise ValueError('Auto SFX chỉ tạo trực tiếp ở master 48 kHz.')
    if kind == 'impact':
        duration = .25
        t = np.arange(round(rate * duration)) / rate
        decay = np.exp(-t * 12.5)
        raw = (
            base._tone(108, t)
            + .52 * base._tone(432, t, .20)
            + .24 * base._tone(864, t, .42)
        ) * decay
        return base._finish(raw, .010, .090, rate)
    if kind == 'suspense':
        duration = .50
        t = np.arange(round(rate * duration)) / rate
        decay = np.exp(-t * 3.5)
        slow_pulse = .78 + .22 * np.sin(2 * np.pi * 3.2 * t) ** 2
        raw = (
            base._tone(96, t)
            + .34 * base._tone(384, t, .24)
            + .17 * base._tone(768, t, .46)
        ) * decay * slow_pulse
        return base._finish(raw, .060, .135, rate)
    return _BASE_SYNTHESIZE(kind, seed_text, rate)


def mix_auto_sfx(master, captions, settings, rate: int = RATE):
    """Mix SFX at a perceptible but safe level without ever reducing voice."""
    enabled = bool(getattr(settings, 'auto_sfx', False))
    density = str(getattr(settings, 'sfx_density', 'Balanced'))
    strength = str(getattr(settings, 'sfx_strength', 'Medium'))
    if density not in base.DENSITIES or strength not in base.STRENGTHS:
        raise ValueError('Cấu hình Auto SFX không hợp lệ.')
    if not enabled:
        return dict(enabled=False, planned=0, mixed=0, rejected=0, events=[], max_mix_peak=0.0)

    events = base.plan_sfx(captions, settings.language, density)
    from .sfx_editor import apply_sfx_overrides
    events = apply_sfx_overrides(
        events, captions, getattr(settings, 'sfx_overrides', ()), settings.language)
    by_index = {c.index: c for c in captions}

    # 1.6.0 Medium was only ~20% of active voice RMS and could disappear under
    # continuous narration. 1.6.1 targets roughly -10 dB at Medium while still
    # retaining the exact same .88 peak/headroom protection.
    ratio = {'Light': .22, 'Medium': .32, 'Strong': .44}[strength]
    floor = {'Light': .009, 'Medium': .014, 'Strong': .019}[strength]
    ceiling = {'Light': .050, 'Medium': .072, 'Strong': .095}[strength]

    report, rejected, mixed, max_peak = [], 0, 0, 0.0
    for event in events:
        caption = by_index[event.caption_index]
        fx = synthesize_sfx(event.kind, f'{caption.index}|{caption.text}', rate)
        qa = base.inspect_sfx(fx, rate)
        if not qa['passed']:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False,
                               reason='qa:' + ','.join(qa['reasons'])))
            continue

        start = int(event.start_ms * 48)
        hard_stop = min(len(master), int(caption.end * 48))
        if hard_stop - start < round(.07 * rate):
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False,
                               reason='slot_too_short'))
            continue
        if len(fx) > hard_stop - start:
            fx = fx[:hard_stop - start].copy()
            fade = min(len(fx), round(.055 * rate))
            if fade > 1:
                fx[-fade:] *= np.sin(np.linspace(np.pi / 2, 0, fade)) ** 2
                fx[-1] = 0.0

        stop = start + len(fx)
        voice_start = int(caption.start * 48)
        voice_stop = min(len(master), int(caption.end * 48))
        voice = np.asarray(master[voice_start:voice_stop], dtype=np.float64)
        active = voice[np.abs(voice) >= .001]
        voice_rms = float(np.sqrt(np.mean(active * active))) if len(active) else .035
        fx64 = fx.astype(np.float64)
        fx_rms = float(np.sqrt(np.mean(fx64 * fx64))) + 1e-12
        event_scale = float(getattr(event, 'gain_scale', 1.0))
        target_rms = min(.12, min(ceiling * max(1.0, event_scale), max(floor, voice_rms * ratio * event_scale)))
        gain = min(1.0, target_rms / fx_rms)
        region = np.asarray(master[start:stop], dtype=np.float64)

        # Headroom reduction applies to SFX only. Voice samples are never scaled.
        for _ in range(14):
            candidate = region + fx64 * gain
            peak = float(np.max(np.abs(candidate))) if len(candidate) else 0.0
            if peak <= .88:
                break
            gain *= .76
        else:
            peak = 1.0

        if gain < .020 or peak > .88:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False,
                               reason='insufficient_headroom'))
            continue

        candidate = (region + fx64 * gain).astype(np.float32)
        if not np.isfinite(candidate).all() or float(np.max(np.abs(candidate))) > .88001:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False,
                               reason='post_mix_guard'))
            continue

        master[start:stop] = candidate
        mixed += 1
        max_peak = max(max_peak, float(np.max(np.abs(candidate))))
        effective_rms = fx_rms * gain
        report.append(dict(
            caption=caption.index,
            start_ms=event.start_ms,
            kind=event.kind,
            label=base.KIND_LABELS[event.kind],
            score=event.score,
            trigger=event.reason,
            mixed=True,
            gain=float(gain),
            qa_peak=qa['peak'],
            high_frequency_ratio=qa['high_frequency_ratio'],
            speaker_band_ratio=speaker_band_ratio(fx, rate),
            voice_rms=voice_rms,
            sfx_rms=effective_rms,
            relative_rms=(effective_rms / max(voice_rms, 1e-12)),
            manual=bool(getattr(event, 'manual', False)),
            gain_scale=float(getattr(event, 'gain_scale', 1.0)),
        ))

    return dict(enabled=True, planned=len(events), mixed=mixed, rejected=rejected,
                density=density, strength=strength, events=report, max_mix_peak=max_peak)


def self_test():
    """Frozen-app QA for 1.6.1 SFX safety plus speaker-band audibility."""
    for kind in base.KIND_LABELS:
        audio = synthesize_sfx(kind, 'frozen-self-test')
        qa = base.inspect_sfx(audio)
        if not qa['passed']:
            raise RuntimeError(f'SFX {kind} failed QA: {qa}')
        if kind in ('impact', 'suspense') and speaker_band_ratio(audio) < .08:
            raise RuntimeError(f'SFX {kind} speaker-band energy too low: {speaker_band_ratio(audio):.4f}')
    bad = np.ones(round(.2 * RATE), dtype=np.float32) * .4
    if base.inspect_sfx(bad)['passed']:
        raise RuntimeError('SFX QA failed to reject DC/click signal.')
    return 0


def apply_patch():
    """Install 1.6.1 functions before render/UI modules import them."""
    base.synthesize_sfx = synthesize_sfx
    base.mix_auto_sfx = mix_auto_sfx
    base.self_test = self_test
    return base
