"""Comedy Host Studio 5.5.5 - Visual-Grounded SRT writer.

Design goal:
    VIDEO -> Visual evidence -> factual narrative captions -> light QC -> SRT.

This module deliberately does NOT try to create the final viral/comedy script.
It preserves enough concrete visual information for a later ChatGPT rewrite while
keeping CapCut-friendly timing and concise spoken captions.

Integration contract:
    result = write_visual_srt_script_555(
        pipeline, observations, story, duration, language,
        transcript=transcript, dialogue_mode=dialogue_mode,
    )

The function only requires the existing Pipeline object to provide:
    pipeline.r.chat(...), pipeline.work, pipeline.out

No API/cloud dependency is introduced. It continues to use the app-local Ollama
runtime and the current one-model-at-a-time GPU policy.
"""
from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path

VERSION = "5.5.5-visual-grounded"
US_TARGET_MIN = 8
US_TARGET_MAX = 12
US_PREFERRED_MIN = 9
US_PREFERRED_MAX = 11
US_HARD_MIN = 6
US_HARD_MAX = 14
JP_TARGET_MIN = 15
JP_TARGET_MAX = 22
DEFAULT_GAP = 0.10
US_ACTIVE_TARGET = 4.081
JP_ACTIVE_TARGET = 3.50


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text or "").lower().replace("’", "'"))


def _jp_chars(text):
    return [c for c in str(text or "") if re.match(r"[ぁ-んァ-ヶ一-龯々〆ヵヶーA-Za-z0-9]", c)]


def _units(text, language):
    return len(_jp_chars(text)) if language == "ja" else len(_words(text))


