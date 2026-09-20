import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from pathlib import Path
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from studio.continuity import trim_edge_silence
from studio.render import Settings
from studio.v15_core import (estimate_caption, BUILTIN_PRESETS, settings_from_mapping,
    save_batch_queue, load_batch_queue)
from studio.batch import BatchQueue, RUNNING, WAITING


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_continuous_voice_trims_only_outer_silence():
    rate=1000
    signal=np.concatenate([np.zeros(120,dtype=np.float32),np.full(400,.1,dtype=np.float32),np.zeros(180,dtype=np.float32)])
    result,lead,tail=trim_edge_silence(signal,rate,True)
    assert 0.08<lead<0.13
    assert 0.12<tail<0.19
    assert len(result)<len(signal)
    assert np.max(np.abs(result))==pytest.approx(.1)
    untouched,lead2,tail2=trim_edge_silence(signal,rate,False)
    assert len(untouched)==len(signal) and lead2==0 and tail2==0


def test_smart_timeline_preflight_states():
    good=estimate_caption('This is a short natural review line.',3.0,'English US')
    long=estimate_caption(' '.join(['word']*30),2.0,'English US')
    short=estimate_caption('Hi.',8.0,'English US')
    jp=estimate_caption('これは自然な日本語のテストです。',3.0,'Japanese')
    assert good['status']=='ỔN'
    assert long['status']=='NGUY CƠ CẮT'
    assert short['status']=='QUÁ NGẮN'
    assert jp['units']>0 and jp['estimated_seconds']>0


def test_builtin_presets_enable_continuity():
    assert {'JP TikTok Comedy','US Reviewer','Renovation Calm','Horror Narration','Food Challenge'} <= set(BUILTIN_PRESETS)
    for value in BUILTIN_PRESETS.values():
        settings=settings_from_mapping(value)
        assert isinstance(settings,Settings) and settings.continuous
        assert settings.gap_ms == -1
        assert 50<=settings.continuous_target_ms<=250


def test_batch_queue_persistence_recovers_interrupted_item(tmp_path):
    srt=tmp_path/'one.srt';srt.write_text('1\n00:00:00,000 --> 00:00:02,000\nHello world.\n',encoding='utf-8')
    queue=BatchQueue();queue.add([srt],Settings(continuous=True))
    queue.items[0].state=RUNNING;queue.items[0].progress=43
    state=tmp_path/'queue.json';save_batch_queue(queue,state)
    restored=load_batch_queue(state)
    assert len(restored.items)==1
    assert restored.items[0].state==WAITING and restored.items[0].progress==0
    assert restored.items[0].settings.continuous is True


def test_enhanced_window_exposes_five_1_5_workflows(app,tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    from studio.ui import Window
    from studio.v15_upgrade import enhance_window
    w=enhance_window(Window())
    try:
        names=[w.tabs.tabText(i) for i in range(w.tabs.count())]
        assert 'Hàng đợi xử lý' in names
        assert 'So sánh giọng A/B/C/D' in names
        assert 'Smart Timeline Fit 2.0' in names
        assert 'Preset 1.5' in names
        assert hasattr(w,'continuous_voice') and hasattr(w,'continuous_target')
        assert w.settings().continuous is True
        assert w.settings().continuous_target_ms in (80,100,120,150)
        assert w.voice_compare_panel.choices[0].count()>0
        assert w.preset_panel.preset.count()>=5
    finally:
        w.close();w.deleteLater();app.processEvents()
