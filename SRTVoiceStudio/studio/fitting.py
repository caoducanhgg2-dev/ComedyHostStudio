"""The sole post-DSP fitting implementation for production and Preview C."""
import numpy as np
from .audio import convert, normalize
from .timeline import RATE, TimelineError, validate

MIN_EFFECTIVE_SPEED = 0.88
MAX_EFFECTIVE_SPEED = 1.20
TARGET_TRAILING = 0.20
UNDERFILL_TRIGGER = 0.30
UNDERFILL_WARNING = 0.40

def fit_processed(samples, rate, slot, settings, emotion_tempo, folder, cancel):
    if not 1.0 <= settings.speed <= 1.2:
        raise ValueError('Speed phải nằm trong 1.00–1.20x.')
    if settings.overflow not in ('Safe Trim','Stop and Report'):
        raise ValueError('Overflow mode không hợp lệ.')
    if not 0.9 <= emotion_tempo <= 1.2:
        raise ValueError('Emotion tempo không hợp lệ.')
    available = slot.end-slot.start
    duration = len(samples)/rate
    # B already includes emotion tempo. Account for it exactly once, including
    # its interaction with user speed and the measured effect tail.
    requested = min(MAX_EFFECTIVE_SPEED, settings.speed*emotion_tempo)
    slot_seconds = available/RATE
    initial_duration = duration*emotion_tempo/requested
    initial_trailing = max(0.0, slot_seconds-initial_duration)
    underfill_detected = initial_trailing > UNDERFILL_TRIGGER
    needed = duration/slot_seconds*emotion_tempo
    effective = requested
    if settings.adaptive:
        if underfill_detected:
            # Never move another caption. At the 0.88x floor, a short script can
            # still leave silence; that is a warning, not a timeline failure.
            target_duration = max(1/RATE, slot_seconds-TARGET_TRAILING)
            fill_speed = duration*emotion_tempo/target_duration
            effective = max(MIN_EFFECTIVE_SPEED, min(requested,fill_speed))
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
    underfilled = trailing > UNDERFILL_WARNING
    record = dict(caption=slot.caption.index,start_sample=slot.start,
        end_sample=slot.start+len(fitted),allowed_end=slot.end,
        processed_seconds=duration,available_seconds=available/RATE,
        speed=effective,emotion_tempo=emotion_tempo,fit_tempo=fit_tempo,
        requested_speed=requested,trimmed=bool(excess),trimmed_samples=excess,
        final_seconds=len(fitted)/RATE,overlaps=0,
        initial_trailing_seconds=initial_trailing, trailing_silence=trailing,
        underfill_detected=underfill_detected, underfilled=underfilled,
        underfill_adjusted=effective < requested-1e-6,
        speed_up=effective > requested+1e-6, slow_down=effective < requested-1e-6,
        underfilled_at_hard_minimum=underfilled and effective <= MIN_EFFECTIVE_SPEED+1e-6,
        warning='SHORT SCRIPT / UNDERFILLED SLOT' if underfilled else '')
    return fitted,record
