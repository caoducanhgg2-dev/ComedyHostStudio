"""The sole post-DSP fitting implementation for production and Preview C."""
import numpy as np
from .audio import convert, normalize
from .timeline import RATE, TimelineError, validate
from .continuity import trim_edge_silence, audible_end

MIN_EFFECTIVE_SPEED = 0.88
CONTINUOUS_MIN_EFFECTIVE_SPEED = 0.86
MAX_EFFECTIVE_SPEED = 1.20
TARGET_TRAILING = 0.15
UNDERFILL_TRIGGER = 0.30
UNDERFILL_WARNING = 0.80
CONTINUOUS_TRIGGER = 0.08
CONTINUOUS_TOLERANCE = 0.035
CONTINUOUS_WARNING_EXCESS = 0.20


def fit_processed(samples, rate, slot, settings, emotion_tempo, folder, cancel, previous_speed=None):
    if not 1.0 <= settings.speed <= 1.2:
        raise ValueError('Speed phải nằm trong 1.00–1.20x.')
    if settings.overflow not in ('Safe Trim','Stop and Report'):
        raise ValueError('Overflow mode không hợp lệ.')
    if not 0.9 <= emotion_tempo <= 1.2:
        raise ValueError('Emotion tempo không hợp lệ.')
    continuous = bool(getattr(settings, 'continuous', False))
    target_ms = int(getattr(settings, 'continuous_target_ms', 100))
    if continuous and not 50 <= target_ms <= 250:
        raise ValueError('Continuous target phải nằm trong 50–250 ms.')

    configured_gap = max(0.0, float(settings.gap_ms) / 1000.0)
    target_transition = target_ms / 1000.0 if continuous else None
    # slots_for() has already removed the configured minimum gap from this slot.
    # Therefore a 100 ms Continuous target + 100 ms minimum gap means audio
    # should fill the slot itself; adding another 100 ms here would double-gap.
    target_trailing = max(0.0, target_transition - configured_gap) if continuous else TARGET_TRAILING
    min_effective = CONTINUOUS_MIN_EFFECTIVE_SPEED if continuous else MIN_EFFECTIVE_SPEED
    underfill_trigger = CONTINUOUS_TRIGGER if continuous else UNDERFILL_TRIGGER

    original_processed_duration = len(samples) / rate
    post_trim_start = post_trim_end = 0.0
    if continuous:
        # A second edge pass after emotion/FX is essential.  Some TTS and DSP
        # paths retain low-level tails that are technically non-zero but sound
        # silent. Smart Fit must measure the audible speech region, not raw PCM.
        samples, post_trim_start, post_trim_end = trim_edge_silence(
            samples, rate, True, keep_lead_ms=20, keep_tail_ms=35)
    if not len(samples) or not np.isfinite(samples).all():
        raise RuntimeError('Continuous Voice tạo audio sau DSP không hợp lệ.')

    available = slot.end - slot.start
    duration = len(samples) / rate
    requested = min(MAX_EFFECTIVE_SPEED, settings.speed * emotion_tempo)
    slot_seconds = available / RATE
    initial_duration = duration * emotion_tempo / requested
    initial_trailing = max(0.0, slot_seconds - initial_duration)
    underfill_detected = initial_trailing > (target_trailing + underfill_trigger if continuous else underfill_trigger)
    needed = duration / slot_seconds * emotion_tempo
    effective = requested
    classification = ('UNDERFILL' if slot_seconds - duration > underfill_trigger
                      else ('OVERFLOW' if duration > slot_seconds else 'FIT'))

    if settings.adaptive:
        if underfill_detected:
            target_duration = max(1 / RATE, slot_seconds - target_trailing)
            fill_speed = duration * emotion_tempo / target_duration
            ceiling = min(requested, 1.0, emotion_tempo) if classification == 'UNDERFILL' else requested
            effective = max(min_effective, min(ceiling, fill_speed))
        else:
            effective = max(requested, min(needed, 1.15))
            if needed > 1.15:
                effective = max(effective, min(needed, MAX_EFFECTIVE_SPEED))
    effective = max(min_effective, min(effective, MAX_EFFECTIVE_SPEED))
    neighbor_limited = False
    if bool(getattr(settings, 'smart_fit3', False)):
        from .smartfit3 import smooth_speed
        effective, neighbor_limited = smooth_speed(
            effective, previous_speed, needed, classification,
            min_effective, MAX_EFFECTIVE_SPEED)

    def converted_for(value):
        return convert(samples, rate, value / emotion_tempo, folder, cancel)

    fitted = converted_for(effective)
    refit_passes = 0
    # Closed-loop audible fit.  atempo and DSP can leave a different audible end
    # than their raw array length suggests, so measure the result and correct at
    # most twice.  We only slow when there is excess audible silence; no caption
    # start is moved and the hard naturalness floor remains enforced.
    if continuous and settings.adaptive:
        desired_active_seconds = max(1 / RATE, slot_seconds - target_trailing)
        for _ in range(2):
            clipped = fitted[:available]
            active_stop = audible_end(clipped, RATE)
            current_active_seconds = active_stop / RATE
            internal_gap = max(0.0, slot_seconds - current_active_seconds)
            if internal_gap <= target_trailing + CONTINUOUS_TOLERANCE:
                break
            if current_active_seconds <= 0.05 or effective <= min_effective + 1e-6:
                break
            correction = current_active_seconds / desired_active_seconds
            candidate = max(min_effective, min(effective, effective * correction))
            if candidate >= effective - 0.001:
                break
            effective = candidate
            fitted = converted_for(effective)
            refit_passes += 1

    fit_tempo = effective / emotion_tempo
    active_before_clip = audible_end(fitted, RATE) if continuous else len(fitted)
    raw_excess = max(0, len(fitted) - available)
    audible_excess = max(0, active_before_clip - available)
    if audible_excess and settings.overflow == 'Stop and Report':
        raise TimelineError(f'CAPTION {slot.caption.index} TOO LONG\nSlot: {available/RATE:.3f} s\n'
            f'Processed: {duration:.3f} s\nSpeed: {effective:.3f}x\n'
            f'Audible overflow: {audible_excess/RATE:.3f} s\nKhông export.')

    fitted = fitted[:available].copy()
    # Fade only when audible speech, not merely an inaudible processing tail,
    # crossed the boundary.
    if audible_excess:
        fade = min(len(fitted), 240)
        fitted[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    if settings.loudness:
        fitted = normalize(fitted)
    fitted = np.clip(fitted, -.89, .89)
    validate([slot], [len(fitted)], settings.gap_ms)

    raw_trailing = max(0.0, (available - len(fitted)) / RATE)
    active_stop = audible_end(fitted, RATE) if continuous else len(fitted)
    audible_internal_trailing = max(0.0, (available - active_stop) / RATE)
    transition_silence = audible_internal_trailing + configured_gap if continuous else audible_internal_trailing
    if continuous:
        underfilled = transition_silence > target_transition + CONTINUOUS_WARNING_EXCESS
    else:
        underfilled = audible_internal_trailing > UNDERFILL_WARNING

    speed_up = effective > requested + 1e-6
    slow_down = effective < requested - 1e-6
    if audible_excess:
        fit_status = 'TOO_LONG_TRIMMED'
    elif underfilled:
        fit_status = 'TOO_SHORT'
    elif speed_up:
        fit_status = 'SPEED_UP'
    elif slow_down:
        fit_status = 'SLOW_DOWN'
    else:
        fit_status = 'GOOD'

    at_floor = underfilled and effective <= min_effective + 1e-6
    if at_floor and continuous:
        warning = 'CONTINUOUS TARGET UNREACHABLE / SHORT SCRIPT'
    elif at_floor:
        warning = 'SHORT SCRIPT / REMAINING SILENCE'
    else:
        warning = ''

    record = dict(
        caption=slot.caption.index, start_sample=slot.start,
        end_sample=slot.start + len(fitted), allowed_end=slot.end,
        audible_end_sample=slot.start + active_stop,
        processed_seconds=duration, processed_seconds_before_continuity_trim=original_processed_duration,
        available_seconds=available / RATE, classification=classification,
        fit_status=fit_status, continuous_mode=continuous,
        target_transition_seconds=target_transition,
        target_trailing_seconds=target_trailing,
        configured_gap_seconds=configured_gap,
        speed=effective, emotion_tempo=emotion_tempo, fit_tempo=fit_tempo,
        requested_speed=requested, trimmed=bool(audible_excess),
        trimmed_samples=audible_excess, raw_tail_trimmed_samples=max(0, raw_excess-audible_excess),
        final_seconds=len(fitted) / RATE, overlaps=0,
        initial_trailing_seconds=initial_trailing,
        raw_trailing_silence=raw_trailing,
        internal_audible_trailing_silence=audible_internal_trailing,
        transition_silence=transition_silence,
        trailing_silence=audible_internal_trailing,
        underfill_detected=underfill_detected, underfilled=underfilled,
        underfill_adjusted=slow_down, speed_up=speed_up, slow_down=slow_down,
        underfilled_at_hard_minimum=at_floor,
        continuous_refit_passes=refit_passes,
        post_dsp_trimmed_start=post_trim_start,
        post_dsp_trimmed_end=post_trim_end,
        post_dsp_trimmed_seconds=post_trim_start + post_trim_end,
        minimum_effective_speed=min_effective,
        warning=warning,
        smart_fit3=bool(getattr(settings, 'smart_fit3', False)),
        smart_fit3_neighbor_limited=bool(neighbor_limited),
        previous_caption_speed=previous_speed)
    return fitted, record
