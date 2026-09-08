from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("visual_srt_555", HERE / "visual_srt_555.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_us_slots_full_timeline_and_gap():
    duration = 186.9
    slots = M._slots(duration, "en")
    assert slots[0][0] == 0.0
    assert abs(slots[-1][1] - duration) < 1e-6
    for prev, cur in zip(slots, slots[1:]):
        assert abs((cur[0] - prev[1]) - 0.10) < 1e-6
    active = [b-a for a,b in slots[:-1]]
    assert 3.5 < sum(active)/len(active) < 4.5


def test_word_count_is_flexible_not_exact_ten():
    assert M._budget_ok("Another wooden panel closes the remaining roof gap.", "en")
    assert M._budget_ok("Another wooden panel closes the last visible gap across the roof.", "en")
    assert not M._budget_ok("He works.", "en")


def test_fragments_are_rejected():
    assert M._fragment_issue("As the camera follows her toward the bridge.", "en")
    assert M._fragment_issue("Approaching the wooden bridge near the garden.", "en")
    assert not M._fragment_issue("She approaches the wooden bridge beside the garden.", "en")


def test_generic_fillers_are_flagged():
    assert M._generic_issue("The process continues.", "en")
    assert M._generic_issue("Things are taking shape.", "en")
    assert not M._generic_issue("Another stone closes the visible gap around the pipe.", "en")


def test_same_action_similarity_is_not_a_hard_error():
    history = ["He stacks flat stones around the circular pipe opening."]
    candidate = "Another stone fills the exposed gap beside the pipe."
    # Only exact sentence reuse is hard in 5.5.5 visual mode.
    assert M._candidate_issue(candidate, "en", history, strict_budget=False) == ""
    assert M._candidate_issue(history[0], "en", history, strict_budget=False) == "exact duplicate"


def test_emergency_fallback_never_dumps_long_visual_paragraph():
    evidence = [{
        "description": (
            "A woman walks along a garden path toward a wooden pavilion, while several chairs, bamboo screens, "
            "green plants, stone decorations, and other architectural details remain visible around the area."
        )
    }]
    value = M._best_evidence_clause(evidence, "en")
    assert M._units(value, "en") <= M.US_HARD_MAX + 3  # neutral anchor may add three words
    assert len(value) < len(evidence[0]["description"])


def test_speculative_language_is_flagged():
    assert M._speculation_issue("She probably has a secret plan for this room.", "en")
    assert M._speculation_issue("The hallway looks cleaned by a ghost.", "en")
    assert not M._speculation_issue("She carries the wooden panel into the room.", "en")


def test_japanese_budget_is_preserved():
    assert M._budget_ok("木の板を壁沿いに丁寧に並べていきます。", "ja")


if __name__ == "__main__":
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(f"{len(tests)}/{len(tests)} tests passed")
