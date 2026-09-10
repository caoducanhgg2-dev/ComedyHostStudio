from pathlib import Path
from dataclasses import replace
import threading
import numpy as np
import pytest
from studio.fitting import fit_processed
from studio.preview import PreviewCache
from studio.render import Settings
from studio.timeline import Caption,slots_for,RATE
from studio.underfill_checks import run_comparison
from test_styles import CountingBackend

@pytest.fixture
def context(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'appdata'))
    return tmp_path,threading.Event()

def test_underfill_2_8_seconds_hard_floor_warning(context):
    folder,cancel=context;a,rate=CountingBackend(2.8).synthesize()
    slot=slots_for([Caption(1,0,4000,'test'),Caption(2,4100,8100,'next')])[0]
    b,r=fit_processed(a,rate,slot,Settings(),1,folder,cancel)
    assert r['speed']==.88 and 3.12<len(b)/RATE<3.23
    assert .77<r['trailing_silence']<.89 and r['underfilled']
    assert r['warning']=='SHORT SCRIPT / REMAINING SILENCE'
    assert r['end_sample']+4800<=round(4.1*RATE) and r['start_sample']==0 and r['overlaps']==0

@pytest.mark.parametrize('duration',[3.36,3.5,3.6])
def test_reachable_underfill_target(context,duration):
    folder,cancel=context;a,rate=CountingBackend(duration).synthesize()
    slot=slots_for([Caption(1,5000,9000,'test')])[0]
    b,r=fit_processed(a,rate,slot,Settings(),1,folder,cancel)
    assert .1<=r['trailing_silence']<=.3 and .88<=r['speed']<1
    assert not r['underfilled'] and r['slow_down'] and r['start_sample']==5*RATE

def test_adaptive_off_does_not_slow(context):
    folder,cancel=context;a,rate=CountingBackend(2.8).synthesize()
    slot=slots_for([Caption(1,0,4000,'test')])[0]
    _,r=fit_processed(a,rate,slot,Settings(adaptive=False),1,folder,cancel)
    assert r['speed']==1 and not r['slow_down'] and r['underfilled']

@pytest.mark.parametrize('requested',[1.0,1.15,1.2])
def test_v2_classifies_processed_audio_before_user_speed(context,requested):
    folder,cancel=context;a,rate=CountingBackend(3.6).synthesize()
    slot=slots_for([Caption(1,5100,9100,'test')])[0]
    _,r=fit_processed(a,rate,slot,Settings(speed=requested),1,folder,cancel)
    assert r['classification']=='UNDERFILL'
    assert .88<=r['speed']<=1 and r['fit_tempo']<=1
    assert .1<=r['trailing_silence']<=.3
    assert r['start_sample']==5100*48 and r['end_sample']<=9100*48

def test_v2_residual_below_warning_threshold_is_not_overlap(context):
    folder,cancel=context;a,rate=CountingBackend(3.0).synthesize()
    slot=slots_for([Caption(1,0,4000,'test')])[0]
    _,r=fit_processed(a,rate,slot,Settings(),1,folder,cancel)
    assert r['speed']==.88 and .4<r['trailing_silence']<.8
    assert not r['warning'] and r['overlaps']==0

@pytest.mark.parametrize('emotion',['Natural','Excited','Sad'])
def test_underfill_c_production_identical_combined_floor(context,emotion):
    folder,cancel=context;s=Settings(emotion=emotion,intensity='Strong',effect='Cave',strength='Strong')
    slot=slots_for([Caption(1,5000,15000,'sample')])[0];cache=PreviewCache();backend=CountingBackend(2.8)
    b=cache.get('B','sample',s,backend,cancel,slot);c=cache.get('C','sample',s,backend,cancel,slot)
    expected,record=fit_processed(b.samples,b.rate,slot,s,cache.emotion_tempo,folder,cancel)
    assert np.array_equal(c.samples,expected) and c.details['speed']==.88
    assert c.details['underfilled'] and c.details['underfilled_at_hard_minimum']
    assert backend.count==1

def test_slowdown_preserves_pitch(context):
    folder,cancel=context;t=np.arange(24000*3)/24000
    a=(.2*np.sin(2*np.pi*220*t)).astype('float32')
    slot=slots_for([Caption(1,0,4000,'test')])[0]
    b,r=fit_processed(a,24000,slot,Settings(),1,folder,cancel)
    sample=b[4800:-4800];spectrum=np.abs(np.fft.rfft(sample*np.hanning(len(sample))))
    freq=np.fft.rfftfreq(len(sample),1/RATE)[np.argmax(spectrum)]
    assert abs(freq-220)<2 and r['speed']==.88

def test_30_caption_reference_comparison(context):
    folder,cancel=context
    source=Path(__file__).parents[1]/'samples'/'underfill_30_en.srt'
    result=run_comparison(CountingBackend(3.4),cancel,source,folder)
    assert result['slow_down_captions']==30 and result['underfilled_captions']==0
    assert result['average_trailing_silence']<.3 and result['reduction_percent']>50
