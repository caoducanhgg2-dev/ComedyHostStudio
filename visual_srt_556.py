"""Comedy Host Studio 5.5.6 - information-first Visual-Grounded SRT writer.

Goal: preserve accurate, useful visual information for later ChatGPT rewriting.
Word count is guidance, never more important than a complete factual sentence.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

VERSION = "5.5.6-visual-quality-stability"
DEFAULT_GAP = 0.10
US_ACTIVE_TARGET = 4.081
JP_ACTIVE_TARGET = 3.50

# US length policy. 8-12 is aesthetically ideal, not a validity gate.
US_IDEAL_MIN = 8
US_IDEAL_MAX = 12
US_NORMAL_MIN = 7
US_NORMAL_MAX = 14
US_EXTENDED_MAX = 18
US_ABSOLUTE_MAX = 24
US_ABSOLUTE_MIN = 5
JP_IDEAL_MIN = 15
JP_IDEAL_MAX = 22
JP_ABSOLUTE_MIN = 9
JP_ABSOLUTE_MAX = 30


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


def _normalize_punctuation(text, language):
    value = " ".join(str(text or "").strip().split())
    if not value:
        return ""
    if language == "ja":
        return value if value.endswith(("。", "！", "？")) else value + "。"
    return value if value.endswith((".", "!", "?")) else value + "."


_EN_FINITE_VERBS = {
    "is","are","was","were","has","have","had","shows","show","remains","remain","appears","appear",
    "walks","walk","approaches","approach","enters","enter","exits","exit","opens","open","closes","close",
    "carries","carry","pulls","pull","holds","hold","lifts","lift","steps","step","climbs","climb",
    "ascends","ascend","descends","descend","passes","pass","moves","move","stands","stand","sits","sit",
    "turns","turn","faces","face","reaches","reach","uses","use","cuts","cut","clears","clear","trims","trim",
    "removes","remove","places","place","adds","add","installs","install","stacks","stack","builds","build",
    "crosses","cross","continues","continue","leads","lead","extends","extend","contains","contain","includes","include",
    "surrounds","surround","covers","cover","indicates","indicate","describes","describe","reveals","reveal",
    "looks","look","sweeps","sweep","travels","travel","follows","follow","heads","head","leaves","leave"
}
_EN_BAD_STARTS = {
    "with","then","and","but","which","because","while","although","though","unless","as","surrounded"
}
_EN_GERUND_STARTS = {
    "approaching","walking","moving","showing","revealing","carrying","holding","placing","adding","cutting",
    "building","stacking","opening","closing","entering","leaving","standing","sitting","kneeling","arranging",
    "cleaning","removing","installing","crossing","following","trimming","clearing","pulling","lifting"
}
_EN_BAD_ENDS = {
    "than","what","which","who","whom","whose","because","while","although","though","until","if","and","but","or",
    "to","of","with","for","from","is","are","was","were","be","been","being","how","a","an","the",
    "wooden","stone","brick","metal","glass","surrounded","toward","through","along","beside"
}


def _fragment_issue(text, language):
    value = " ".join(str(text or "").strip().split())
    if not value:
        return "empty"
    if language == "ja":
        compact = re.sub(r"\s+", "", value).rstrip("。！？")
        if compact.endswith(("けど", "ので", "から", "ながら", "そして", "でも")):
            return "dangling Japanese connective"
        return ""

    plain = value.lstrip('"\'“‘(')
    if plain and plain[0].isalpha() and plain[0].islower():
        return "starts lowercase like a carried-over clause"
    words = _words(value)
    if not words:
        return "empty"
    first, last = words[0], words[-1]
    if first in _EN_BAD_STARTS:
        return "starts with dependent/linking phrase"
    if first in _EN_GERUND_STARTS:
        return "starts like a visual-log fragment"
    if last in _EN_BAD_ENDS:
        return "ends with dangling/incomplete word"
    # Captions should stand alone. Noun phrases leaked from vision logs usually
    # have no finite visual verb at all.
    if not any(w in _EN_FINITE_VERBS for w in words):
        return "no finite visual verb"
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


def _length_class(text, language):
    n = _units(text, language)
    if language == "ja":
        if JP_IDEAL_MIN <= n <= JP_IDEAL_MAX:
            return "ideal"
        if JP_ABSOLUTE_MIN <= n <= JP_ABSOLUTE_MAX:
            return "acceptable"
        return "hard"
    if US_IDEAL_MIN <= n <= US_IDEAL_MAX:
        return "ideal"
    if US_NORMAL_MIN <= n <= US_NORMAL_MAX:
        return "normal"
    if US_ABSOLUTE_MIN <= n <= US_EXTENDED_MAX:
        return "extended"
    if US_ABSOLUTE_MIN <= n <= US_ABSOLUTE_MAX:
        return "long_repairable"
    return "hard"


def _candidate_issue(text, language, history, check_duplicate=True):
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
    if _length_class(value, language) == "hard":
        return f"hard_length={_units(value, language)}"
    if check_duplicate:
        key = _clean_key(value)
        if key and any(key == _clean_key(old) for old in history):
            return "exact duplicate"
    return ""


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


def _evidence_for(observations, a, b):
    nearby = [o for o in observations if float(o.get("start", 0)) < b and float(o.get("end", 0)) > a]
    if not nearby and observations:
        center = (a + b) / 2
        nearby = [min(observations, key=lambda o: abs((float(o.get("start", 0))+float(o.get("end", 0)))/2-center))]
    return [{
        "start": round(float(o.get("start", 0)), 2),
        "end": round(float(o.get("end", 0)), 2),
        "description": str(o.get("description", ""))[:900],
        "uncertain": str(o.get("uncertain", ""))[:220],
        "mood": str(o.get("mood", "action")),
    } for o in nearby]


def _dialogue_for(transcript, a, b, enabled):
    if not enabled:
        return []
    rows = []
    for seg in transcript or []:
        if float(seg.get("start", 0)) < b and float(seg.get("end", 0)) > a:
            rows.append({"start": round(float(seg.get("start", 0)), 2), "end": round(float(seg.get("end", 0)), 2),
                         "text": str(seg.get("text", ""))[:280]})
    return rows[:4]


def _writer_rules(language):
    if language == "ja":
        return (
            "映像に忠実で情報量のある日本語SRTを書く。後で別のWriterが書き直せるよう人物・動作・物・状態・変化を残す。"
            "目的、感情、背景、見えない結果は推測しない。自然な一文を優先し、文字数のために文を壊さない。"
        )
    return (
        "Write factual American English visual-narrative captions for later rewriting. Preserve useful visible details: subject, action, object/material, "
        "location, visible condition and visible change when supported. Do not invent motive, thoughts, emotion, identity, backstory, danger, hidden purpose, "
        "elapsed time or off-screen outcomes. Each caption must be a natural standalone sentence. 8-12 words is ideal, 7-14 is normal, and 15-18 is allowed "
        "when the extra visible detail is useful. Never damage a good sentence just to hit a word count. Never output raw vision-log fragments, generic filler, jokes, "
        "hooks, catchphrases, slang or stage directions. If the same action truly continues, semantic similarity is allowed."
    )


def _deterministic_evidence_sentence(evidence, language):
    """Last-resort bounded fallback. It never returns a raw comma fragment."""
    descriptions = [str(x.get("description", "")).strip() for x in evidence if str(x.get("description", "")).strip()]
    if not descriptions:
        return "映像では人物の動きが続いています。" if language == "ja" else "The scene shows the visible action continuing in this area."
    if language == "ja":
        for desc in descriptions:
            for part in re.split(r"[。！？]+", desc):
                part = part.strip()
                if part and not _fragment_issue(part + "。", language):
                    return _normalize_punctuation(part[:60], language)
        return _normalize_punctuation(re.sub(r"\s+", "", descriptions[0])[:30], language)

    # Prefer a complete real sentence; then a complete first clause before a comma.
    for desc in descriptions:
        for part in re.split(r"[.!?]+", desc):
            part = part.strip(" ,.-")
            if not part:
                continue
            candidate = _normalize_punctuation(part, language)
            if not _fragment_issue(candidate, language) and _units(candidate, language) <= US_ABSOLUTE_MAX:
                return candidate
            first_clause = part.split(",", 1)[0].strip(" ,.-")
            candidate = _normalize_punctuation(first_clause, language)
            if first_clause and not _fragment_issue(candidate, language) and _units(candidate, language) <= US_ABSOLUTE_MAX:
                return candidate

    base = re.split(r"[.!?]+", descriptions[0])[0].strip(" ,.-")
    low = base.lower()
    if low.startswith("with "):
        return _normalize_punctuation("The scene shows " + base[5:], language)
    if low.startswith("then "):
        rest = base[5:].strip()
        if rest and _words(rest) and _words(rest)[0] in {"exits","enters","walks","moves","approaches","crosses","opens","closes"}:
            return _normalize_punctuation("The person " + rest, language)
    if low.startswith("surrounded by "):
        return _normalize_punctuation("The area is " + base, language)
    if _words(base) and _words(base)[0] in _EN_GERUND_STARTS:
        return _normalize_punctuation("The scene shows the action of " + base.lower(), language)
    # Noun phrase fallback: keep the evidence intact instead of chopping it.
    return _normalize_punctuation("The scene shows " + base, language)


def write_visual_srt_script_556(pipeline, observations, story, duration, language, transcript=None, dialogue_mode=False):
    transcript = transcript or []
    slots = _slots(float(duration), language)
    total = len(slots)
    meta = [{"slot": i+1, "start": a, "end": b, "evidence": _evidence_for(observations, a, b),
             "dialogue_context": _dialogue_for(transcript, a, b, dialogue_mode)} for i, (a, b) in enumerate(slots)]
    result = [None] * total
    repairs, fallbacks, warnings, preserved = [], [], [], []
    batch_size = 8 if getattr(pipeline.r, "writer_model", "").startswith("qwen3:8b") else 6

    def structural_validator(expected):
        expected = list(expected)
        def validate(obj):
            caps = obj.get("captions")
            if not isinstance(caps, list) or len(caps) != len(expected):
                raise ValueError("caption count mismatch")
            if [int(x.get("slot", 0)) for x in caps] != expected:
                raise ValueError("caption slots/order mismatch")
        return validate

    def batch_write(items, previous_lines):
        schema = {"type":"object","properties":{"captions":{"type":"array","minItems":len(items),"maxItems":len(items),
                  "items":{"type":"object","properties":{"slot":{"type":"integer"},"text":{"type":"string"}},
                  "required":["slot","text"],"additionalProperties":False}}},"required":["captions"],"additionalProperties":False}
        payload = [{"slot":x["slot"],"time":[round(x["start"],2),round(x["end"],2)],"evidence":x["evidence"],
                    "dialogue_context":x["dialogue_context"]} for x in items]
        context = {"global_setup":str(story.get("setup", ""))[:900],"global_ending":str(story.get("ending", ""))[:900],
                   "previous_captions":previous_lines[-4:],"slots":payload}
        prompt = _writer_rules(language) + "\nWrite one standalone caption for every slot, in order, using ONLY that slot's evidence. Dialogue is context only, never transcript. Return JSON only.\n" + json.dumps(context, ensure_ascii=False)
        first, last = items[0]["slot"], items[-1]["slot"]
        return pipeline.r.chat("You are a precise factual visual subtitle writer. Return JSON only.", prompt,
            tokens=max(600,110*len(items)), schema=schema, validator=structural_validator([x["slot"] for x in items]),
            context=f"Visual Narrative 5.5.6 {first}-{last}", diagnostics=pipeline.work/"AI"/f"visual_narrative_556_{language}_{first}_{last}",
            num_ctx=4096, temperature=.18).get("captions", [])

    def repair_one(item, current, previous_lines, reason, attempt):
        schema = {"type":"object","properties":{"slot":{"type":"integer"},"text":{"type":"string"}},
                  "required":["slot","text"],"additionalProperties":False}
        ctx = {"slot":item["slot"],"time":[round(item["start"],2),round(item["end"],2)],"current":current,"problem":reason,
               "evidence":item["evidence"],"dialogue_context":item["dialogue_context"],"previous_captions":previous_lines[-4:]}
        prompt = _writer_rules(language) + "\nRepair this ONE caption from its evidence. Completeness and factual detail outrank word count. Return JSON only.\n" + json.dumps(ctx, ensure_ascii=False)
        def validator(obj):
            if int(obj.get("slot",0)) != item["slot"] or not str(obj.get("text","")).strip():
                raise ValueError("invalid repaired caption")
        return pipeline.r.chat("You repair one factual visual caption. Return JSON only.", prompt, tokens=260, schema=schema,
            validator=validator, context=f"Visual Repair 5.5.6 {item['slot']} attempt {attempt}",
            diagnostics=pipeline.work/"AI"/f"visual_repair_556_{language}_{item['slot']}_{attempt}", num_ctx=4096,
            temperature=.14 + .04*attempt).get("text", "")

    for start in range(0, total, batch_size):
        items = meta[start:start+batch_size]
        previous_lines = [r["text"] for r in result[:start] if r]
        try:
            caps = batch_write(items, previous_lines)
            by_slot = {int(x.get("slot",0)):str(x.get("text","")).strip() for x in caps}
        except Exception as exc:
            warnings.append({"stage":"batch","slots":[items[0]["slot"],items[-1]["slot"]],"error":str(exc)})
            by_slot = {}

        for item in items:
            slot = item["slot"]
            previous = [r["text"] for r in result[:slot-1] if r]
            candidate = _normalize_punctuation(by_slot.get(slot, ""), language)
            issue = _candidate_issue(candidate, language, previous, check_duplicate=False) if candidate else "missing batch caption"
            length_class = _length_class(candidate, language) if candidate else "hard"

            # A complete factual 7-18 word sentence is accepted immediately. Only
            # 19-24 words are gently compressed; word count alone never triggers fallback.
            needs_repair = bool(issue) or length_class == "long_repairable"
            if needs_repair:
                reason = issue or f"long_but_repairable={_units(candidate, language)}"
                repaired = ""
                for attempt in (1,2,3):
                    try:
                        trial = _normalize_punctuation(repair_one(item, candidate, previous, reason, attempt), language)
                        trial_issue = _candidate_issue(trial, language, previous, check_duplicate=False)
                        if not trial_issue and _length_class(trial, language) != "hard":
                            repaired = trial
                            repairs.append({"caption":slot,"reason":reason,"new_text":trial,"attempt":attempt,
                                            "length_class":_length_class(trial, language)})
                            break
                        reason = trial_issue or f"length={_units(trial, language)}"
                    except Exception as exc:
                        reason = str(exc)
                if repaired:
                    candidate = repaired
                elif candidate and not _candidate_issue(candidate, language, previous, check_duplicate=False) and _units(candidate, language) <= US_ABSOLUTE_MAX:
                    preserved.append({"caption":slot,"reason":"repair failed; preserved complete factual candidate","text":candidate})
                else:
                    candidate = _deterministic_evidence_sentence(item["evidence"], language)
                    fallbacks.append({"caption":slot,"reason":reason,"text":candidate})

            # Exact duplicate: best-effort one-caption rewrite. If rewrite fails,
            # retain the accurate duplicate and flag QA rather than inventing content.
            if any(_clean_key(candidate) == _clean_key(old) for old in previous if _clean_key(old)):
                try:
                    trial = _normalize_punctuation(repair_one(item, candidate, previous, "exact duplicate", 4), language)
                    if not _candidate_issue(trial, language, previous, check_duplicate=True):
                        candidate = trial
                        repairs.append({"caption":slot,"reason":"exact duplicate","new_text":trial,"attempt":4})
                except Exception as exc:
                    warnings.append({"caption":slot,"stage":"dedupe","error":str(exc)})

            result[slot-1] = {"start":item["start"],"end":item["end"],"text":candidate,
                              "mood":item["evidence"][0].get("mood","action") if item["evidence"] else "action",
                              "role":"visual_narrative"}
        _write_json(pipeline.out/"Script_Timeline.json", result)

    ideal, normal, extended, long_rows, hard_rows = [], [], [], [], []
    fragments, duplicates, speculation, generic = [], [], [], []
    history = []
    for i,row in enumerate(result,1):
        cls = _length_class(row["text"], language)
        rec = {"caption":i,"units":_units(row["text"],language),"text":row["text"]}
        {"ideal":ideal,"normal":normal,"extended":extended,"long_repairable":long_rows,"hard":hard_rows}.get(cls, long_rows).append(rec)
        frag = _fragment_issue(row["text"], language)
        if frag: fragments.append({"caption":i,"issue":frag,"text":row["text"]})
        spec = _speculation_issue(row["text"], language)
        if spec: speculation.append({"caption":i,"issue":spec,"text":row["text"]})
        gen = _generic_issue(row["text"], language)
        if gen: generic.append({"caption":i,"issue":gen,"text":row["text"]})
        key = _clean_key(row["text"])
        for j,old in enumerate(history,1):
            if key and key == _clean_key(old):
                duplicates.append({"caption":i,"first_caption":j,"text":row["text"]}); break
        history.append(row["text"])

    visual_context = [{"slot":item["slot"],"start":item["start"],"end":item["end"],"final_caption":row["text"],
                       "evidence":item["evidence"],"dialogue_context_used_for_understanding_only":bool(item["dialogue_context"])}
                      for item,row in zip(meta,result)]
    _write_json(pipeline.out/"Visual_Context.json", {"version":VERSION,"purpose":"Detailed visual evidence for later ChatGPT rewriting; not production subtitles.","slots":visual_context})
    qa = {
        "version":VERSION,
        "architecture":"Visual Brain -> evidence map -> factual writer -> completeness/grounding repair -> light length guidance -> best-effort exact dedupe -> SRT",
        "caption_count":total,
        "us_length_policy":"8-12 ideal; 7-14 normal; 15-18 allowed for useful visible detail; 19-24 repairable; completeness outranks count" if language=="en" else None,
        "ideal_count":len(ideal),"normal_count":len(normal),"extended_count":len(extended),"long_repairable_remaining":long_rows,"hard_length_remaining":hard_rows,
        "average_units":round(sum(_units(r["text"],language) for r in result)/max(1,total),2),
        "fragment_captions":fragments,"exact_duplicates":duplicates,"speculation_warnings":speculation,"generic_filler_warnings":generic,
        "repairs":repairs,"preserved_complete_candidates":preserved,"emergency_fallbacks":fallbacks,"batch_warnings":warnings,
        "requires_review":bool(fragments or speculation or generic or hard_rows or fallbacks or duplicates),
        "policy":"Accuracy, completeness and rewriteable visual detail outrank word count. One caption never aborts the job. Exact duplicate repair is best-effort."
    }
    _write_json(pipeline.out/"Visual_SRT_QA.json", qa)
    return result
