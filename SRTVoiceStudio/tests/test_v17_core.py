from types import SimpleNamespace

import numpy as np

from studio.quality import analyze_render, measure_master
from studio.render_cache import TtsCache, cache_key
from studio.smartfit3 import smooth_speed
from studio.sfx import SfxEvent
from studio.sfx_editor import apply_sfx_overrides
from studio.timeline import Caption


def _settings(**kwargs):
    base = dict(language="Japanese", voice="jf_alpha", native_style=None)
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_render_cache_roundtrip_and_key_is_voice_text_style_specific(tmp_path):
    cache = TtsCache(tmp_path / "cache")
    s = _settings()
    samples = np.sin(np.linspace(0, 20, 4800)).astype(np.float32) * .1
    assert cache.get(s, "テスト") is None
    assert cache.put(s, "テスト", samples, 48000)
    got, rate = cache.get(s, "テスト")
    assert rate == 48000
    assert np.allclose(got, samples)
    assert cache_key(s, "テスト") != cache_key(_settings(voice="jm_kumo"), "テスト")
    assert cache_key(s, "テスト") != cache_key(s, "別の文")
    assert cache.invalidate(s, "テスト")
    assert cache.get(s, "テスト") is None


def test_quality_control_reports_trim_sfx_and_clipping():
    master = np.zeros(2000, dtype=np.float32)
    master[100:200] = 1.0
    metrics = measure_master(master)
    report = analyze_render(dict(
        overlaps=0,
        safely_trimmed=2,
        underfilled_after_hard_minimum=1,
        transitions_over_08=1,
        auto_sfx=True,
        sfx_planned=3,
        sfx_mixed=2,
        sfx_rejected=1,
        master_metrics=metrics,
    ))
    assert report["status"] == "FAIL"
    codes = {x["code"] for x in report["issues"]}
    assert {"CLIPPING", "TRIMMED_CAPTIONS", "SFX_REJECTED"} <= codes


def test_smart_fit3_smooths_only_when_slot_stays_safe():
    value, changed = smooth_speed(1.20, 1.00, 1.08, "OVERFLOW", .86, 1.20)
    assert changed and value == 1.10
    value, changed = smooth_speed(1.20, 1.00, 1.18, "OVERFLOW", .86, 1.20)
    assert not changed and value == 1.20


def test_manual_sfx_override_can_disable_replace_shift_and_add():
    captions = [
        Caption(1, 0, 3000, "完成"),
        Caption(2, 3100, 6500, "普通の文"),
    ]
    events = [SfxEvent(1, 800, "chime", 4, "完成")]
    edited = apply_sfx_overrides(events, captions, (
        {"caption": 1, "enabled": True, "kind": "comic", "offset_ms": 100, "gain_scale": 1.2},
        {"caption": 2, "enabled": True, "kind": "transition", "offset_ms": 0, "gain_scale": .8},
    ))
    assert len(edited) == 2
    first = next(e for e in edited if e.caption_index == 1)
    second = next(e for e in edited if e.caption_index == 2)
    assert first.kind == "comic" and first.manual and first.gain_scale == 1.2
    assert second.kind == "transition" and second.manual
    assert second.start_ms >= captions[1].start
