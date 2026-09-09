from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("visual_srt_557", ROOT / "visual_srt_557.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
from visual_priority_557 import install_priority_fallback
install_priority_fallback(M)


def test_timestamp_number_leak_is_removed():
    src = "A small white object appears near the bottom at 11."
    out = M._sanitize_text(src)
    assert out == "A small white object appears near the bottom."
    assert not M._technical_issue(out)


def test_explicit_frame_language_is_removed_or_blocked():
    src = "Fish movement overlaps across frames, suggesting active swimming."
    clean = M._sanitize_text(src)
    assert "frames" not in clean.lower()
    assert M._inference_issue(clean, "en")


def test_flame_like_object_becomes_neutral_object():
    src = "A small orange flame-like object appears near the bottom left."
    out = M._sanitize_text(src)
    assert "flame-like" not in out.lower()
    assert "orange object" in out.lower()


def test_multi_sentence_raw_observation_is_rejected():
    src = "Fish swim in an aquarium with gravel and a filter. Bubbles rise. A white fish appears near the surface."
    assert M._one_sentence_issue(src, "en") == "multiple sentences"


def test_good_single_sentence_is_accepted():
    src = "A white fish rises near the surface beside the bubbling filter."
    assert M._quality_issue(src, "en", [], check_duplicate=True) == ""


def test_repeated_aquarium_boilerplate_is_detected_as_soft_continuity_issue():
    old = "Fish swim in an aquarium with gravel and a filter while bubbles rise."
    new = "Fish swim in the aquarium with gravel and filtration as bubbles rise."
    issue = M._recent_similarity_issue(new, [old])
    assert issue.startswith("recent boilerplate similarity")


def test_exact_duplicate_stays_hard_issue():
    src = "Fish move in different directions near the filter."
    assert M._quality_issue(src, "en", [src], check_duplicate=True) == "exact duplicate"


def test_inference_terms_are_rejected():
    bad = "Fish movement is erratic, suggesting agitation near the surface."
    assert "unsupported inference" in M._quality_issue(bad, "en", [], check_duplicate=False)


def test_fallback_prefers_new_distinctive_detail_over_static_background():
    history = ["Several fish cross the tank while bubbles rise behind them."]
    evidence = [{
        "description": "Fish swim in an aquarium with gravel and a filter. Bubbles rise. A white fish appears near the surface.",
        "start": 0, "end": 4, "uncertain": "", "mood": "action"
    }]
    out = M._fallback_from_evidence(evidence, history, "en")
    assert "white fish" in out.lower()
    assert M._one_sentence_issue(out, "en") == ""


def test_timing_policy_is_unchanged():
    slots = M.base._slots(67.25, "en")
    assert slots[0][0] == 0.0
    assert abs(slots[-1][1] - 67.25) < 1e-6
    for a, b in zip(slots, slots[1:]):
        assert abs((b[0] - a[1]) - .10) < 1e-6


if __name__ == "__main__":
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test(); print("PASS", test.__name__)
    print(f"{len(tests)}/{len(tests)} tests passed")
