"""Installed-app 74-caption real Kokoro acceptance in both languages."""
import json
import logging
import tempfile
import threading
from pathlib import Path
import numpy as np
from .backend import Backend, JA_VOICES
from .render import Settings, render
from .paths import workspace, executable, data_dir
from .audio import run
from . import __version__

def timestamp(ms):
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def stress_test():
    cancel=threading.Event();backend=Backend();result={'version':__version__,'languages':{}}
    try:
        for language,voice in [('English US','am_michael'),('Japanese','jm_kumo')]:
            with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as temp:
                folder=Path(temp);source=folder/'日本語 テスト.srt';out=folder/'日本語 テスト_Voice.mp3'
                en=['What is THAT?!','No way this actually worked.','Everything finally went quiet.',
                    'And then everything went wrong.','That was hilarious!','We finally finished it.']
                ja=['これは本当に大丈夫なのか？','ついに完成しました。','何をしてるんだよ！',
                    '静かな夜です。','突然、全てを失いました。','本当に面白いですね！']
                phrases=ja if language=='Japanese' else en
                blocks=[f'{i+1}\n{timestamp(5000+i*3000)} --> {timestamp(5000+(i+1)*3000)}\n{phrases[i%len(phrases)]}' for i in range(74)]
                source.write_text('\n\n'.join(blocks),encoding='utf-8-sig')
                settings=Settings(language=language,voice=voice,emotion_mode='Auto',effect='Cave',strength='Strong')
                r=render(source,out,settings,backend,cancel,lambda d,t,m:logging.info(m))
                assert r['valid']==74 and r['overlaps']==0 and r['duration_ms']==227000
                assert len(list(folder.glob('*.mp3')))==1
                for i,record in enumerate(r['records']):
                    assert record['start_sample']==(5000+i*3000)*48
                    assert record['end_sample']<=record['allowed_end'] and record['speed']<=1.2
                decoded=folder/'decoded.raw'
                run([executable('ffmpeg'),'-nostdin','-v','error','-y','-i',str(out),'-f','f32le',str(decoded)],cancel)
                audio=np.fromfile(decoded,dtype='<f4')
                assert abs(len(audio)/48000-227)<.05
                assert np.max(np.abs(audio[:round(4.97*48000)]))<.001
                r.pop('output')
                result['languages'][language]=r
            assert not list(workspace().glob('job-*'))
        result['passed']=True;code=0
    except Exception as exc:
        logging.exception('74-caption acceptance failed')
        result.update(passed=False,error=str(exc));code=1
    (data_dir()/'stress-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
