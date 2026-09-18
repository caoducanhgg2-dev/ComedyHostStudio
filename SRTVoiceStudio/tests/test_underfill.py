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
    assert .84<r['trailing_silence']<.96 and r['underfilled']
    assert r['warning']=='SHORT SCRIPT / REMAINING SILENCE'
    assert r['end_sample']+1440<=round(4.1*RATE) and r['start_sample']==0 and r['overlaps']==0

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
