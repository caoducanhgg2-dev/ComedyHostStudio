"""Controlled 1.1/working-V2 comparison on identical cached original speech.

The supplied historical MP3 has unknown synthesis settings. Its measured silence
belongs in a separate observational comparison, not this causal A/B benchmark.
"""
import hashlib
from pathlib import Path
import numpy as np
from . import acceptance_fitting_1_1 as reference
from .effects import EffectProcessor
from .render import render, Settings
from .timeline import read_srt,slots_for,RATE
from .underfill_checks import SharedBase


def silence_metrics(records,slots):
    trailing=[(s.end-r['end_sample'])/RATE for s,r in zip(slots,records)]
    transitions=[(slots[i+1].start-r['end_sample'])/RATE for i,r in enumerate(records[:-1])]
    return dict(average_trailing_silence=float(np.mean(trailing)),
                median_trailing_silence=float(np.median(trailing)),
                maximum_trailing_silence=max(trailing),
                transitions_over_08=sum(x>.8 for x in transitions))


def run_comparison(backend,cancel,source,folder,settings=None):
    settings=settings or Settings(voice='am_michael')
    captions=read_srt(source);slots=slots_for(captions,settings.gap_ms)
    assert len(captions)==46
    assert all(4000<=c.end-c.start<=4200 for c in captions)
    assert all(b.start-a.end==100 for a,b in zip(captions,captions[1:]))
    shared=SharedBase(backend);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    baseline=[];processor=EffectProcessor(folder,cancel)
    for slot in slots:
        a,rate=shared.synthesize(slot.caption.text,settings.language,settings.voice,cancel)
        b,tempo,_,_=processor.process(a,rate,settings,slot.caption.text)
        _,record=reference.fit_processed(b,rate,slot,settings,tempo,folder,cancel)
        baseline.append(record)
    final=render(source,folder/(Path(source).stem+'_Voice.mp3'),settings,shared,cancel)
    for slot,old,new in zip(slots,baseline,final['records']):
        assert old['start_sample']==new['start_sample']==slot.caption.start*48
        assert new['end_sample']<=slot.end and .88<=new['speed']<=1.20
        if new['classification']=='UNDERFILL' and settings.adaptive:
            assert new['fit_tempo']<=1.000001
    assert final['overlaps']==0 and len(list(folder.glob('*.mp3')))==1
    old=silence_metrics(baseline,slots);new=silence_metrics(final['records'],slots)
    return dict(source=Path(source).name,source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        reference='Exact fitting.py from verified 1.1.0 source commit 33fea46',
        same_cached_tts=True,unique_synthesis_calls=shared.count,captions=len(captions),voice=settings.voice,
        start_times_unchanged=True,overlaps=0,baseline=old,final=new,
        average_reduction_seconds=old['average_trailing_silence']-new['average_trailing_silence'],
        large_transition_reduction=old['transitions_over_08']-new['transitions_over_08'],
        target_reached=new['average_trailing_silence']<=.35,
        listening_status='Not certified; real listening is required for naturalness.',
        records=final['records'],output=final['output'])
