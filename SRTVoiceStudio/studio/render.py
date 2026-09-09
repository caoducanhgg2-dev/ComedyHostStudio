from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import os
import tempfile
import numpy as np
from .timeline import read_srt, slots_for, validate, RATE, display_time, TimelineError
from .paths import workspace
from .audio import convert, normalize, encode, check_cancel

@dataclass(frozen=True)
class Settings:
    language: str = 'English US'
    voice: str = 'af_heart'
    speed: float = 1.0
    gap_ms: int = 100
    adaptive: bool = True
    loudness: bool = True
    overflow: str = 'Safe Trim'

def render(srt, output, settings, backend, cancel, progress=lambda *_: None):
    if not 1.0 <= settings.speed <= 1.2:
        raise ValueError('Speed phải nằm trong 1.00–1.20x.')
    if settings.overflow not in ('Safe Trim', 'Stop and Report'):
        raise ValueError('Overflow mode không hợp lệ.')
    captions = read_srt(srt)
    slots = slots_for(captions, settings.gap_ms)
    end_ms = max(c.end for c in captions)
    output = Path(output).resolve()
    if output.suffix.lower() != '.mp3':
        raise ValueError('Đầu ra phải là .mp3.')
    if output == Path(srt).resolve():
        raise ValueError('Không ghi đè SRT gốc.')
    output.parent.mkdir(parents=True, exist_ok=True)
    lengths, records = [], []
    logging.info('Render settings: %s', asdict(settings))
    # Master is disk-backed; even long input cannot allocate hours of PCM in RAM.
    with tempfile.TemporaryDirectory(prefix='job-', dir=workspace()) as temp:
        temp = Path(temp)
        master_path = temp / 'master.raw'
        total_samples = end_ms * 48
        with master_path.open('wb') as f:
            f.truncate(total_samples * 4)
        master = np.memmap(master_path, mode='r+', dtype='<f4', shape=(total_samples,))
        try:
            for i, slot in enumerate(slots):
                check_cancel(cancel)
                c = slot.caption
                progress(i, len(slots), f'Creating voice {i+1} / {len(slots)} • Caption {c.index}')
                samples, rate = backend.synthesize(c.text, settings.language, settings.voice, cancel,
                    lambda msg: progress(i, len(slots), msg))
                samples = np.asarray(samples, dtype=np.float32).reshape(-1)
                if not len(samples) or not np.isfinite(samples).all() or not np.any(np.abs(samples) > 1e-7):
                    raise RuntimeError(f'CAPTION {c.index}: TTS trả về audio rỗng hoặc không hợp lệ.')
                available = slot.end - slot.start
                duration = len(samples) / rate
                needed = duration / (available / RATE)
                # Prefer <=1.15; use up to 1.20 only when the slot needs it.
                speed = max(settings.speed, min(needed, 1.15)) if settings.adaptive else settings.speed
                if settings.adaptive and needed > 1.15:
                    speed = max(speed, min(needed, 1.20))
                fitted = convert(samples, rate, speed, temp, cancel)
                excess = max(0, len(fitted) - available)
                if excess and settings.overflow == 'Stop and Report':
                    raise TimelineError(f'CAPTION {c.index} TOO LONG\nSlot: {available/RATE:.3f} s\n'
                        f'TTS: {duration:.3f} s\nSpeed: {speed:.3f}x\n'
                        f'Adjusted: {len(fitted)/RATE:.3f} s\nKhông export.')
                fitted = fitted[:available].copy()
                # Fade only inside the slot; no crossfade across subtitle boundaries.
                if excess:
                    fade = min(len(fitted), 240)
                    fitted[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
                if settings.loudness:
                    fitted = normalize(fitted)
                fitted = np.clip(fitted, -0.89, 0.89)
                master[slot.start:slot.start+len(fitted)] = fitted
                lengths.append(len(fitted))
                record = dict(caption=c.index, start_sample=slot.start, end_sample=slot.start+len(fitted),
                              allowed_end=slot.end, tts_seconds=duration, speed=speed, trimmed=bool(excess))
                records.append(record)
                logging.info('Caption result: %s', record)
            summary = validate(slots, lengths, settings.gap_ms)
            master.flush()
        finally:
            del master
        check_cancel(cancel)
        summary.update(speed_adjusted=sum(r['speed'] > settings.speed+1e-6 for r in records),
                       safely_trimmed=sum(r['trimmed'] for r in records),
                       duration=display_time(end_ms), duration_ms=end_ms, records=records)
        progress(len(slots), len(slots), 'TIMELINE VALID • Đang mã hóa MP3')
        # Stage in the destination filesystem so publishing is atomic on any drive.
        # Register this path for recovery after a process crash.
        fd, staged = tempfile.mkstemp(prefix='.srtvs-', suffix='.mp3', dir=output.parent)
        os.close(fd)
        (temp/'staged-output.txt').write_text(staged, encoding='utf-8')
        try:
            encode(master_path, staged, cancel)
            check_cancel(cancel)
            os.replace(staged, output)
        finally:
            Path(staged).unlink(missing_ok=True)
        summary['output'] = str(output)
        logging.info('TIMELINE VALID: %s', {k:v for k,v in summary.items() if k != 'records'})
        return summary
