import json
import logging
import tempfile
import threading
from pathlib import Path
import numpy as np
from .paths import workspace, executable, data_dir
from .audio import run, encode, check_cancel
from .backend import Backend, PREVIEW, JA_VOICES
from .render import render, Settings
from .timeline import parse, slots_for, validate

def diagnose(backend, cancel, progress):
    results = []
    with tempfile.TemporaryDirectory(prefix='job-', dir=workspace()) as folder:
        folder = Path(folder)
        for name, operation in [
            ('Temporary directory', lambda: (folder/'write-check').write_text('OK')),
            ('FFmpeg', lambda: run([executable('ffmpeg'), '-version'], cancel)),
            ('FFprobe', lambda: run([executable('ffprobe'), '-version'], cancel)),
            ('Timeline engine', lambda: validate(slots_for(parse('1\n00:00:05,000 --> 00:00:06,000\nHello.')), [100], 100)),
        ]:
            try:
                check_cancel(cancel)
                operation()
                results.append(f'{name}: OK')
            except Exception as exc:
                check_cancel(cancel)
                results.append(f'{name}: FAILED — {exc}')
        for language, voice in [('English US', 'af_heart'), ('Japanese', 'jf_alpha')]:
            try:
                audio, rate = backend.synthesize(PREVIEW[language], language, voice, cancel, progress)
                assert len(audio) > rate * 0.1 and np.isfinite(audio).all() and np.max(np.abs(audio)) > 0.001
                results.append(f'{language} TTS: OK (audio generated)')
            except Exception as exc:
                check_cancel(cancel)
                results.append(f'{language} TTS: FAILED — {exc}')
        try:
            raw = folder/'encoder.raw'
            np.zeros(48000, dtype='<f4').tofile(raw)
            encode(raw, folder/'encoder.mp3', cancel)
            assert (folder/'encoder.mp3').stat().st_size > 1000
            results.append('MP3 encoder / output directory: OK')
        except Exception as exc:
            check_cancel(cancel)
            results.append(f'MP3 encoder: FAILED — {exc}')
    return results

def self_test():
    # Frozen executable acceptance gate: no Python executable / PATH lookup.
    cancel = threading.Event()
    backend = Backend()
    result = {'diagnostics': diagnose(backend, cancel, logging.info)}
    try:
        if any('FAILED' in line for line in result['diagnostics']):
            raise RuntimeError('Diagnostics failed')
        with tempfile.TemporaryDirectory(prefix='job-', dir=workspace()) as folder:
            folder = Path(folder)/'LỒNG TIẾNG'/'Test App'
            folder.mkdir(parents=True)
            from .audio import run
            for language, voice, text in [('English US','am_puck','Hello, this is a test.'),
                                          ('Japanese','jm_kumo','これは音声のテストです。')]:
                file = folder/('日本語.srt' if language == 'Japanese' else 'English.srt')
                file.write_text(f'1\n00:00:05,000 --> 00:00:09,420\n{text}\n', encoding='utf-8-sig')
                output = file.with_suffix('.mp3')
                report = render(file, output, Settings(language=language,voice=voice),backend,cancel)
                decoded = folder/'decoded.raw'
                run([executable('ffmpeg'),'-nostdin','-v','error','-y','-i',str(output),
                     '-f','f32le','-ar','48000','-ac','1',str(decoded)],cancel)
                audio = np.fromfile(decoded,dtype='<f4')
                # MP3 encoders can pre-ring within a few ms of an onset.
                assert np.max(np.abs(audio[:int(4.97*48000)])) < 0.001
                assert abs(len(audio)/48000-9.42) < 0.05
                assert report['overlaps'] == 0
                result[language] = {'render': 'OK','duration':len(audio)/48000,'overlaps':0}
            for voice in JA_VOICES:
                a, rate = backend.synthesize(PREVIEW['Japanese'],'Japanese',voice,cancel)
                assert len(a)>rate/10
            result['all_japanese_voices'] = 'OK'
        result['passed'] = True
        code = 0
    except Exception as exc:
        logging.exception('Self test failed')
        result.update(passed=False, error=str(exc))
        code = 1
    (data_dir()/'self-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
