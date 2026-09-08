from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("visual_srt_556", ROOT / "visual_srt_556.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
RSPEC = importlib.util.spec_from_file_location("visual_rules_556", ROOT / "visual_rules_556.py")
R = importlib.util.module_from_spec(RSPEC)
RSPEC.loader.exec_module(R)
M._fragment_issue = R.fragment_issue


def test_good_fourteen_word_sentence_is_not_rejected():
    text = "A woman walks along a tiled path toward rustic houses, pulling a pink suitcase."
    assert M._units(text, "en") == 14
    assert M._candidate_issue(text, "en", [], check_duplicate=False) == ""
    assert M._length_class(text, "en") == "normal"


def test_good_seventeen_word_sentence_can_survive():
    text = "A worker carefully clears tall grass along the brick path beside the wooden fence and palm trees."
    assert 15 <= M._units(text, "en") <= 18
    assert M._candidate_issue(text, "en", [], check_duplicate=False) == ""
    assert M._length_class(text, "en") == "extended"


def test_real_fragments_are_detected():
    bad = [
        "with greenery below and white graffiti on the glass.",
        "then exits through a door with frosted glass panels.",
        "green outdoor area with wooden railings and stone paths.",
        "A woman in a white top and black skirt walks away from a wooden.",
        "A woman in a white top and black pants walks along a path surrounded.",
        "trimming grass in a consistent direction.",
    ]
    for text in bad:
        assert M._fragment_issue(text, "en"), text


def test_complete_caption_is_not_fragment():
    good = [
        "The scene shows greenery below and white graffiti on the glass.",
        "The person exits through a door with frosted glass panels.",
        "A worker trims grass along the paved path near the fence.",
        "The house shows signs of abandonment.",
        "Stone and glass are visible near the entrance.",
    ]
    for text in good:
        assert not M._fragment_issue(text, "en"), text


def test_fallback_prefers_complete_first_clause():
    evidence = [{"description":"A woman walks along a tiled path toward rustic houses, pulling a pink suitcase behind her."}]
    out = M._deterministic_evidence_sentence(evidence, "en")
    assert not M._fragment_issue(out, "en")
    assert out.startswith("A woman walks")


def test_fallback_repairs_with_fragment_prefix():
    evidence = [{"description":"with greenery below and white graffiti on the glass."}]
    out = M._deterministic_evidence_sentence(evidence, "en")
    assert out.startswith("The scene shows")
    assert not M._fragment_issue(out, "en")


def test_timeline_gap_and_end():
    slots = M._slots(186.92, "en")
    assert slots[0][0] == 0.0
    assert abs(slots[-1][1] - 186.92) < 1e-6
    for a,b in zip(slots, slots[1:]):
        assert abs((b[0]-a[1])-.10) < 1e-6


if __name__ == "__main__":
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test(); print("PASS", test.__name__)
    print(f"{len(tests)}/{len(tests)} tests passed")
