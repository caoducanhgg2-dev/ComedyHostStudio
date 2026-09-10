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
from . import __version__

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
            from .style_checks import style_checks
            results.extend(style_checks(backend,cancel,progress))
        except Exception as exc:
            check_cancel(cancel)
            results.append(f'Emotion / FX / Preview: FAILED — {exc}')
        try:
            from misaki.cutlet import Cutlet
            phonemes,_ = Cutlet()('これは日本語です。')
            assert phonemes.strip()
            results.append('Japanese G2P: OK')
            backend.load(cancel,progress)
            results.append('Kokoro backend: OK')
            from .timeline import TimelineError
            bad=slots_for(parse('1\n00:00:00,000 --> 00:00:01,000\nA'))
            try:
                validate(bad,[48001],100)
            except TimelineError:
                results.append('Overlap Validator: OK (invalid boundary rejected)')
            else:
                raise AssertionError('Boundary violation accepted')
        except Exception as exc:
            check_cancel(cancel)
            results.append(f'Backend / G2P / Validator: FAILED — {exc}')
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
    result = {'version': __version__, 'diagnostics': diagnose(backend, cancel, logging.info)}
    try:
        if any('FAILED' in line for line in result['diagnostics']):
            raise RuntimeError('Diagnostics failed')
        with tempfile.TemporaryDirectory(prefix='job-', dir=workspace()) as folder:
            folder = Path(folder)/'LỒNG TIẾNG'/'Test App'
            folder.mkdir(parents=True)
            from .audio import run
            for language, voice, text in [('English US','am_puck','Hello, this is a test.'),
                                          ('Japanese','jm_kumo','これは音声のテストです。')]:
                file = folder/('日本語 テスト.srt' if language == 'Japanese' else 'English.srt')
                file.write_text(f'1\n00:00:05,000 --> 00:00:09,420\n{text}\n', encoding='utf-8-sig')
                output = file.with_name(file.stem+'_Voice.mp3')
                report = render(file, output, Settings(language=language,voice=voice,emotion='Dramatic',effect='Cave'),backend,cancel)
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
                from .preview import PreviewCache
                from dataclasses import replace
                cache=PreviewCache()
                text=PREVIEW['Japanese']
                slot=slots_for(parse(f'1\n00:00:00,000 --> 00:00:03,000\n{text}'))[0]
                settings=Settings(language='Japanese',voice=voice,emotion='Funny / Playful',effect='Radio')
                for stage in ('A','B','C'):
                    preview=cache.get(stage,text,settings,backend,cancel,slot)
                    assert len(preview.samples)>0
                assert preview.details['overlaps']==0
            result['all_japanese_voices'] = 'OK (5 voices, real TTS + A/B/C)'
            from .paths import root
            installed_srt = root().parent/'日本語 テスト.srt'
            # Windows acceptance optionally supplies a writable D: Unicode test location.
            import os
            if os.environ.get('SRTVS_UNICODE_TEST_DIR'):
                target=Path(os.environ['SRTVS_UNICODE_TEST_DIR'])
                target.mkdir(parents=True,exist_ok=True)
                source=target/'日本語 テスト.srt'
                source.write_text('1\n00:00:05,000 --> 00:00:09,420\nこれは音声のテストです。',encoding='utf-8-sig')
                out=target/'日本語 テスト_Voice.mp3'
                r=render(source,out,Settings(language='Japanese',voice='jf_alpha',effect='Echo',strength='Strong'),backend,cancel)
                assert r['overlaps']==0 and out.is_file()
                result['unicode_input_output']={'path':str(out),'overlaps':0}
                out.unlink();source.unlink()
        result['passed'] = True
        code = 0
    except Exception as exc:
        logging.exception('Self test failed')
        result.update(passed=False, error=str(exc))
        code = 1
    (data_dir()/'self-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
