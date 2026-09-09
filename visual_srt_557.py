"""Comedy Host Studio 5.5.7 - Visual Continuity SRT.

Information-first factual captions for later ChatGPT rewriting.
5.5.7 removes technical frame/timestamp leakage, prefers one natural sentence,
and avoids repeating unchanged background boilerplate across adjacent captions.
"""
from __future__ import annotations

import difflib
import json
import re

import visual_srt_556 as base
from visual_rules_556 import fragment_issue

VERSION = "5.5.7-visual-continuity"

_STOP = {
    "a","an","the","and","or","but","to","of","in","on","at","for","with","from","into","near","beside","across",
    "he","she","they","it","this","that","these","those","is","are","was","were","be","been","being","has","have","had",
    "scene","video","shows","show","visible","appears","appear","then","now"
}

_TECH_PATTERNS = [
    re.compile(r"\b(?:time|timestamp|frame|frames|pts|pts_time)\s*[:#]?\s*\d+(?:\.\d+)?(?:\s*(?:s|sec|secs|second|seconds))?\b", re.I),
    re.compile(r"\b(?:at|around)\s+\d+(?:\.\d+)?\s*(?:s|sec|secs|second|seconds)\b", re.I),
    re.compile(r"\b(?:across|between|through)\s+(?:the\s+)?frames\b", re.I),
]
_TRAILING_AT_NUMBER = re.compile(r"\s+(?:at|around)\s+\d+(?:\.\d+)?(?=\s*[.!?]?\s*$)", re.I)
_ANALOGY_OBJECT = re.compile(r"\b[a-z]+-like\s+(object|shape|item)\b", re.I)

_INFERENCE_TERMS = (
    "suggesting", "which suggests", "indicating", "which indicates", "agitation", "agitated",
    "erratic", "seems to want", "appears to want", "likely trying", "probably trying",
)
_GENERIC_OPENERS = (
    "the scene shows ", "the video shows ", "in this scene ", "the footage shows ",
)


def _sanitize_text(text):
    value = " ".join(str(text or "").replace("\n", " ").split())
    for rx in _TECH_PATTERNS:
        value = rx.sub("", value)
    value = _TRAILING_AT_NUMBER.sub("", value)
    value = _ANALOGY_OBJECT.sub(r"\1", value)
    value = re.sub(r"\s+([,.;!?])", r"\1", value)
    value = re.sub(r"([,;])\s*([,;])", r"\1", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" ,;:-")
    return value


def _sanitize_evidence(rows):
    out = []
    for row in rows or []:
        out.append({
            "start": row.get("start"), "end": row.get("end"),
            "description": _sanitize_text(row.get("description", ""))[:900],
            "uncertain": _sanitize_text(row.get("uncertain", ""))[:220],
            "mood": row.get("mood", "action"),
        })
    return out


def _technical_issue(text):
    raw = str(text or "")
    if any(rx.search(raw) for rx in _TECH_PATTERNS) or _TRAILING_AT_NUMBER.search(raw):
        return "technical frame/timestamp leakage"
    if re.search(r"\b(?:frame|frames|timestamp|pts_time)\b", raw, re.I):
        return "technical frame wording"
    return ""


def _one_sentence_issue(text, language):
    if language == "ja":
        body = str(text or "").strip().rstrip("。！？")
        if len([p for p in re.split(r"[。！？]+", body) if p.strip()]) > 1:
            return "multiple sentences"
        return ""
    body = str(text or "").strip().rstrip(".!?")
    parts = [p for p in re.split(r"[.!?]+\s+", body) if p.strip()]
    if len(parts) > 1:
        return "multiple sentences"
    return ""


def _inference_issue(text, language):
    if language == "ja":
        bad = ("示唆して", "推測", "興奮している", "不安そう", "狙っている")
        low = str(text or "")
    else:
        bad = _INFERENCE_TERMS
        low = str(text or "").lower()
    return next((x for x in bad if x in low), "")


def _generic_opener_issue(text, language):
    if language != "en":
        return ""
    low = str(text or "").strip().lower()
    return next((x.strip() for x in _GENERIC_OPENERS if low.startswith(x)), "")


def _content_words(text):
    return [w for w in base._words(text) if w not in _STOP and len(w) > 2]


def _similarity(a, b):
    aa, bb = base._clean_key(a), base._clean_key(b)
    if not aa or not bb:
        return 0.0
    seq = difflib.SequenceMatcher(None, aa, bb, autojunk=False).ratio()
    wa, wb = set(_content_words(a)), set(_content_words(b))
    jac = len(wa & wb) / max(1, len(wa | wb))
    return max(seq, jac)


