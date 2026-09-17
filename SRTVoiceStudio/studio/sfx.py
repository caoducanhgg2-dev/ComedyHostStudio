"""Deterministic Auto SFX for SRT Voice Studio 1.6.

Design goals:
- no downloaded/generative audio and no SFX time-stretch/pitch-resampling;
- synthesize directly at the 48 kHz master rate;
- every event starts/ends at zero with mandatory fades;
- reject non-finite, DC-heavy, clicky, clipped or high-frequency-heavy audio;
- mix SFX *under* the already rendered voice and reduce/skip it when headroom is low;
- conservative text cue detection, at most one event per caption and a minimum event spacing;
- place the event near the triggering word inside long captions, not blindly at caption start.

The safety gate is intentionally fail-closed: a rejected SFX is omitted while the
voice render continues normally.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import numpy as np

from .timeline import RATE

DENSITIES = ('Sparse', 'Balanced', 'Energetic')
STRENGTHS = ('Light', 'Medium', 'Strong')
KIND_LABELS = {
    'impact': 'Impact trầm',
    'chime': 'Chime thành công',
    'comic': 'Comic pop',
    'suspense': 'Nhấn hồi hộp',
    'transition': 'Transition tick',
    'accent': 'Accent nhẹ',
}
KIND_DURATION_MS = {
    'impact': 240,
    'chime': 540,
    'comic': 340,
    'suspense': 480,
    'transition': 260,
    'accent': 160,
}

@dataclass(frozen=True)
class SfxEvent:
    caption_index: int
    start_ms: int
    kind: str
    score: int
    reason: str


def _contains(value: str, phrases) -> int:
    return sum(1 for phrase in phrases if phrase in value)


def classify_sfx(text: str, language: str, density: str = 'Balanced'):
    """Return ``(kind, score, reason)`` or ``None``.

    Rules are intentionally lexical and deterministic. Auto SFX never invents
    scene events from weak context. Sparse requires a strong cue; Balanced
    accepts normal semantic cues; Energetic may also use punctuation.
    """
    if density not in DENSITIES:
        raise ValueError('SFX density không hợp lệ.')
    raw = str(text or '').strip()
    if not raw:
        return None
    value = raw if language == 'Japanese' else raw.casefold()
    if language == 'Japanese':
        groups = [
            ('impact', ('衝撃','激突','落下','落ちた','崩れ','倒れ','爆発','ぶつか','破壊'), 4),
            ('chime', ('完成','成功','やった','できた','達成','勝利','ついに','最高'), 4),
            ('comic', ('笑','面白','おもしろ','反則','冗談','なんちゃって','まさか'), 3),
            ('suspense', ('危険','怖','恐怖','不気味','怪しい','注意','謎','緊張'), 3),
            ('transition', ('次は','そして','その後','突然','ここから','一方で'), 2),
        ]
    else:
        groups = [
            ('impact', ('crash','smash','impact','hit the','dropped','fell','collapse','boom','collision'), 4),
            ('chime', ('finally','success','completed','complete','finished','victory','won','nailed it','amazing'), 4),
            ('comic', ('hilarious','funny','ridiculous','joke','just kidding','plot twist','seriously'), 3),
            ('suspense', ('danger','careful','scary','horror','ghost','creepy','suspicious','mystery','warning'), 3),
            ('transition', ('next','then','after that','suddenly','meanwhile','from here'), 2),
        ]
    candidates = []
    for order, (kind, phrases, weight) in enumerate(groups):
        hits = _contains(value, phrases)
        if hits:
            candidates.append((weight + min(2, hits - 1), -order, kind, phrases))
    bangs = raw.count('!') + raw.count('！')
    questions = raw.count('?') + raw.count('？')
    if density == 'Energetic' and bangs + questions:
        candidates.append((2 if bangs + questions >= 2 else 1, -99, 'accent', ()))
    if not candidates:
        return None
    score, _, kind, phrases = max(candidates)
    threshold = {'Sparse': 4, 'Balanced': 2, 'Energetic': 1}[density]
    if score < threshold:
        return None
    hit = next((p for p in phrases if p in value), 'dấu câu nhấn mạnh')
    return kind, int(score), str(hit)


def _cue_anchor_ms(caption, reason: str, kind: str, language: str) -> int:
    """Approximate cue position from text proportion, while keeping full SFX in-caption."""
    raw = str(caption.text or '')
    value = raw if language == 'Japanese' else raw.casefold()
    needle = reason if language == 'Japanese' else reason.casefold()
    pos = value.find(needle) if needle and needle != 'dấu câu nhấn mạnh' else -1
    if pos >= 0:
        ratio = (pos + max(1, len(needle)) * .5) / max(1, len(value))
    else:
        marks = [p for p in (value.find('!'), value.find('！'), value.find('?'), value.find('？')) if p >= 0]
        ratio = ((min(marks) + .5) / max(1, len(value))) if marks else .10
    ratio = max(.04, min(.92, ratio))
    span = max(1, int(caption.end - caption.start))
    desired = int(caption.start + span * ratio)
    earliest = int(caption.start + 45)
    latest = int(caption.end - KIND_DURATION_MS[kind] - 45)
    if latest < earliest:
        return earliest
    return max(earliest, min(latest, desired))


def plan_sfx(captions, language: str, density: str = 'Balanced'):
    """Plan conservative, cue-aligned events without touching audio."""
    if density not in DENSITIES:
        raise ValueError('SFX density không hợp lệ.')
    min_spacing = {'Sparse': 6000, 'Balanced': 3500, 'Energetic': 2200}[density]
    events = []
    last_ms = -10**12
    for caption in captions:
        result = classify_sfx(caption.text, language, density)
        if result is None:
            continue
        kind, score, reason = result
        anchor = _cue_anchor_ms(caption, reason, kind, language)
        if anchor - last_ms < min_spacing:
            continue
        events.append(SfxEvent(caption.index, anchor, kind, score, reason))
        last_ms = anchor
    return events


def _envelope(n: int, attack_s: float, release_s: float, rate: int = RATE):
    env = np.ones(n, dtype=np.float64)
    a = min(n // 2, max(2, round(rate * attack_s)))
    r = min(n // 2, max(2, round(rate * release_s)))
    env[:a] = np.sin(np.linspace(0, np.pi / 2, a, endpoint=True)) ** 2
    env[-r:] = np.sin(np.linspace(np.pi / 2, 0, r, endpoint=True)) ** 2
    env[0] = 0.0
    env[-1] = 0.0
    return env


def _tone(freq: float, t, phase=0.0):
    return np.sin(2 * np.pi * float(freq) * t + phase)


def _finish(raw, attack, release, rate=RATE):
    x = np.asarray(raw, dtype=np.float64).reshape(-1)
    env = _envelope(len(x), attack, release, rate)
    x *= env
    # Remove residual DC after the asymmetric decay/envelope. Subtract a
    # correction shaped by the same zero-edge envelope so no click is created.
    if len(x):
        mean_env = float(np.mean(env))
        if mean_env > 1e-12:
            x -= (float(np.mean(x)) / mean_env) * env
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > 1e-12:
        x *= 0.58 / peak
    if len(x):
        x[0] = 0.0; x[-1] = 0.0
    return x.astype(np.float32)


def synthesize_sfx(kind: str, seed_text: str = '', rate: int = RATE):
    """Create one clean mono effect natively at ``rate``; never resample it."""
    if rate != RATE:
        raise ValueError('Auto SFX chỉ tạo trực tiếp ở master 48 kHz.')
    # Keep a deterministic seed contract without introducing broadband random noise.
    hashlib.sha256(str(seed_text).encode('utf-8')).digest()
    if kind == 'impact':
        duration = .24; t = np.arange(round(rate * duration)) / rate
        decay = np.exp(-t * 13.0)
        raw = (_tone(105, t) + .38 * _tone(210, t, .25) + .12 * _tone(315, t, .5)) * decay
        return _finish(raw, .010, .085, rate)
    if kind == 'chime':
        duration = .54; t = np.arange(round(rate * duration)) / rate
        decay = np.exp(-t * 5.3)
        raw = (_tone(660, t) + .48 * _tone(990, t, .12) + .18 * _tone(1320, t, .2)) * decay
        return _finish(raw, .012, .130, rate)
    if kind == 'comic':
        duration = .34; n = round(rate * duration); raw = np.zeros(n, dtype=np.float64)
        pulse_len = round(rate * .105)
        tp = np.arange(pulse_len) / rate
        pulse = (_tone(310, tp) + .28 * _tone(620, tp)) * np.exp(-tp * 19.0)
        pulse *= _envelope(pulse_len, .006, .055, rate)
        raw[:pulse_len] += pulse
        offset = round(rate * .145); raw[offset:offset + pulse_len] += pulse * .72
        return _finish(raw, .004, .045, rate)
    if kind == 'suspense':
        duration = .48; t = np.arange(round(rate * duration)) / rate
        raw = (_tone(92, t) + .22 * _tone(184, t, .3)) * np.exp(-t * 3.7)
        return _finish(raw, .055, .120, rate)
    if kind == 'transition':
        duration = .26; t = np.arange(round(rate * duration)) / rate
        raw = (_tone(520, t) + .35 * _tone(780, t, .2)) * np.exp(-t * 12.0)
        return _finish(raw, .008, .070, rate)
    if kind == 'accent':
        duration = .16; t = np.arange(round(rate * duration)) / rate
        raw = (_tone(240, t) + .25 * _tone(480, t, .1)) * np.exp(-t * 18.0)
        return _finish(raw, .006, .050, rate)
    raise ValueError('Loại SFX không hợp lệ.')


def inspect_sfx(samples, rate: int = RATE):
    """Fail-closed artifact gate for generated effects."""
    x = np.asarray(samples, dtype=np.float64).reshape(-1)
    reasons = []
    if rate != RATE:
        reasons.append('sample_rate')
    if len(x) < round(.06 * rate) or len(x) > round(1.2 * rate):
        reasons.append('duration')
    if not len(x) or not np.isfinite(x).all():
        reasons.append('non_finite')
        return {'passed': False, 'reasons': reasons}
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x * x)))
    dc = abs(float(np.mean(x)))
    max_step = float(np.max(np.abs(np.diff(x)))) if len(x) > 1 else 0.0
    edge = max(abs(float(x[0])), abs(float(x[-1])))
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / rate)
    total = float(np.sum(spectrum)) + 1e-18
    hf_ratio = float(np.sum(spectrum[freqs >= 12000]) / total)
    if not .008 <= peak <= .70:
        reasons.append('peak')
    if rms <= 1e-5:
        reasons.append('silent')
    if dc > max(.0012, rms * .015):
        reasons.append('dc')
    if edge > 1e-4:
        reasons.append('edge_click')
    if max_step > .18:
        reasons.append('sample_click')
    if hf_ratio > .035:
        reasons.append('high_frequency_hiss')
    return dict(passed=not reasons, reasons=reasons, peak=peak, rms=rms, dc=dc,
                max_step=max_step, edge=edge, high_frequency_ratio=hf_ratio)


def mix_auto_sfx(master, captions, settings, rate: int = RATE):
    """Mix accepted SFX below the voice without changing the SRT timeline."""
    enabled = bool(getattr(settings, 'auto_sfx', False))
    density = str(getattr(settings, 'sfx_density', 'Balanced'))
    strength = str(getattr(settings, 'sfx_strength', 'Medium'))
    if density not in DENSITIES or strength not in STRENGTHS:
        raise ValueError('Cấu hình Auto SFX không hợp lệ.')
    if not enabled:
        return dict(enabled=False, planned=0, mixed=0, rejected=0, events=[], max_mix_peak=0.0)
    events = plan_sfx(captions, settings.language, density)
    by_index = {c.index: c for c in captions}
    ratio = {'Light': .14, 'Medium': .20, 'Strong': .27}[strength]
    report, rejected, mixed, max_peak = [], 0, 0, 0.0
    for event in events:
        caption = by_index[event.caption_index]
        fx = synthesize_sfx(event.kind, f'{caption.index}|{caption.text}', rate)
        qa = inspect_sfx(fx, rate)
        if not qa['passed']:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False,
                               reason='qa:' + ','.join(qa['reasons'])))
            continue
        start = int(event.start_ms * 48)
        hard_stop = min(len(master), int(caption.end * 48))
        if hard_stop - start < round(.07 * rate):
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False, reason='slot_too_short'))
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
        fx_rms = float(np.sqrt(np.mean(fx.astype(np.float64) ** 2))) + 1e-12
        target_rms = min(.055, max(.006, voice_rms * ratio))
        gain = min(.75, target_rms / fx_rms)
        region = np.asarray(master[start:stop], dtype=np.float64)
        # Reduce only SFX until the mixed peak is safe; never attenuate voice.
        for _ in range(12):
            candidate = region + fx.astype(np.float64) * gain
            peak = float(np.max(np.abs(candidate))) if len(candidate) else 0.0
            if peak <= .88:
                break
            gain *= .72
        else:
            peak = 1.0
        if gain < .025 or peak > .88:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False, reason='insufficient_headroom'))
            continue
        candidate = (region + fx.astype(np.float64) * gain).astype(np.float32)
        if not np.isfinite(candidate).all() or float(np.max(np.abs(candidate))) > .88001:
            rejected += 1
            report.append(dict(caption=caption.index, kind=event.kind, mixed=False, reason='post_mix_guard'))
            continue
        master[start:stop] = candidate
        mixed += 1; max_peak = max(max_peak, float(np.max(np.abs(candidate))))
        report.append(dict(caption=caption.index, start_ms=event.start_ms, kind=event.kind,
                           label=KIND_LABELS[event.kind], score=event.score, trigger=event.reason,
                           mixed=True, gain=float(gain), qa_peak=qa['peak'],
                           high_frequency_ratio=qa['high_frequency_ratio']))
    return dict(enabled=True, planned=len(events), mixed=mixed, rejected=rejected,
                density=density, strength=strength, events=report, max_mix_peak=max_peak)


def self_test():
    """Fast frozen-app SFX gate; returns process-style status code."""
    for kind in KIND_LABELS:
        a = synthesize_sfx(kind, 'frozen-self-test')
        qa = inspect_sfx(a)
        if not qa['passed']:
            raise RuntimeError(f'SFX {kind} failed QA: {qa}')
    bad = np.ones(round(.2 * RATE), dtype=np.float32) * .4
    if inspect_sfx(bad)['passed']:
        raise RuntimeError('SFX QA failed to reject DC/click signal.')
    return 0
