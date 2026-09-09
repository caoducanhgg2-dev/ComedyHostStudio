"""Distinctive-detail fallback ranking for Comedy Host Studio 5.5.7.

Installed into visual_srt_557 by engine_557.  Keeps generic scene/background
sentences from beating a later, more useful visible change during fallback.
"""
from __future__ import annotations

_SPECIFIC_WORDS = {
    # visible colours / concrete modifiers
    "white","black","red","blue","green","yellow","orange","pink","purple","brown","gray","grey","silver","gold",
    "large","small","tall","short","wide","narrow","broken","open","closed","empty","full","wet","dry",
    # spatial anchors useful to a later writer
    "left","right","center","centre","top","bottom","surface","edge","corner","inside","outside","above","below","behind","front",
    # visible transitions / changes
    "appears","appear","emerges","emerge","enters","enter","exits","exit","leaves","leave","reaches","reach",
    "rises","rise","sinks","sink","descends","descend","ascends","ascend","opens","open","closes","close",
    "turns","turn","lifts","lift","lowers","lower","drops","drop","falls","fall","reveals","reveal",
}

_STATIC_CONTEXT_WORDS = {
    "aquarium","tank","room","house","building","path","ground","background","equipment","filter","filtration","gravel","wall","walls"
}


def install_priority_fallback(visual):
    """Replace only the emergency evidence selector, leaving main writer intact."""
    base = visual.base

    def specificity(sentence):
        words = set(base._words(sentence))
        specific = len(words & _SPECIFIC_WORDS)
        static = len(words & _STATIC_CONTEXT_WORDS)
        # A sentence that mostly establishes an environment is useful once, but
        # should not outrank a concrete new object/movement in later captions.
        return specific * 2.4 - max(0, static - specific) * 0.45

    def fallback_from_evidence(evidence, history, language):
        candidates = []
        recent_words = set(visual._content_words(" ".join(history[-3:])))
        ordinal = 0
        for row in evidence or []:
            for sentence in visual._sentences(row.get("description", ""), language):
                ordinal += 1
                if visual._technical_issue(sentence) or visual.fragment_issue(sentence, language) or visual._inference_issue(sentence, language):
                    continue
                if visual._one_sentence_issue(sentence, language):
                    continue
                n = base._units(sentence, language)
                if language == "en" and not (5 <= n <= 24):
                    continue
                unique = len(set(visual._content_words(sentence)) - recent_words)
                repeated = max((visual._similarity(sentence, old) for old in history[-3:]), default=0.0)
                score = (
                    unique * 2.2
                    + specificity(sentence)
                    - repeated * 5.0
                    - abs(n - 11) * .07
                    + min(ordinal, 6) * .12
                )
                candidates.append((score, sentence))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return base._normalize_punctuation(candidates[0][1], language)
        cleaned = visual._sanitize_evidence(evidence)
        return base._normalize_punctuation(base._deterministic_evidence_sentence(cleaned, language), language)

    visual._fallback_from_evidence = fallback_from_evidence
    return fallback_from_evidence