def _recent_similarity_issue(text, history):
    best = (0.0, None)
    for offset, old in enumerate(history[-3:], max(1, len(history)-2)):
        score = _similarity(text, old)
        if score > best[0]:
            best = (score, offset)
    if best[0] >= .82:
        return f"recent boilerplate similarity {best[0]:.2f} to caption {best[1]}"
    return ""


def _quality_issue(text, language, history, check_duplicate=True):
    value = base._normalize_punctuation(_sanitize_text(text), language)
    if not value:
        return "empty"
    tech = _technical_issue(value)
    if tech:
        return tech
    multi = _one_sentence_issue(value, language)
    if multi:
        return multi
    frag = fragment_issue(value, language)
    if frag:
        return frag
    inf = _inference_issue(value, language)
    if inf:
        return "unsupported inference: " + inf
    generic = _generic_opener_issue(value, language)
    if generic:
        return "generic visual-log opener: " + generic
    old_issue = base._speculation_issue(value, language) or base._generic_issue(value, language)
    if old_issue:
        return old_issue
    if base._length_class(value, language) == "hard":
        return f"hard_length={base._units(value, language)}"
    if check_duplicate:
        key = base._clean_key(value)
        if key and any(key == base._clean_key(old) for old in history):
            return "exact duplicate"
    return ""


def _sentences(text, language):
    value = _sanitize_text(text)
    if not value:
        return []
    if language == "ja":
        return [p.strip() + "。" for p in re.split(r"[。！？]+", value) if p.strip()]
    return [base._normalize_punctuation(p.strip(" ,;:-"), language) for p in re.split(r"[.!?]+", value) if p.strip(" ,;:-")]


def _fallback_from_evidence(evidence, history, language):
    """Pick the most distinctive complete evidence sentence; never dump a paragraph."""
    candidates = []
    recent_words = set(_content_words(" ".join(history[-3:])))
    for row in evidence or []:
        for sentence in _sentences(row.get("description", ""), language):
            if _technical_issue(sentence) or fragment_issue(sentence, language) or _inference_issue(sentence, language):
                continue
            if _one_sentence_issue(sentence, language):
                continue
            n = base._units(sentence, language)
            if language == "en" and not (5 <= n <= 24):
                continue
            unique = len(set(_content_words(sentence)) - recent_words)
            repeated = max((_similarity(sentence, old) for old in history[-3:]), default=0.0)
            score = unique * 3.0 - repeated * 4.0 - abs(n - 11) * .08
            candidates.append((score, sentence))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return base._normalize_punctuation(candidates[0][1], language)
    cleaned = _sanitize_evidence(evidence)
    return base._normalize_punctuation(base._deterministic_evidence_sentence(cleaned, language), language)


def _writer_rules(language):
    if language == "ja":
        return (
            "映像だけに基づく、後で書き直しやすい事実中心のSRTを書く。各スロットは自然な一文だけ。"
            "前の字幕ですでに説明した変わらない背景は繰り返さず、現在のスロットで新しく見える動作・物・位置・変化を優先する。"
            "フレーム番号、時刻ラベル、技術情報、推測、感情、目的、比喩を入れない。文字数より正確さと文の完成度を優先する。"
        )
    return (
        "Write factual American-English visual captions for later rewriting. EXACTLY ONE natural standalone sentence per slot. "
        "Accuracy and useful visible detail outrank word count. 8-12 words is ideal, 7-14 normal, and 15-18 is allowed when useful. "
        "Treat unchanged background as already established: do NOT keep repeating the same aquarium/room/path/filter/wall/background description. "
        "For each slot, prioritize the most distinctive NEW or CHANGING visible detail: subject movement, object, direction, position, material, condition, reveal, or visible result. "
        "If the action genuinely continues, describe the current visible state without inventing novelty. Never include frame numbers, timestamps, TIME labels, sampling language, coordinates, or phrases like 'across frames'. "
        "Do not infer emotion, motive, health, danger, intention, agitation, cause, or outcome. Avoid analogies such as '-like object'. "
        "No jokes, hooks, slang, generic 'The scene shows...' wording, raw vision-log fragments, or multiple sentences."
    )


