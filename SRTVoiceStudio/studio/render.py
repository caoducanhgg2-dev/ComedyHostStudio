from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import os
import tempfile
import numpy as np
from .timeline import read_srt, slots_for, validate, RATE, display_time, TimelineError
from .paths import workspace
from .audio import encode, check_cancel
from .effects import EffectProcessor
from .fitting import fit_processed
from .voice_backends import synthesize_selected

@dataclass(frozen=True)
class Settings:
    language: str = 'English US'
    voice: str = 'af_heart'
    speed: float = 1.0
    gap_ms: int = 100
    adaptive: bool = True
    loudness: bool = True
    overflow: str = 'Safe Trim'
    emotion_mode: str = 'Manual'
    emotion: str = 'Natural'
    intensity: str = 'Medium'
    effect: str = 'None'
    strength: str = 'Medium'
    native_style: int | None = None

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
        processor = EffectProcessor(temp, cancel)
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
                samples, rate = synthesize_selected(backend,c.text,settings,cancel,
                    lambda msg: progress(i, len(slots), msg))
                samples = np.asarray(samples, dtype=np.float32).reshape(-1)
                if not len(samples) or not np.isfinite(samples).all() or not np.any(np.abs(samples) > 1e-7):
                    raise RuntimeError(f'CAPTION {c.index}: TTS trả về audio rỗng hoặc không hợp lệ.')
                base_duration = len(samples)/rate
                processed, emotion_tempo, emotion, intensity = processor.process(samples, rate, settings, c.text)
                fitted, record = fit_processed(processed, rate, slot, settings, emotion_tempo, temp, cancel)
                record.update(tts_seconds=base_duration, emotion=emotion, intensity=intensity,
                              effect=settings.effect, strength=settings.strength)
                master[slot.start:slot.start+len(fitted)] = fitted
                lengths.append(len(fitted))
                progress(i+1, len(slots), f"Caption {c.index} • {emotion} • {settings.effect} / {settings.strength} • "
                    f"Processed {record['processed_seconds']:.2f}s / Slot {record['available_seconds']:.2f}s • "
                    f"Fit {record['speed']:.3f}x • Silence {record['trailing_silence']:.2f}s • Overlap 0")
                records.append(record)
                logging.info('Caption result: %s', record)
            summary = validate(slots, lengths, settings.gap_ms)
            master.flush()
        finally:
            del master
        check_cancel(cancel)
        summary.update(emotion_mode=settings.emotion_mode, emotion=settings.emotion,
                       effect=settings.effect, strength=settings.strength,
                       speed_adjusted=sum(r['speed_up'] or r['slow_down'] for r in records),
                       speed_up_captions=sum(r['speed_up'] for r in records),
                       slow_down_captions=sum(r['slow_down'] for r in records),
                       underfilled_captions=sum(r['underfilled'] for r in records),
                       underfilled_after_hard_minimum=sum(r['underfilled_at_hard_minimum'] for r in records),
                       average_trailing_silence=sum(r['trailing_silence'] for r in records)/len(records),
                       median_trailing_silence=float(np.median([r['trailing_silence'] for r in records])),
                       transitions_over_08=sum((slots[i+1].start-r['end_sample'])/RATE > .8 for i,r in enumerate(records[:-1])),
                       maximum_trailing_silence=max(r['trailing_silence'] for r in records),
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