def _clean_key(text):
    value = str(text or "").lower().replace("’", "'")
    value = re.sub(r"[^\w\sぁ-んァ-ヶ一-龯ー'-]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _similarity(a, b, language):
    ka, kb = _clean_key(a), _clean_key(b)
    if not ka or not kb:
        return 0.0
    seq = difflib.SequenceMatcher(None, ka, kb, autojunk=False).ratio()
    if language == "ja":
        ca, cb = "".join(_jp_chars(a)), "".join(_jp_chars(b))
        ga = {ca[i:i+2] for i in range(max(0, len(ca)-1))}
        gb = {cb[i:i+2] for i in range(max(0, len(cb)-1))}
    else:
        stop = {"a","an","the","and","or","but","to","of","in","on","at","for","with","from",
                "he","she","they","it","this","that","then","now","is","are","was","were","be",
                "his","her","their"}
        ga = {w for w in _words(a) if w not in stop}
        gb = {w for w in _words(b) if w not in stop}
    jac = len(ga & gb) / max(1, len(ga | gb))
    return max(seq, jac)


def _fragment_issue(text, language):
    value = " ".join(str(text or "").strip().split())
    if not value:
        return "empty"
    if language == "ja":
        compact = re.sub(r"\s+", "", value).rstrip("。！？")
        if compact.endswith(("けど", "ので", "から", "ながら", "そして", "でも")):
            return "dangling Japanese connective"
        return ""

    words = _words(value)
    if not words:
        return "empty"
    first, last = words[0], words[-1]
    if first in {"but","and","which","because","while","although","though","unless","as"}:
        return "starts with dependent conjunction"
    # Visual logs often leak as gerund/participle fragments.
    if first in {
        "approaching","walking","moving","showing","revealing","carrying","holding","placing","adding",
        "cutting","building","stacking","opening","closing","entering","leaving","standing","sitting",
        "kneeling","arranging","cleaning","removing","installing","crossing","following"
    }:
        return "starts like a visual-log fragment"
    if last in {"than","what","which","who","whom","whose","because","while","although","though","until",
                "if","and","but","or","to","of","with","for","from","is","are","was","were","be","been",
                "being","how"}:
        return "ends with dangling word"
    return ""


def _speculation_issue(text, language):
    value = str(text or "").lower()
    if language == "ja":
        bad = ("たぶん", "きっと", "秘密", "呪い", "幽霊", "超常", "考えている", "狙っている", "企んでいる")
    else:
        bad = (
            "probably", "maybe", "must be", "secretly", "obviously", "definitely", "long-lost",
            "ghost", "haunted", "war zone", "supernatural", "ritual", "portal", "secret chamber",
            "plans to", "planning to", "wants to", "thinking about", "believes", "feels like"
        )
    return next((x for x in bad if x in value), "")


def _generic_issue(text, language):
    value = _clean_key(text)
    if language == "ja":
        generic = ("作業が続きます", "進んでいます", "少しずつ変わります", "同じ作業です")
    else:
        generic = (
            "the process continues", "he keeps working", "she keeps working", "they keep working",
            "more progress is happening", "the work continues", "things are taking shape",
            "the setup is taking shape", "progress continues", "the scene continues"
        )
    return next((x for x in generic if x in value), "")


def _slots(duration, language, gap=DEFAULT_GAP):
    target = JP_ACTIVE_TARGET if language == "ja" else US_ACTIVE_TARGET
    count = max(1, math.ceil((duration + gap) / (target + gap)))
    while count > 1 and duration - gap * (count - 1) <= count * .50:
        count -= 1
    active = (duration - gap * (count - 1)) / count
    result, cursor = [], 0.0
    for i in range(count):
        start = cursor
        end = duration if i == count - 1 else start + active
        result.append((round(start, 6), round(end, 6)))
        cursor = end + gap
    return result


def _budget_ok(text, language):
    n = _units(text, language)
    if language == "ja":
        return JP_TARGET_MIN <= n <= JP_TARGET_MAX
    return US_TARGET_MIN <= n <= US_TARGET_MAX


def _hard_budget_ok(text, language):
    n = _units(text, language)
    if language == "ja":
        return 10 <= n <= 26
    return US_HARD_MIN <= n <= US_HARD_MAX


def _normalize_punctuation(text, language):
    value = " ".join(str(text or "").strip().split())
    if not value:
        return value
    if language == "ja":
        return value if value.endswith(("。", "！", "？")) else value + "。"
    return value if value.endswith((".", "!", "?")) else value + "."


def _candidate_issue(text, language, history, strict_budget=False):
    value = _normalize_punctuation(text, language)
    if not value:
        return "empty"
    if re.search(r"\[(?:pause|sfx|music|laugh|beat)\]|<[^>]+>", value, re.I):
        return "technical/stage direction"
    frag = _fragment_issue(value, language)
    if frag:
        return frag
    spec = _speculation_issue(value, language)
    if spec:
        return "speculative phrase: " + spec
    generic = _generic_issue(value, language)
    if generic:
        return "generic filler: " + generic
    if strict_budget and not _budget_ok(value, language):
        return f"budget={_units(value, language)}"
    if not _hard_budget_ok(value, language):
        return f"hard_budget={_units(value, language)}"
    key = _clean_key(value)
    if key and any(key == _clean_key(old) for old in history):
        return "exact duplicate"
    return ""


def _best_evidence_clause(evidence, language):
    """Emergency-only factual fallback; never emits the entire raw vision paragraph."""
    descriptions = [str(x.get("description", "")).strip() for x in evidence if str(x.get("description", "")).strip()]
    if not descriptions:
        return "映像では同じ動作が続いています。" if language == "ja" else "The visible action continues within this part of the scene."

    candidates = []
    for description in descriptions:
        normalized = description.replace("—", ".").replace("–", ".").replace(";", ".")
        pieces = [x.strip(" ,.-") for x in re.split(r"[.!?。！？]+|,(?=\s)", normalized) if x.strip(" ,.-")]
        candidates.extend(pieces)

    if language == "ja":
        good = [x for x in candidates if 10 <= _units(x, language) <= 26 and not _fragment_issue(x, language)]
        if good:
            return _normalize_punctuation(min(good, key=lambda x: abs(_units(x, language)-18)), language)
        compact = re.sub(r"\s+", "", candidates[0] if candidates else descriptions[0])
        return _normalize_punctuation("".join(_jp_chars(compact)[:24]), language)

    good = [x for x in candidates if US_HARD_MIN <= _units(x, language) <= US_HARD_MAX and not _fragment_issue(x, language)]
    if good:
        return _normalize_punctuation(min(good, key=lambda x: abs(_units(x, language)-10)), language)

    # Last resort: prefer a short beginning of a real evidence sentence. This is
    # intentionally marked for review by the caller; it never dumps 30-40 words.
    base = candidates[0] if candidates else descriptions[0]
    words = re.findall(r"\S+", base)
    trimmed = " ".join(words[:US_HARD_MAX]).strip(" ,.-")
    if _fragment_issue(trimmed, language):
        # Avoid gerund/dependent starts by using a neutral visual anchor. This may
        # be less elegant, but it remains truthful and bounded.
        trimmed = "The scene shows " + " ".join(words[:max(3, US_HARD_MAX-3)])
    return _normalize_punctuation(trimmed, language)


def _evidence_for(observations, a, b):
    nearby = [o for o in observations if float(o.get("start", 0)) < b and float(o.get("end", 0)) > a]
    if not nearby and observations:
        center = (a + b) / 2
        nearby = [min(observations, key=lambda o: abs((float(o.get("start", 0))+float(o.get("end", 0)))/2-center))]
    return [{
        "start": round(float(o.get("start", 0)), 2),
        "end": round(float(o.get("end", 0)), 2),
        "description": str(o.get("description", ""))[:700],
        "uncertain": str(o.get("uncertain", ""))[:180],
        "mood": str(o.get("mood", "action")),
    } for o in nearby]


def _dialogue_for(transcript, a, b, enabled):
    if not enabled:
        return []
    rows = []
    for seg in transcript or []:
        if float(seg.get("start", 0)) < b and float(seg.get("end", 0)) > a:
            rows.append({
                "start": round(float(seg.get("start", 0)), 2),
                "end": round(float(seg.get("end", 0)), 2),
                "text": str(seg.get("text", ""))[:280],
            })
    return rows[:4]


def _writer_rules(language):
    if language == "ja":
        return (
            "映像に忠実な日本語SRTを書く。最終的なバズ台本ではなく、後で別のWriterが書き直せる情報量のある映像ナレーションを作る。 "
            "映像に見える人物・動作・物・場所の状態・変化・前後関係を優先する。目的、感情、背景、経過時間、見えない結果は推測しない。 "
            "通常15〜22文字程度。短い断片、名詞だけ、映像ログ、同じ文の再利用は禁止。無理に面白くしない。"
        )
    return (
        "Write factual American English visual-narrative captions. This is NOT the final viral/comedy script. "
        "Preserve enough concrete visual information that another writer can later rewrite the SRT creatively without rewatching every frame. "
        "Prioritize visible subject + action + object/material + visible condition/change/relationship when available. "
        "Do not invent motive, thoughts, emotion, identity, backstory, danger, elapsed time, hidden purpose, or off-screen outcome. "
        "Use natural complete sentences, normally 8-12 spoken words; 9-11 is preferred, but do not damage meaning just to hit a number. "
        "Never output raw vision-log paragraphs, fragments, generic filler, stage directions, jokes, clickbait, hooks, catchphrases, or slang. "
        "If the same action genuinely continues, describe the visible change or concrete object accurately; semantic similarity is allowed. Exact sentence reuse is not."
    )


def write_visual_srt_script_555(pipeline, observations, story, duration, language,
                                transcript=None, dialogue_mode=False):
    """Create a factual, information-rich, rewrite-friendly SRT timeline.

    Reliability policy:
      * Batch failure never discards good captions from other slots.
      * A bad slot is repaired independently.
      * Raw Visual Brain descriptions can never be emitted directly.
      * Exact duplicate is repaired; ordinary same-action similarity is allowed.
      * Word count is a flexible target, not a hard 10-word lock.
      * Final export should continue with review flags rather than crash for one
        recoverable caption.
    """
    transcript = transcript or []
    slots = _slots(float(duration), language)
    total = len(slots)
    meta = []
    for idx, (a, b) in enumerate(slots, 1):
        meta.append({
            "slot": idx,
            "start": a,
            "end": b,
            "evidence": _evidence_for(observations, a, b),
            "dialogue_context": _dialogue_for(transcript, a, b, dialogue_mode),
        })

    result = [None] * total
    repairs = []
    fallbacks = []
    warnings = []
    batch_size = 8 if getattr(pipeline.r, "writer_model", "").startswith("qwen3:8b") else 6

    def structural_validator(expected_slots):
        expected_slots = list(expected_slots)
        def validate(obj):
            caps = obj.get("captions")
            if not isinstance(caps, list) or len(caps) != len(expected_slots):
                raise ValueError("caption count mismatch")
            got = [int(x.get("slot", 0)) for x in caps]
            if got != expected_slots:
                raise ValueError("caption slots/order mismatch")
        return validate

    def batch_write(items, previous_lines):
        schema = {
            "type": "object",
            "properties": {
                "captions": {
                    "type": "array", "minItems": len(items), "maxItems": len(items),
                    "items": {
                        "type": "object",
                        "properties": {"slot": {"type": "integer"}, "text": {"type": "string"}},
                        "required": ["slot", "text"], "additionalProperties": False,
                    },
                }
            },
            "required": ["captions"], "additionalProperties": False,
        }
        payload = [{
            "slot": x["slot"], "time": [round(x["start"], 2), round(x["end"], 2)],
            "evidence": x["evidence"], "dialogue_context": x["dialogue_context"],
        } for x in items]
        context = {
            "global_setup": str(story.get("setup", ""))[:900],
            "global_ending": str(story.get("ending", ""))[:900],
            "previous_captions": previous_lines[-4:],
            "slots": payload,
        }
        prompt = (
            _writer_rules(language) +
            "\nWrite exactly one caption for every supplied slot, in order. Each caption must describe ONLY that slot's evidence. "
            "Dialogue context, when present, is meaning/context only; do not transcribe it. Do not force different wording when the same visual action truly continues, "
            "but never repeat an identical sentence. Return JSON only.\n" + json.dumps(context, ensure_ascii=False)
        )
        first, last = items[0]["slot"], items[-1]["slot"]
        return pipeline.r.chat(
            "You are a precise visual-narrative subtitle writer. Return JSON only.",
            prompt,
            tokens=max(600, 100*len(items)),
            schema=schema,
            validator=structural_validator([x["slot"] for x in items]),
            context=f"Visual Narrative {first}-{last}",
            diagnostics=pipeline.work/"AI"/f"visual_narrative_555_{language}_{first}_{last}",
            num_ctx=4096,
            temperature=.22,
        ).get("captions", [])

    def repair_one(item, current, previous_lines, reason, attempt=1):
        schema = {
            "type": "object",
            "properties": {"slot": {"type": "integer"}, "text": {"type": "string"}},
            "required": ["slot", "text"], "additionalProperties": False,
        }
        context = {
            "slot": item["slot"],
            "time": [round(item["start"], 2), round(item["end"], 2)],
            "current": current,
            "problem": reason,
            "evidence": item["evidence"],
            "dialogue_context": item["dialogue_context"],
            "previous_captions": previous_lines[-4:],
        }
        if language == "ja":
            budget = "自然な一文。通常15〜22文字。"
        else:
            budget = "Use a complete natural sentence, normally 8-12 words; 9-11 preferred."
        prompt = (
            _writer_rules(language) +
            "\nRepair this ONE caption from its own evidence. Do not paraphrase unsupported parts of the current text; rebuild from evidence. "
            + budget + " Exact duplicate is forbidden. Return JSON only.\n" + json.dumps(context, ensure_ascii=False)
        )
        def validator(obj):
            if int(obj.get("slot", 0)) != item["slot"]:
                raise ValueError("wrong slot")
            if not str(obj.get("text", "")).strip():
                raise ValueError("empty text")
        return pipeline.r.chat(
            "You are the per-caption visual-grounding repair editor. Return JSON only.",
            prompt,
            tokens=220,
            schema=schema,
            validator=validator,
            context=f"Visual Repair {item['slot']} attempt {attempt}",
            diagnostics=pipeline.work/"AI"/f"visual_repair_555_{language}_{item['slot']}_{attempt}",
            num_ctx=4096,
            temperature=.18 + .05*attempt,
        ).get("text", "")

    # Main batch pass. Batch validation is STRUCTURAL ONLY, so one imperfect line
    # never causes six/seven other good captions to be thrown away.
    for start in range(0, total, batch_size):
        items = meta[start:start+batch_size]
        previous_lines = [r["text"] for r in result[:start] if r]
        try:
            caps = batch_write(items, previous_lines)
            by_slot = {int(x.get("slot", 0)): str(x.get("text", "")).strip() for x in caps}
        except Exception as exc:
            warnings.append({"stage": "batch", "slots": [items[0]["slot"], items[-1]["slot"]], "error": str(exc)})
            by_slot = {}

        for item in items:
            slot = item["slot"]
            previous = [r["text"] for r in result[:slot-1] if r]
            candidate = _normalize_punctuation(by_slot.get(slot, ""), language)
            issue = _candidate_issue(candidate, language, previous, strict_budget=False) if candidate else "missing batch caption"

            # Preferred range is repaired, but flexibility wins over artificial filler.
            if not issue and not _budget_ok(candidate, language):
                issue = f"outside preferred target range: {_units(candidate, language)}"

            if issue:
                repaired = ""
                last_issue = issue
                for attempt in (1, 2):
                    try:
                        trial = _normalize_punctuation(repair_one(item, candidate, previous, last_issue, attempt), language)
                        trial_issue = _candidate_issue(trial, language, previous, strict_budget=False)
                        if not trial_issue and _budget_ok(trial, language):
                            repaired = trial
                            repairs.append({"caption": slot, "reason": issue, "new_text": trial, "attempt": attempt})
                            break
                        # 7/13-word complete factual sentences are acceptable only
                        # after repair attempts; do not force filler for a number.
                        if not trial_issue and _hard_budget_ok(trial, language):
                            repaired = trial
                            repairs.append({"caption": slot, "reason": issue, "new_text": trial,
                                            "attempt": attempt, "soft_budget_accept": True})
                            break
                        last_issue = trial_issue or f"budget={_units(trial, language)}"
                    except Exception as exc:
                        last_issue = str(exc)
                if repaired:
                    candidate = repaired
                else:
                    candidate = _best_evidence_clause(item["evidence"], language)
                    fallbacks.append({"caption": slot, "reason": last_issue, "text": candidate})

            # Exact duplicate repair only. Do NOT reject ordinary continuing-action
            # similarity, because it may be the accurate description of the video.
            if any(_clean_key(candidate) == _clean_key(old) for old in previous if _clean_key(old)):
                try:
                    trial = _normalize_punctuation(repair_one(item, candidate, previous, "exact duplicate", 3), language)
                    if not _candidate_issue(trial, language, previous, strict_budget=False):
                        candidate = trial
                        repairs.append({"caption": slot, "reason": "exact duplicate", "new_text": trial, "attempt": 3})
                except Exception as exc:
                    warnings.append({"caption": slot, "stage": "dedupe", "error": str(exc)})

            result[slot-1] = {
                "start": item["start"], "end": item["end"], "text": candidate,
                "mood": item["evidence"][0].get("mood", "action") if item["evidence"] else "action",
                "role": "visual_narrative",
            }

        _write_json(pipeline.out/"Script_Timeline.json", result)

    # Final non-destructive QA. Problems are flagged for review, never used to
    # discard the entire SRT.
    budget_outside = []
    fragments = []
    exact_duplicates = []
    speculation = []
    generic = []
    history = []
    for i, row in enumerate(result, 1):
        n = _units(row["text"], language)
        if not _budget_ok(row["text"], language):
            budget_outside.append({"caption": i, "units": n, "text": row["text"]})
        frag = _fragment_issue(row["text"], language)
        if frag:
            fragments.append({"caption": i, "issue": frag, "text": row["text"]})
        spec = _speculation_issue(row["text"], language)
        if spec:
            speculation.append({"caption": i, "issue": spec, "text": row["text"]})
        gen = _generic_issue(row["text"], language)
        if gen:
            generic.append({"caption": i, "issue": gen, "text": row["text"]})
        key = _clean_key(row["text"])
        for j, old in enumerate(history, 1):
            if key and key == _clean_key(old):
                exact_duplicates.append({"caption": i, "first_caption": j, "text": row["text"]})
                break
        history.append(row["text"])

    visual_context = []
    for item, row in zip(meta, result):
        visual_context.append({
            "slot": item["slot"], "start": item["start"], "end": item["end"],
            "final_caption": row["text"], "evidence": item["evidence"],
            "dialogue_context_used_for_understanding_only": bool(item["dialogue_context"]),
        })
    _write_json(pipeline.out/"Visual_Context.json", {
        "version": VERSION,
        "purpose": "Detailed visual evidence for later script rewriting; not production subtitles.",
        "slots": visual_context,
    })

    within_target = total - len(budget_outside)
    qa = {
        "version": VERSION,
        "architecture": "Visual Brain -> evidence map -> factual narrative writer -> per-slot repair -> basic exact-repeat QC -> SRT",
        "caption_count": total,
        "us_target_words": "8-12, preferred 9-11; no exact-10 requirement" if language == "en" else None,
        "jp_target_chars": "15-22" if language == "ja" else None,
        "within_target_count": within_target,
        "within_target_ratio": round(within_target/max(1, total), 3),
        "average_units": round(sum(_units(r["text"], language) for r in result)/max(1, total), 2),
        "budget_outside": budget_outside,
        "fragment_captions": fragments,
        "exact_duplicates": exact_duplicates,
        "speculation_warnings": speculation,
        "generic_filler_warnings": generic,
        "repairs": repairs,
        "emergency_fallbacks": fallbacks,
        "batch_warnings": warnings,
        "requires_review": bool(fragments or exact_duplicates or speculation or generic or fallbacks),
        "policy": (
            "Accuracy and rewriteable visual detail come first. Same-action semantic similarity is allowed. "
            "One bad caption never aborts the whole SRT. Raw vision paragraphs are never exported directly."
        ),
    }
    _write_json(pipeline.out/"Visual_SRT_QA.json", qa)
    return result
