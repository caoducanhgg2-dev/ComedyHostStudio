from types import SimpleNamespace
from pathlib import Path

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
    cache.put(s, "one", samples, 48000)
    cache.put(s, "two", samples, 48000)
    stats = cache.stats()
    assert stats["items"] == 2 and stats["bytes"] > 0
    cleared = cache.clear()
    assert cleared["items"] == 2 and cache.stats()["items"] == 0


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
    trimmed_issue = next(x for x in report["issues"] if x["code"] == "TRIMMED_CAPTIONS")
    assert isinstance(trimmed_issue.get("captions", []), list)


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


def test_final_encoded_qc_duration_drift_and_click_spike_are_detected(tmp_path):
    from studio.quality import measure_raw_float_file
    raw = tmp_path / "final.raw"
    x = np.zeros(48000, dtype="<f4")
    x[1000] = 0.9
    x[1001] = -0.9
    x.tofile(raw)
    metrics = measure_raw_float_file(raw, 48000)
    assert metrics["samples"] == 48000
    assert metrics["duration_seconds"] == 1.0
    assert metrics["max_step"] >= 1.79

    report = analyze_render(dict(
        overlaps=0,
        safely_trimmed=0,
        underfilled_after_hard_minimum=0,
        transitions_over_08=0,
        auto_sfx=False,
        sfx_planned=0,
        sfx_mixed=0,
        sfx_rejected=0,
        duration_ms=2000,
        master_metrics={"peak": .5, "rms": .1, "dc": 0.0,
                        "clipping_samples": 0, "non_finite": False},
        encoded_metrics=metrics,
    ))
    codes = {x["code"] for x in report["issues"]}
    assert "ENCODE_CLICK_SPIKE" in codes
    assert "ENCODE_DURATION_DRIFT" in codes
    assert report["status"] == "FAIL"


def test_batch_common_settings_preserve_per_file_sfx_overrides(tmp_path):
    from studio.batch import BatchQueue
    from studio.render import Settings
    import threading

    a = tmp_path / "a.srt"
    b = tmp_path / "b.srt"
    body = "1\n00:00:00,000 --> 00:00:01,500\nFinally completed!\n"
    a.write_text(body, encoding="utf-8")
    b.write_text(body, encoding="utf-8")

    queue = BatchQueue()
    base = Settings(language="English US", voice="af_heart")
    items = queue.add([a, b], base)
    items[0].sfx_overrides = ({"caption": 1, "enabled": False, "kind": "chime",
                               "offset_ms": 0, "gain_scale": 1.0},)
    items[1].sfx_overrides = ({"caption": 1, "enabled": True, "kind": "comic",
                               "offset_ms": 100, "gain_scale": 1.3},)

    seen = []
    def fake_renderer(source, output, settings, backend, cancel, progress):
        seen.append((source.name, settings.speed, settings.sfx_overrides))
        Path(output).write_bytes(b"fake")
        return {"output": str(output), "quality": {"status": "PASS"}}

    common = Settings(language="English US", voice="af_heart", speed=1.07)
    queue.run(object(), output_dir=tmp_path / "out", common_settings=common,
              renderer=fake_renderer)

    assert len(seen) == 2
    assert all(speed == 1.07 for _, speed, _ in seen)
    assert seen[0][2][0]["enabled"] is False
    assert seen[1][2][0]["kind"] == "comic"


