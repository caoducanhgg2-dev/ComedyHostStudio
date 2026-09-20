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
from .continuity import trim_edge_silence
from .voice_backends import synthesize_selected
from .sfx import mix_auto_sfx, DENSITIES, STRENGTHS
from .render_cache import TtsCache
from .quality import measure_master, analyze_render

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
    continuous: bool = False
    continuous_target_ms: int = 100
    auto_sfx: bool = False
    sfx_density: str = 'Balanced'
    sfx_strength: str = 'Medium'
    smart_fit3: bool = False
    use_render_cache: bool = True
    sfx_overrides: tuple = ()


def render(srt, output, settings, backend, cancel, progress=lambda *_: None):
    if not 1.0 <= settings.speed <= 1.2:
        raise ValueError('Speed phải nằm trong 1.00–1.20x.')
    if settings.overflow not in ('Safe Trim', 'Stop and Report'):
        raise ValueError('Overflow mode không hợp lệ.')
    if settings.continuous and not 50 <= int(settings.continuous_target_ms) <= 250:
        raise ValueError('Continuous target phải nằm trong 50–250 ms.')
    if settings.sfx_density not in DENSITIES or settings.sfx_strength not in STRENGTHS:
        raise ValueError('Cấu hình Auto SFX không hợp lệ.')
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
    sfx_report = dict(enabled=False, planned=0, mixed=0, rejected=0, events=[], max_mix_peak=0.0)
    logging.info('Render settings: %s', asdict(settings))
    cache = None
    if bool(getattr(settings, 'use_render_cache', True)):
        try:
            cache = TtsCache()
        except OSError:
            logging.exception('Cannot initialize TTS render cache; continuing without cache')
    cache_hits = cache_misses = 0
    previous_speed = None
    master_metrics = {}
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
                cached = cache.get(settings, c.text) if cache is not None else None
                if cached is not None:
                    samples, rate = cached
                    cache_hits += 1
                    progress(i, len(slots), f'Cache TTS HIT • Caption {c.index}')
                else:
                    samples, rate = synthesize_selected(backend,c.text,settings,cancel,
                        lambda msg: progress(i, len(slots), msg))
                    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
                    if not len(samples) or not np.isfinite(samples).all() or not np.any(np.abs(samples) > 1e-7):
                        raise RuntimeError(f'CAPTION {c.index}: TTS trả về audio rỗng hoặc không hợp lệ.')
                    cache_misses += 1
                    if cache is not None:
                        try:
                            cache.put(settings, c.text, samples, rate)
                        except OSError:
                            logging.exception('Cannot write TTS cache for caption %s', c.index)
                base_duration = len(samples)/rate
                samples, trim_start, trim_end = trim_edge_silence(samples, rate, settings.continuous)
                if not len(samples) or not np.isfinite(samples).all() or not np.any(np.abs(samples) > 1e-7):
                    raise RuntimeError(f'CAPTION {c.index}: Continuous Voice tạo audio không hợp lệ.')
                processed, emotion_tempo, emotion, intensity = processor.process(samples, rate, settings, c.text)
                fitted, record = fit_processed(
                    processed, rate, slot, settings, emotion_tempo, temp, cancel,
                    previous_speed=previous_speed)
                previous_speed = record.get('speed', previous_speed)
                record.update(tts_seconds=base_duration, emotion=emotion, intensity=intensity,
                              effect=settings.effect, strength=settings.strength,
                              continuity_trimmed_start=trim_start,
                              continuity_trimmed_end=trim_end,
                              continuity_trimmed_seconds=trim_start+trim_end)
                master[slot.start:slot.start+len(fitted)] = fitted
                lengths.append(len(fitted))
                shown_silence = record.get('transition_silence', record['trailing_silence']) if settings.continuous else record['trailing_silence']
                progress(i+1, len(slots), f"Caption {c.index} • {emotion} • {settings.effect} / {settings.strength} • "
                    f"Processed {record['processed_seconds']:.2f}s / Slot {record['available_seconds']:.2f}s • "
                    f"Fit {record['speed']:.3f}x • Audible gap {shown_silence:.2f}s • Overlap 0")
                records.append(record)
                logging.info('Caption result: %s', record)
            summary = validate(slots, lengths, settings.gap_ms)
            check_cancel(cancel)
            if settings.auto_sfx:
                progress(len(slots), len(slots), 'TIMELINE VALID • Auto SFX: đang phân tích và kiểm tra artifact')
            sfx_report = mix_auto_sfx(master, captions, settings, RATE)
            master_metrics = measure_master(master)
            master.flush()
        finally:
            del master
        check_cancel(cancel)
        fit_status = {}
        for record in records:
            key = record.get('fit_status', 'GOOD')
            fit_status[key] = fit_status.get(key, 0) + 1
        measured_silence = [
            (r.get('transition_silence', r['trailing_silence']) if settings.continuous else r['trailing_silence'])
            for r in records
        ]
        summary.update(emotion_mode=settings.emotion_mode, emotion=settings.emotion,
                       effect=settings.effect, strength=settings.strength,
                       continuous_mode=bool(settings.continuous),
                       continuous_target_ms=int(settings.continuous_target_ms),
                       continuity_trimmed_seconds=sum(
                           r.get('continuity_trimmed_seconds',0.0) + r.get('post_dsp_trimmed_seconds',0.0)
                           for r in records),
                       timeline_fit_status=fit_status,
                       speed_adjusted=sum(r['speed_up'] or r['slow_down'] for r in records),
                       speed_up_captions=sum(r['speed_up'] for r in records),
                       slow_down_captions=sum(r['slow_down'] for r in records),
                       underfilled_captions=sum(r['underfilled'] for r in records),
                       underfilled_after_hard_minimum=sum(r['underfilled_at_hard_minimum'] for r in records),
                       average_trailing_silence=sum(measured_silence)/len(records),
                       median_trailing_silence=float(np.median(measured_silence)),
                       transitions_over_08=sum(
                           (slots[i+1].start-r.get('audible_end_sample',r['end_sample']))/RATE > .8
                           for i,r in enumerate(records[:-1])),
                       maximum_trailing_silence=max(measured_silence),
                       safely_trimmed=sum(r['trimmed'] for r in records),
                       auto_sfx=bool(settings.auto_sfx),
                       sfx_density=settings.sfx_density,
                       sfx_strength=settings.sfx_strength,
                       sfx_planned=int(sfx_report.get('planned',0)),
                       sfx_mixed=int(sfx_report.get('mixed',0)),
                       sfx_rejected=int(sfx_report.get('rejected',0)),
                       sfx_max_mix_peak=float(sfx_report.get('max_mix_peak',0.0)),
                       sfx_events=sfx_report.get('events',[]),
                       smart_fit3=bool(getattr(settings, 'smart_fit3', False)),
                       smart_fit3_neighbor_adjusted=sum(bool(r.get('smart_fit3_neighbor_limited')) for r in records),
                       render_cache=bool(cache is not None),
                       cache_hits=int(cache_hits), cache_misses=int(cache_misses),
                       master_metrics=master_metrics,
                       duration=display_time(end_ms), duration_ms=end_ms, records=records)
        summary['quality'] = analyze_render(summary)
        summary['quality_status'] = summary['quality']['status']
        summary['quality_issues'] = summary['quality']['issues']
        progress(len(slots), len(slots),
                 f"TIMELINE VALID • QC {summary['quality_status']} • SFX {summary['sfx_mixed']}/{summary['sfx_planned']} • Đang mã hóa MP3")
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
        logging.info('TIMELINE VALID: %s', {k:v for k,v in summary.items() if k not in ('records','sfx_events')})
        return summary