def write_visual_srt_script_557(pipeline, observations, story, duration, language, transcript=None, dialogue_mode=False):
    transcript = transcript or []
    slots = base._slots(float(duration), language)
    total = len(slots)
    meta = []
    for i, (a, b) in enumerate(slots):
        ev = base._evidence_for(observations, a, b)
        meta.append({
            "slot": i + 1, "start": a, "end": b,
            "evidence": _sanitize_evidence(ev),
            "dialogue_context": base._dialogue_for(transcript, a, b, dialogue_mode),
        })

    result = [None] * total
    repairs, fallbacks, warnings, continuity_warnings = [], [], [], []
    technical_repairs, multi_sentence_repairs = [], []
    batch_size = 10 if getattr(pipeline.r, "writer_model", "").startswith("qwen3:8b") else 8

    def structural_validator(expected):
        def validate(obj):
            caps = obj.get("captions")
            if not isinstance(caps, list) or len(caps) != len(expected):
                raise ValueError("caption count mismatch")
            if [int(x.get("slot", 0)) for x in caps] != list(expected):
                raise ValueError("caption slots/order mismatch")
        return validate

    def batch_write(items, previous_lines):
        schema = {"type":"object","properties":{"captions":{"type":"array","minItems":len(items),"maxItems":len(items),
                  "items":{"type":"object","properties":{"slot":{"type":"integer"},"text":{"type":"string"}},
                  "required":["slot","text"],"additionalProperties":False}}},"required":["captions"],"additionalProperties":False}
        payload = [{"slot":x["slot"],"time":[round(x["start"],2),round(x["end"],2)],"evidence":x["evidence"]} for x in items]
        prompt = _writer_rules(language) + "\nRecent accepted captions are context only; do not repeat their unchanged background wording. Return JSON only.\n" + json.dumps({
            "global_setup": _sanitize_text(story.get("setup", ""))[:700],
            "previous_captions": previous_lines[-5:], "slots": payload,
        }, ensure_ascii=False)
        first, last = items[0]["slot"], items[-1]["slot"]
        return pipeline.r.chat(
            "You are a precise visual continuity subtitle writer. Return JSON only.", prompt,
            tokens=max(650, 90 * len(items)), schema=schema,
            validator=structural_validator([x["slot"] for x in items]),
            context=f"Visual Continuity 5.5.7 {first}-{last}",
            diagnostics=pipeline.work/"AI"/f"visual_continuity_557_{language}_{first}_{last}",
            num_ctx=3584, temperature=.14,
        ).get("captions", [])

    def repair_one(item, current, previous_lines, reason, attempt=1):
        schema = {"type":"object","properties":{"slot":{"type":"integer"},"text":{"type":"string"}},
                  "required":["slot","text"],"additionalProperties":False}
        prompt = _writer_rules(language) + "\nRepair only this caption. Preserve the useful visible detail, remove the stated problem, and return one sentence. JSON only.\n" + json.dumps({
            "slot": item["slot"], "time": [round(item["start"],2), round(item["end"],2)],
            "current": current, "problem": reason, "evidence": item["evidence"],
            "previous_captions": previous_lines[-4:],
        }, ensure_ascii=False)
        def validator(obj):
            if int(obj.get("slot",0)) != item["slot"] or not str(obj.get("text","")).strip():
                raise ValueError("invalid repaired caption")
        return pipeline.r.chat(
            "You repair one factual visual caption. Return JSON only.", prompt, tokens=220,
            schema=schema, validator=validator, context=f"Visual 5.5.7 repair {item['slot']}",
            diagnostics=pipeline.work/"AI"/f"visual_repair_557_{language}_{item['slot']}_{attempt}",
            num_ctx=3072, temperature=.10 + .03 * attempt,
        ).get("text", "")

    for start in range(0, total, batch_size):
        items = meta[start:start+batch_size]
        previous_lines = [r["text"] for r in result[:start] if r]
        try:
            caps = batch_write(items, previous_lines)
            by_slot = {int(x.get("slot",0)): str(x.get("text","")).strip() for x in caps}
        except Exception as exc:
            warnings.append({"stage":"batch","slots":[items[0]["slot"],items[-1]["slot"]],"error":str(exc)})
            by_slot = {}

        for item in items:
            slot = item["slot"]
            previous = [r["text"] for r in result[:slot-1] if r]
            candidate = base._normalize_punctuation(_sanitize_text(by_slot.get(slot, "")), language)
            issue = _quality_issue(candidate, language, previous, check_duplicate=False) if candidate else "missing batch caption"
            length_class = base._length_class(candidate, language) if candidate else "hard"

            if issue or length_class == "long_repairable":
                reason = issue or f"long_but_repairable={base._units(candidate, language)}"
                if "technical" in reason:
                    technical_repairs.append(slot)
                if "multiple sentences" in reason:
                    multi_sentence_repairs.append(slot)
                repaired = ""
                for attempt in (1, 2):
                    try:
                        trial = base._normalize_punctuation(_sanitize_text(repair_one(item, candidate, previous, reason, attempt)), language)
                        trial_issue = _quality_issue(trial, language, previous, check_duplicate=False)
                        if not trial_issue and base._length_class(trial, language) != "hard":
                            repaired = trial
                            repairs.append({"caption":slot,"reason":reason,"new_text":trial,"attempt":attempt})
                            break
                        reason = trial_issue or f"length={base._units(trial, language)}"
                    except Exception as exc:
                        reason = str(exc)
                if repaired:
                    candidate = repaired
                else:
                    candidate = _fallback_from_evidence(item["evidence"], previous, language)
                    fallbacks.append({"caption":slot,"reason":reason,"text":candidate})

            # Best-effort continuity repair. Similarity is not fatal because some
            # videos genuinely show the same action for several slots.
            sim_issue = _recent_similarity_issue(candidate, previous)
            if sim_issue and not any(base._clean_key(candidate) == base._clean_key(old) for old in previous):
                try:
                    trial = base._normalize_punctuation(_sanitize_text(repair_one(item, candidate, previous, sim_issue, 3)), language)
                    if not _quality_issue(trial, language, previous, check_duplicate=False) and _similarity(trial, candidate) < .98:
                        candidate = trial
                        repairs.append({"caption":slot,"reason":sim_issue,"new_text":trial,"attempt":3})
                    else:
                        continuity_warnings.append({"caption":slot,"issue":sim_issue,"text":candidate})
                except Exception as exc:
                    continuity_warnings.append({"caption":slot,"issue":sim_issue,"text":candidate,"error":str(exc)})

            # Exact duplicate gets one targeted rewrite. Failure keeps factual text
            # and marks QA; it never aborts the video.
            if any(base._clean_key(candidate) == base._clean_key(old) for old in previous if base._clean_key(old)):
                try:
                    trial = base._normalize_punctuation(_sanitize_text(repair_one(item, candidate, previous, "exact duplicate", 4)), language)
                    if not _quality_issue(trial, language, previous, check_duplicate=True):
                        candidate = trial
                        repairs.append({"caption":slot,"reason":"exact duplicate","new_text":trial,"attempt":4})
                except Exception as exc:
                    warnings.append({"caption":slot,"stage":"exact_dedupe","error":str(exc)})

            result[slot-1] = {
                "start": item["start"], "end": item["end"], "text": candidate,
                "mood": item["evidence"][0].get("mood","action") if item["evidence"] else "action",
                "role": "visual_continuity",
            }
        base._write_json(pipeline.out/"Script_Timeline.json", result)

    exact_duplicates, tech_remaining, fragments, multi_remaining, inference_remaining, similarity_remaining = [], [], [], [], [], []
    history = []
    for i, row in enumerate(result, 1):
        text = row["text"]
        tech = _technical_issue(text)
        if tech: tech_remaining.append({"caption":i,"issue":tech,"text":text})
        frag = fragment_issue(text, language)
        if frag: fragments.append({"caption":i,"issue":frag,"text":text})
        multi = _one_sentence_issue(text, language)
        if multi: multi_remaining.append({"caption":i,"issue":multi,"text":text})
        inf = _inference_issue(text, language)
        if inf: inference_remaining.append({"caption":i,"issue":inf,"text":text})
        key = base._clean_key(text)
        for j, old in enumerate(history, 1):
            if key and key == base._clean_key(old):
                exact_duplicates.append({"caption":i,"first_caption":j,"text":text}); break
        sim = _recent_similarity_issue(text, history)
        if sim: similarity_remaining.append({"caption":i,"issue":sim,"text":text})
        history.append(text)

    visual_context = [{
        "slot": item["slot"], "start": item["start"], "end": item["end"],
        "final_caption": row["text"], "evidence": item["evidence"],
        "dialogue_context_used_for_understanding_only": bool(item["dialogue_context"]),
    } for item, row in zip(meta, result)]
    base._write_json(pipeline.out/"Visual_Context.json", {
        "version": VERSION,
        "purpose": "Sanitized detailed visual evidence for later ChatGPT rewriting; technical frame/timestamp labels removed.",
        "slots": visual_context,
    })
    lengths = [base._units(r["text"], language) for r in result]
    qa = {
        "version": VERSION,
        "architecture": "Visual Brain -> sanitized evidence -> continuity writer -> targeted repair -> one-sentence QC -> SRT",
        "caption_count": total,
        "average_units": round(sum(lengths)/max(1,total), 2), "max_units": max(lengths) if lengths else 0,
        "technical_leakage_remaining": tech_remaining,
        "fragment_captions": fragments,
        "multi_sentence_remaining": multi_remaining,
        "unsupported_inference_remaining": inference_remaining,
        "exact_duplicates": exact_duplicates,
        "recent_similarity_warnings": similarity_remaining,
        "technical_repairs": sorted(set(technical_repairs)),
        "multi_sentence_repairs": sorted(set(multi_sentence_repairs)),
        "repairs": repairs, "emergency_fallbacks": fallbacks, "warnings": warnings,
        "requires_review": bool(tech_remaining or fragments or multi_remaining or inference_remaining or exact_duplicates or fallbacks),
        "policy": "One factual natural sentence per slot. Unchanged background is context, not boilerplate. Technical labels never belong in SRT. Accuracy outranks word count and similarity is non-fatal unless exact duplicate.",
    }
    base._write_json(pipeline.out/"Visual_SRT_QA.json", qa)
    return result
