"""The sole post-DSP fitting implementation for production and Preview C."""
import numpy as np
from .audio import convert, normalize
from .timeline import RATE, TimelineError, validate

MIN_EFFECTIVE_SPEED = 0.88
MAX_EFFECTIVE_SPEED = 1.20
TARGET_TRAILING = 0.15
UNDERFILL_TRIGGER = 0.30
UNDERFILL_WARNING = 0.80
CONTINUOUS_TRIGGER = 0.16
CONTINUOUS_WARNING = 0.50


def fit_processed(samples, rate, slot, settings, emotion_tempo, folder, cancel):
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
    target_trailing = target_ms / 1000 if continuous else TARGET_TRAILING
    underfill_trigger = CONTINUOUS_TRIGGER if continuous else UNDERFILL_TRIGGER
    underfill_warning = CONTINUOUS_WARNING if continuous else UNDERFILL_WARNING
    available = slot.end-slot.start
    duration = len(samples)/rate
    # B already includes emotion tempo. Account for it exactly once, including
    # its interaction with user speed and the measured effect tail.
    requested = min(MAX_EFFECTIVE_SPEED, settings.speed*emotion_tempo)
    slot_seconds = available/RATE
    initial_duration = duration*emotion_tempo/requested
    initial_trailing = max(0.0, slot_seconds-initial_duration)
    underfill_detected = initial_trailing > underfill_trigger
    needed = duration/slot_seconds*emotion_tempo
    effective = requested
    # Smart Timeline Fit 2.0 classifies measured B before extra speed changes.
    classification = 'UNDERFILL' if slot_seconds-duration > underfill_trigger else ('OVERFLOW' if duration > slot_seconds else 'FIT')
    if settings.adaptive:
        if underfill_detected:
            # Never move another caption. Continuous mode aims for a tighter
            # tail while retaining the same hard 0.88x naturalness floor.
            target_duration = max(1/RATE, slot_seconds-target_trailing)
            fill_speed = duration*emotion_tempo/target_duration
            ceiling = min(requested, 1.0, emotion_tempo) if classification == 'UNDERFILL' else requested
            effective = max(MIN_EFFECTIVE_SPEED, min(ceiling,fill_speed))
        else:
            effective = max(requested,min(needed,1.15))
            if needed > 1.15:
                effective = max(effective,min(needed,MAX_EFFECTIVE_SPEED))
    effective = max(MIN_EFFECTIVE_SPEED,min(effective,MAX_EFFECTIVE_SPEED))
    fit_tempo = effective/emotion_tempo
    fitted = convert(samples,rate,fit_tempo,folder,cancel)
    excess = max(0,len(fitted)-available)
    if excess and settings.overflow == 'Stop and Report':
        raise TimelineError(f'CAPTION {slot.caption.index} TOO LONG\nSlot: {available/RATE:.3f} s\n'
            f'Processed: {duration:.3f} s\nSpeed: {effective:.3f}x\n'
            f'Adjusted: {len(fitted)/RATE:.3f} s\nKhông export.')
    fitted = fitted[:available].copy()
    if excess:
        fade = min(len(fitted),240)
        fitted[-fade:] *= np.linspace(1,0,fade,dtype=np.float32)
    if settings.loudness:
        fitted = normalize(fitted)
    fitted = np.clip(fitted,-.89,.89)
    # The slot already incorporates next-start minus gap. A second, whole-SRT
    # validation remains in render before the master is encoded.
    validate([slot],[len(fitted)],settings.gap_ms)
    trailing = max(0.0,(available-len(fitted))/RATE)
    underfilled = trailing > underfill_warning
    speed_up = effective > requested+1e-6
    slow_down = effective < requested-1e-6
    if excess:
        fit_status = 'TOO_LONG_TRIMMED'
    elif underfilled:
        fit_status = 'TOO_SHORT'
    elif speed_up:
        fit_status = 'SPEED_UP'
    elif slow_down:
        fit_status = 'SLOW_DOWN'
    else:
        fit_status = 'GOOD'
    record = dict(caption=slot.caption.index,start_sample=slot.start,
        end_sample=slot.start+len(fitted),allowed_end=slot.end,
        processed_seconds=duration,available_seconds=available/RATE,classification=classification,
        fit_status=fit_status,continuous_mode=continuous,target_trailing_seconds=target_trailing,
        speed=effective,emotion_tempo=emotion_tempo,fit_tempo=fit_tempo,
        requested_speed=requested,trimmed=bool(excess),trimmed_samples=excess,
        final_seconds=len(fitted)/RATE,overlaps=0,
        initial_trailing_seconds=initial_trailing, trailing_silence=trailing,
        underfill_detected=underfill_detected, underfilled=underfilled,
        underfill_adjusted=slow_down,
        speed_up=speed_up, slow_down=slow_down,
        underfilled_at_hard_minimum=underfilled and effective <= MIN_EFFECTIVE_SPEED+1e-6,
        warning='SHORT SCRIPT / REMAINING SILENCE' if underfilled and effective <= MIN_EFFECTIVE_SPEED+1e-6 else '')
    return fitted,record