def test_render_cache_is_used_on_second_render_without_recalling_tts(tmp_path, monkeypatch):
    import threading
    import studio.render as render_module
    from studio.render import Settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    srt = tmp_path / "cache.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,500\nHello cache.\n", encoding="utf-8")

    calls = {"tts": 0}
    raw = (0.05 * np.sin(np.linspace(0, 100, 12000))).astype(np.float32)

    def fake_synth(backend, text, settings, cancel, progress):
        calls["tts"] += 1
        return raw.copy(), 48000

    def fake_fit(samples, rate, slot, settings, emotion_tempo, folder, cancel, previous_speed=None):
        n = min(len(samples), slot.end - slot.start)
        fitted = samples[:n].copy()
        trailing = max(0.0, (slot.end - slot.start - n) / 48000)
        return fitted, dict(
            caption=slot.caption.index, start_sample=slot.start,
            end_sample=slot.start+n, allowed_end=slot.end,
            audible_end_sample=slot.start+n,
            processed_seconds=len(samples)/rate,
            processed_seconds_before_continuity_trim=len(samples)/rate,
            available_seconds=(slot.end-slot.start)/48000,
            classification="FIT", fit_status="GOOD",
            continuous_mode=False, target_transition_seconds=None,
            target_trailing_seconds=.15, configured_gap_seconds=.1,
            speed=1.0, emotion_tempo=1.0, fit_tempo=1.0, requested_speed=1.0,
            trimmed=False, trimmed_samples=0, raw_tail_trimmed_samples=0,
            final_seconds=n/48000, overlaps=0, initial_trailing_seconds=trailing,
            raw_trailing_silence=trailing, internal_audible_trailing_silence=trailing,
            transition_silence=trailing, trailing_silence=trailing,
            underfill_detected=False, underfilled=False, underfill_adjusted=False,
            speed_up=False, slow_down=False, underfilled_at_hard_minimum=False,
            continuous_refit_passes=0, post_dsp_trimmed_start=0.0,
            post_dsp_trimmed_end=0.0, post_dsp_trimmed_seconds=0.0,
            minimum_effective_speed=.88, warning="",
            smart_fit3=False, smart_fit3_neighbor_limited=False,
            previous_caption_speed=previous_speed)

    class FakeProcessor:
        def __init__(self, *args, **kwargs): pass
        def process(self, samples, rate, settings, text):
            return samples, 1.0, "Natural", "Medium"

    def fake_encode(master, destination, cancel):
        Path(destination).write_bytes(b"fake-mp3")

    def fake_mp3_metrics(path, folder, cancel):
        return dict(peak=.4, rms=.08, dc=0.0, clipping_samples=0,
                    clipping_fraction=0.0, non_finite=False,
                    samples=72000, duration_seconds=1.5, max_step=.02)

    monkeypatch.setattr(render_module, "synthesize_selected", fake_synth)
    monkeypatch.setattr(render_module, "fit_processed", fake_fit)
    monkeypatch.setattr(render_module, "EffectProcessor", FakeProcessor)
    monkeypatch.setattr(render_module, "encode", fake_encode)
    monkeypatch.setattr(render_module, "measure_encoded_mp3", fake_mp3_metrics)

    settings = Settings(language="English US", voice="af_heart",
                        use_render_cache=True, gap_ms=100)
    first = render_module.render(
        srt, tmp_path / "one.mp3", settings, object(), threading.Event())
    second = render_module.render(
        srt, tmp_path / "two.mp3", settings, object(), threading.Event())

    assert calls["tts"] == 1
    assert first["cache_hits"] == 0 and first["cache_misses"] == 1
    assert second["cache_hits"] == 1 and second["cache_misses"] == 0


def test_effect_processor_retries_nonfinite_pcm_then_returns_clean_audio(tmp_path, monkeypatch):
    import threading
    import studio.effects as effects

    calls = {"n": 0}
    def fake_run(args, cancel, cwd=None):
        calls["n"] += 1
        target = Path(args[-1])
        if calls["n"] == 1:
            np.asarray([0.0, np.nan, 0.0], dtype="<f4").tofile(target)
        else:
            np.linspace(-.1, .1, 256, dtype="<f4").tofile(target)
        return ""

    monkeypatch.setattr(effects, "run", fake_run)
    processor = effects.EffectProcessor(tmp_path, threading.Event())
    source = np.linspace(-.05, .05, 128, dtype=np.float32)
    result = processor._process(source, 24000, ["anull"])
    assert calls["n"] == 2
    assert len(result) == 256
    assert np.isfinite(result).all()
