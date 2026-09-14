"""Installed 1.4 acceptance entrypoints. Real backends, no synthetic TTS."""
import json
import logging
from pathlib import Path
import tempfile
import threading
from . import __version__
from .paths import workspace,data_dir,root
from .render import render,Settings
from .backend import Backend
from .batch import BatchQueue,DONE,FAILED
from .aivis_pack import AivisPack
from .stress import timestamp


def batch_test(folder,cancel):
    backend=Backend();results=[]
    cases=(
        ('English US','am_michael','Today we begin a surprising new story.','English US'),
        ('English UK','bf_emma','Today we begin a rather surprising new story.','British English'),
        ('Japanese','jf_alpha','今日は新しい物語を紹介します。','Tiếng Nhật 日本語'))
    for count in (1,5,20):
        case=folder/str(count);case.mkdir();queue=BatchQueue();languages=[]
        for i in range(count):
            language,voice,text,label=cases[i%len(cases)]
            source=case/f'{i:02d}_{label}.srt';source.write_text('1\n00:00:05,000 --> 00:00:09,000\n'+text+'\n',encoding='utf-8')
            queue.add([source],Settings(language=language,voice=voice));languages.append(language)
        counts=queue.run(backend,case/'output')
        assert counts[DONE]==count and len(list((case/'output').glob('*.mp3')))==count
        assert all(i.report['overlaps']==0 and i.report['records'][0]['start_sample']==240000 for i in queue.items)
        results.append(dict(files=count,completed=count,overlaps=0,start_times_unchanged=True,languages=sorted(set(languages))))
    bad=folder/'invalid.srt';bad.write_text('invalid')
    good=folder/'valid.srt';good.write_text('1\n00:00:00,000 --> 00:00:04,000\nThis is the final short test.\n')
    queue=BatchQueue();queue.add([bad,good],Settings());counts=queue.run(backend,folder/'retry-output')
    assert counts[FAILED]==1 and counts[DONE]==1
    bad.write_text(good.read_text());queue.retry();assert queue.run(backend,folder/'retry-output')[DONE]==2
    return dict(cases=results,failed_file_continues=True,retry_passed=True,british_batch=True)


def optional_test(folder,cancel):
    pack=AivisPack();backend=pack.backend()
    if backend is None:raise RuntimeError('Chưa cài gói Aivis để kiểm thử offline.')
    try:
        voices=backend.list_voices();durations={}
        assert len(voices)==6,'Bản 1.4 phải có Mao, Kohaku và 4 giọng Nhật mở rộng.'
        for voice in voices:
            samples,rate=backend.synthesize('これはオフライン音声の確認です。','Japanese',voice.id,cancel)
            assert len(samples)>0 and rate==48000;durations[voice.id]=len(samples)/rate
        source=folder/'日本語 74 câu.srt';phrases=['今日は新しい物語を紹介します。','これは本当に大丈夫でしょうか？','静かな街で冒険が始まりました。']
        source.write_text('\n\n'.join(f'{i+1}\n{timestamp(5000+i*4100)} --> {timestamp(9000+i*4100)}\n{phrases[i%3]}' for i in range(74)),encoding='utf-8')
        settings=Settings(language='Japanese',voice=voices[0].id,emotion='Happy',effect='Cave',strength='Mild')
        report=render(source,folder/'final.mp3',settings,backend,cancel)
        assert report['valid']==74 and report['overlaps']==0
        assert all(r['start_sample']==(5000+i*4100)*48 and r['end_sample']<=r['allowed_end'] for i,r in enumerate(report['records']))
        assert len(list(folder.glob('*.mp3')))==1
        voice=voices[0];samples,rate=backend.synthesize_style('今日は楽しい一日です。','Japanese',voice.id,voice.styles[1]['id'],cancel)
        assert len(samples)>0 and rate==48000
        # Prove one dynamically mapped expansion style as well (Rinne Happy).
        rinne=next(v for v in voices if v.name.startswith('Rinne El'))
        happy=next(s['id'] for s in rinne.styles if s['name']=='Vui vẻ')
        samples,rate=backend.synthesize_style('今日はとても楽しいです。','Japanese',rinne.id,happy,cancel)
        assert len(samples)>0 and rate==48000
        from .preview import PreviewCache
        from .timeline import read_srt,slots_for
        from .fitting import fit_processed
        from dataclasses import replace
        import numpy as np
        cache=PreviewCache();slot=slots_for(read_srt(source))[0];selected=replace(settings,native_style=voice.styles[1]['id'])
        count=[0];original=backend.synthesize_style
        def counted(*args,**kwargs):count[0]+=1;return original(*args,**kwargs)
        backend.synthesize_style=counted
        cache.get('A',slot.caption.text,selected,backend,cancel,slot)
        b=cache.get('B',slot.caption.text,selected,backend,cancel,slot);c=cache.get('C',slot.caption.text,selected,backend,cancel,slot)
        expected,_=fit_processed(b.samples,b.rate,slot,selected,cache.emotion_tempo,folder,cancel)
        assert count[0]==1 and np.array_equal(c.samples,expected)
        return dict(voices=durations,expansion_voices=4,stress_captions=74,overlaps=0,start_times_unchanged=True,native_style=True,dynamic_style=True,abc_shared_fit=True)
    finally:pack.close()


def run_test(name):
    cancel=threading.Event()
    try:
        with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as temp:
            folder=Path(temp)
            if name=='batch':result=batch_test(folder,cancel)
            elif name=='underfill-v2':
                from .underfill_v2_checks import run_comparison
                result=run_comparison(Backend(),cancel,root()/'samples/EN7_American_Comedy_Review.srt',folder)
                import shutil
                evidence=data_dir()/'UnderfillV2';evidence.mkdir(exist_ok=True)
                destination=evidence/'EN7_American_Comedy_Review_Voice.mp3';shutil.copyfile(result['output'],destination);result['output']=str(destination)
            elif name=='install-voice':
                p=AivisPack();p.install(cancel);result=dict(installed=p.available(),complete=p.complete(),japanese_aivis_voices=6)
            elif name=='optional-voices':result=optional_test(folder,cancel)
            elif name=='voice-benchmark':
                from .voice_benchmarks import generate
                result=generate(data_dir()/'VoiceBenchmarks',cancel)
            else:raise ValueError(name)
        result.update(version=__version__,passed=True);code=0
    except Exception as exc:
        logging.exception('Upgrade acceptance failed');result=dict(version=__version__,passed=False,error=str(exc));code=1
    (data_dir()/(name+'-test.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
