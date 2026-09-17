import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from studio.render import Settings
from studio.timeline import Caption, RATE
from studio.sfx_161 import apply_patch, speaker_band_ratio, mix_auto_sfx

sfx = apply_patch()


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_impact_and_suspense_have_phone_speaker_band_energy():
    for kind in ('impact', 'suspense'):
        audio = sfx.synthesize_sfx(kind, 'audibility-test')
        qa = sfx.inspect_sfx(audio)
        assert qa['passed'], (kind, qa)
        assert speaker_band_ratio(audio) >= .08, (kind, speaker_band_ratio(audio))
        assert float(np.max(np.abs(audio))) <= .70001


def test_medium_mix_is_audible_but_keeps_voice_and_headroom_safe():
    caps = [Caption(1, 0, 4000, 'Finally completed successfully!')]
    n = 4000 * 48
    t = np.arange(n) / RATE
    master = (.10 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)
    before = master.copy()
    settings = Settings(language='English US', auto_sfx=True,
                        sfx_density='Balanced', sfx_strength='Medium')
    report = mix_auto_sfx(master, caps, settings)
    assert report['planned'] == 1 and report['mixed'] == 1 and report['rejected'] == 0
    event = report['events'][0]
    assert event['mixed'] is True
    assert event['relative_rms'] >= .22
    assert float(np.max(np.abs(master))) <= .88001
    assert np.isfinite(master).all()
    assert not np.array_equal(master, before)


def test_sfx_off_remains_bit_identical():
    caps = [Caption(1, 0, 2500, 'Finally completed!')]
    master = np.linspace(-.1, .1, 2500 * 48, dtype=np.float32)
    before = master.copy()
    report = mix_auto_sfx(master, caps, Settings(auto_sfx=False))
    assert report['planned'] == 0 and report['mixed'] == 0 and report['rejected'] == 0
    assert np.array_equal(master, before)


def test_161_result_formatter_reports_planned_mixed_rejected():
    from studio.v161_upgrade import format_sfx_result
    status, details = format_sfx_result({
        'auto_sfx': True,
        'sfx_planned': 6,
        'sfx_mixed': 5,
        'sfx_rejected': 1,
        'sfx_density': 'Balanced',
        'sfx_strength': 'Medium',
        'sfx_events': [
            {'caption': 2, 'label': 'Chime thành công', 'mixed': True,
             'gain': .42, 'relative_rms': .31, 'speaker_band_ratio': .88},
            {'caption': 9, 'kind': 'suspense', 'mixed': False,
             'reason': 'insufficient_headroom'},
        ],
    })
    assert '5/6' in status and '1 bị loại' in status
    assert 'planned 6' in details and 'mixed 5' in details and 'rejected 1' in details
    assert 'insufficient_headroom' in details


def test_161_window_has_sfx_preview_controls(app, tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    from studio.ui import Window
    from studio.v161_upgrade import enhance_window_v161
    w = enhance_window_v161(Window())
    try:
        names = [w.tabs.tabText(i) for i in range(w.tabs.count())]
        assert 'Auto SFX 1.6.1' in names
        assert w.sfx_panel.preview_kind.count() == len(sfx.KIND_LABELS)
        assert w.sfx_panel.preview_button.text().startswith('▶')
    finally:
        w.close(); w.deleteLater(); app.processEvents()
