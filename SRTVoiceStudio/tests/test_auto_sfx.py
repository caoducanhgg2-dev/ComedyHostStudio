import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from studio.sfx import (KIND_LABELS, classify_sfx, plan_sfx, synthesize_sfx,
                        inspect_sfx, mix_auto_sfx)
from studio.render import Settings
from studio.timeline import Caption, RATE


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_every_bundled_sfx_is_deterministic_and_passes_artifact_gate():
    for kind in KIND_LABELS:
        a=synthesize_sfx(kind,'same-seed')
        b=synthesize_sfx(kind,'same-seed')
        assert np.array_equal(a,b)
        qa=inspect_sfx(a)
        assert qa['passed'], (kind,qa)
        assert qa['peak']<=.70
        assert qa['high_frequency_ratio']<.035
        assert abs(float(a[0]))<1e-5 and abs(float(a[-1]))<1e-5


def test_artifact_gate_rejects_dc_click_hiss_and_nonfinite():
    dc=np.ones(round(.2*RATE),dtype=np.float32)*.4
    assert not inspect_sfx(dc)['passed']

    click=np.zeros(round(.2*RATE),dtype=np.float32);click[1000:2000]=.7
    q=inspect_sfx(click);assert not q['passed'] and ('sample_click' in q['reasons'] or 'edge_click' in q['reasons'])

    t=np.arange(round(.25*RATE))/RATE
    hiss_like=(.2*np.sin(2*np.pi*17000*t)*np.hanning(len(t))).astype(np.float32)
    q=inspect_sfx(hiss_like);assert not q['passed'] and 'high_frequency_hiss' in q['reasons']

    bad=np.zeros(round(.2*RATE),dtype=np.float32);bad[30]=np.nan
    assert not inspect_sfx(bad)['passed']


def test_auto_classifier_is_conservative_and_bilingual():
    assert classify_sfx('Finally, the renovation is completed!', 'English US', 'Balanced')[0]=='chime'
    assert classify_sfx('The wall suddenly collapsed with a huge impact.', 'English US', 'Sparse')[0]=='impact'
    assert classify_sfx('完成しました。最高です！', 'Japanese', 'Balanced')[0]=='chime'
    assert classify_sfx('危険です。足元に注意してください。', 'Japanese', 'Balanced')[0]=='suspense'
    assert classify_sfx('This is a normal explanatory sentence.', 'English US', 'Balanced') is None
    assert classify_sfx('普通の説明文です。', 'Japanese', 'Balanced') is None


def test_planner_limits_density_and_never_forces_weak_cues():
    caps=[
        Caption(1,0,3000,'Finally completed!'),
        Caption(2,1000,4000,'Amazing success!'),
        Caption(3,5000,8000,'Then the wall collapsed.'),
        Caption(4,9000,12000,'Plain explanation only.'),
    ]
    events=plan_sfx(caps,'English US','Balanced')
    assert [e.caption_index for e in events]==[1,3]
    assert len({e.caption_index for e in events})==len(events)


def test_planner_aligns_event_near_trigger_inside_long_caption():
    text='We inspect the room, check the floor, move the tools, and after all that the project is finally completed successfully.'
    cap=Caption(1,1000,11000,text)
    event=plan_sfx([cap],'English US','Balanced')[0]
    assert event.kind=='chime'
    assert 6500 < event.start_ms < 10450
    assert event.start_ms >= cap.start+45
    assert event.start_ms+540 <= cap.end-45


def test_mix_keeps_voice_and_headroom_safe():
    caps=[Caption(1,0,4000,'Finally the project is completed successfully!'),
          Caption(2,4100,8100,'This is a normal line without a sound cue.')]
    n=8100*48;t=np.arange(n)/RATE
    master=(.10*np.sin(2*np.pi*180*t)).astype(np.float32)
    before=master.copy()
    settings=Settings(language='English US',auto_sfx=True,sfx_density='Balanced',sfx_strength='Strong')
    report=mix_auto_sfx(master,caps,settings)
    assert report['planned']==1 and report['mixed']==1 and report['rejected']==0
    assert np.isfinite(master).all() and float(np.max(np.abs(master)))<=.88001
    a=round(2.0*RATE);b=round(2.2*RATE)
    assert np.array_equal(master[a:b],before[a:b])
    assert not np.array_equal(master, before)


def test_mix_fail_closed_when_disabled():
    caps=[Caption(1,0,2000,'Finally completed!')]
    master=np.zeros(2000*48,dtype=np.float32);before=master.copy()
    report=mix_auto_sfx(master,caps,Settings(auto_sfx=False))
    assert report['mixed']==0 and report['planned']==0
    assert np.array_equal(master,before)


def test_v16_window_exposes_auto_sfx_and_settings(app,tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    from studio.ui import Window
    from studio.v16_upgrade import enhance_window_v16
    w=enhance_window_v16(Window())
    try:
        names=[w.tabs.tabText(i) for i in range(w.tabs.count())]
        assert 'Auto SFX 1.6' in names
        w.sfx_panel.enabled.setChecked(True)
        w.sfx_panel._set_combo(w.sfx_panel.density,'Balanced')
        w.sfx_panel._set_combo(w.sfx_panel.strength,'Medium')
        s=w.settings()
        assert s.auto_sfx is True and s.sfx_density=='Balanced' and s.sfx_strength=='Medium'
        assert w.preset_panel.preset.count()>=5
    finally:
        w.close();w.deleteLater();app.processEvents()
