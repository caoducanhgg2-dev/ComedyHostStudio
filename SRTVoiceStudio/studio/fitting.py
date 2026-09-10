"""The sole post-DSP fitting implementation for production and Preview C."""
import numpy as np
from .audio import convert, normalize
from .timeline import RATE, TimelineError, validate

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
    requested = min(1.2, settings.speed*emotion_tempo)
    needed = duration/(available/RATE)*emotion_tempo
    effective = max(requested,min(needed,1.15)) if settings.adaptive else requested
    if settings.adaptive and needed > 1.15:
        effective = max(effective,min(needed,1.20))
    effective = min(effective,1.20)
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
    record = dict(caption=slot.caption.index,start_sample=slot.start,
        end_sample=slot.start+len(fitted),allowed_end=slot.end,
        processed_seconds=duration,available_seconds=available/RATE,
        speed=effective,emotion_tempo=emotion_tempo,fit_tempo=fit_tempo,
        requested_speed=requested,trimmed=bool(excess),trimmed_samples=excess,
        final_seconds=len(fitted)/RATE,overlaps=0)
    return fitted,record
