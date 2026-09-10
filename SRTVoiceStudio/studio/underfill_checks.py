"""Real Kokoro benchmark against the exact audited 1.0 renderer, same cached TTS.
The archived reference is used ONLY here, never by GUI/Preview C/production.
"""
import hashlib
import json
import logging
import tempfile
import threading
from pathlib import Path
import numpy as np
from .backend import Backend
from .render import Settings, render
from . import acceptance_baseline_1_0 as baseline
from .paths import workspace, root, data_dir, executable
from .timeline import read_srt, RATE
from .audio import run
from . import __version__

class SharedBase:
    def __init__(self,backend):
        self.backend=backend;self.cache={};self.count=0
    def synthesize(self,text,language,voice,cancel,progress=lambda _:None):
        key=(text,language,voice)
        if key not in self.cache:
            samples,rate=self.backend.synthesize(text,language,voice,cancel,progress)
            a=np.asarray(samples,dtype=np.float32).copy();a.setflags(write=False)
            self.cache[key]=(a,rate);self.count+=1
        a,rate=self.cache[key]
        return a.copy(),rate

def run_comparison(backend,cancel,source,folder,voice='am_michael'):
    captions=read_srt(source)
    assert len(captions)==30
    assert all(3800<=c.end-c.start<=4200 and 7<=len(c.text.split())<=9 for c in captions)
    assert all(b.start-a.end==100 for a,b in zip(captions,captions[1:]))
    shared=SharedBase(backend)
    old_dir,new_dir=folder/'reference_1_0',folder/'underfill_1_1'
    old_dir.mkdir();new_dir.mkdir()
    old=baseline.render(source,old_dir/'reference.mp3',baseline.Settings(voice=voice),shared,cancel)
    new=render(source,new_dir/'final.mp3',Settings(voice=voice),shared,cancel)
    assert shared.count==30,'Comparison must reuse the exact same original audio'
    old_silences=[(r['allowed_end']-r['end_sample'])/RATE for r in old['records']]
    old_mean=float(np.mean(old_silences));new_mean=new['average_trailing_silence']
    assert new['overlaps']==0 and new['valid']==30
    assert new['slow_down_captions']>0
    # Compare against achievable extension at the hard floor, not an impossible
    # universal silence target for very short scripts.
    potential=float(np.mean([max(0,min((c.end-c.start)/1000-.2,r['tts_seconds']/.88)
                                       -(r['end_sample']-r['start_sample'])/RATE)
                             for c,r in zip(captions,old['records'])]))
    assert new_mean<old_mean-.10 and old_mean-new_mean>=potential*.8,(old_mean,new_mean,potential)
    for c,a,b in zip(captions,old['records'],new['records']):
        assert a['start_sample']==b['start_sample']==c.start*48
        assert b['end_sample']<=b['allowed_end'] and .88<=b['speed']<=1.2
        # A residual gap is allowed only within declared speed limits; never shift START.
        if b['underfilled'] and b['underfill_adjusted']:
            assert b['speed']<=.880001
    assert len(list(new_dir.iterdir()))==1 and len(list(old_dir.iterdir()))==1
    probe=run([executable('ffprobe'),'-v','error','-show_entries','stream=sample_rate,bit_rate,channels',
               '-of','json',str(new_dir/'final.mp3')],cancel)
    stream=json.loads(probe)['streams'][0]
    assert stream['sample_rate']=='48000' and stream['bit_rate']=='192000' and stream['channels']==1
    return {'version':__version__,'passed':True,'reference':'Exact render.py from audited 1.0 build commit 78fc14f',
        'sample':Path(source).name,
        'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        'captions':30,'words_per_caption':sum(len(c.text.split()) for c in captions)/30,
        'slot_min_seconds':min(c.end-c.start for c in captions)/1000,'slot_max_seconds':max(c.end-c.start for c in captions)/1000,'inter_caption_gap':.1,'voice':voice,'base_synthesis_calls':shared.count,
        'baseline_average_trailing_silence':old_mean,'baseline_maximum_trailing_silence':max(old_silences),
        'average_trailing_silence':new_mean,'maximum_trailing_silence':new['maximum_trailing_silence'],
        'reduction_percent':100*(old_mean-new_mean)/old_mean,'achievable_reduction_at_floor':potential,
        'underfilled_captions':new['underfilled_captions'],
        'underfilled_after_hard_minimum':new['underfilled_after_hard_minimum'],
        'slow_down_captions':new['slow_down_captions'],'speed_up_captions':new['speed_up_captions'],
        'trimmed_captions':new['safely_trimmed'],'overlaps':0,'records':new['records'],
        'naturalness':'Pitch-preserving atempo; effective speed >=0.88. Human listening not certified.'}

def underfill_test():
    try:
        with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as folder:
            result=run_comparison(Backend(),threading.Event(),root()/'samples'/'EN7_US_Comedy_Reviewer_V2.srt',Path(folder))
        assert not list(workspace().glob('job-*'))
        code=0
    except Exception as exc:
        logging.exception('Underfill regression failed')
        result={'version':__version__,'passed':False,'error':str(exc)};code=1
    (data_dir()/'underfill-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
