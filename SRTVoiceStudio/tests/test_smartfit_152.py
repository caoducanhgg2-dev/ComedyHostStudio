import threading
import numpy as np
import pytest

from studio.continuity import active_bounds, trim_edge_silence
from studio.fitting import fit_processed
from studio.render import Settings
from studio.timeline import Caption, slots_for, RATE


def _tone(seconds, amplitude=.22, frequency=220.0, rate=RATE):
    n = round(seconds * rate)
    t = np.arange(n, dtype=np.float64) / rate
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def test_rms_detector_ignores_low_level_tts_tail_but_keeps_internal_pause():
    active1 = _tone(.55)
    pause = np.zeros(round(.20 * RATE), dtype=np.float32)
    active2 = _tone(.55, frequency=260)
    tail = np.full(round(.35 * RATE), 4e-4, dtype=np.float32)
    audio = np.concatenate([active1, pause, active2, tail])
    start, stop, threshold = active_bounds(audio, RATE)
    assert start == 0
    assert 1.25 < stop / RATE < 1.36
    assert threshold > 4e-4
    trimmed, lead, removed_tail = trim_edge_silence(audio, RATE, True)
    # The internal 200 ms pause remains; only the edge tail is removed.
    assert lead == 0
    assert removed_tail > .20
    assert len(trimmed) / RATE > 1.30
    assert len(trimmed) / RATE < 1.42


def test_continuous_target_is_total_transition_not_second_gap(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'appdata'))
    settings = Settings(gap_ms=100, adaptive=True, continuous=True, continuous_target_ms=100)
    # 1.70 s real speech followed by 0.30 s low-level synthetic tail.  The
    # first caption has a 2.00 s usable slot and the next caption starts at
    # 2.10 s.  Smart Fit should target about 100 ms total audible transition.
    speech = _tone(1.70)
    tail = np.full(round(.30 * RATE), 4e-4, dtype=np.float32)
    processed = np.concatenate([speech, tail])
    captions = [Caption(1, 0, 2000, 'test'), Caption(2, 2100, 4100, 'next')]
    slot = slots_for(captions, settings.gap_ms)[0]
    fitted, record = fit_processed(processed, RATE, slot, settings, 1.0,
                                   tmp_path, threading.Event())
    assert record['target_transition_seconds'] == pytest.approx(.1)
    assert record['target_trailing_seconds'] == pytest.approx(0.0)
    assert record['configured_gap_seconds'] == pytest.approx(.1)
    assert record['post_dsp_trimmed_end'] > .20
    assert record['continuous_refit_passes'] >= 0
    assert .86 <= record['speed'] <= .90
    assert record['transition_silence'] <= .18
    assert record['audible_end_sample'] <= slot.end
    assert slot.start + len(fitted) <= slot.end
    assert not record['trimmed']


def test_continuous_short_script_reports_unreachable_without_overlap(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'appdata'))
    settings = Settings(gap_ms=100, adaptive=True, continuous=True, continuous_target_ms=100)
    processed = _tone(1.0)
    captions = [Caption(1, 0, 3000, 'short'), Caption(2, 3100, 6100, 'next')]
    slot = slots_for(captions, settings.gap_ms)[0]
    fitted, record = fit_processed(processed, RATE, slot, settings, 1.0,
                                   tmp_path, threading.Event())
    assert record['speed'] == pytest.approx(.86)
    assert record['underfilled']
    assert record['underfilled_at_hard_minimum']
    assert 'CONTINUOUS TARGET UNREACHABLE' in record['warning']
    assert slot.start + len(fitted) <= slot.end
    assert record['overlaps'] == 0
