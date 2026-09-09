"""Comedy Host Studio 5.5.7 - Visual Continuity + Fast Stability.

Clean wrapper around the preserved 5.5.4 core. SRT-only routes to the 5.5.7
continuity writer. RAM-safe GPU batching, Vision->Writer VRAM handoff, and
consecutive-video cleanup from 5.5.6 are preserved.
"""
from __future__ import annotations

import json
import sys

import engine_554_core as core
import visual_srt_557 as visual
from visual_rules_556 import fragment_issue
from runtime_stability_556 import prepare_consecutive_job, prepare_writer_phase, finish_job
from memory_guard_556 import install_memory_guard

VERSION = "1.1.0-beta5.5.7-visual-continuity-fast"
core.VERSION = VERSION

install_memory_guard(core)


def _plan(self, story, duration):
    story = story or {}
    return {
        "version": "5.5.7-visual-continuity-fast",
        "premise": str(story.get("setup", ""))[:900],
        "story_arc": "Visual evidence preserved in chronological order.",
        "verified_payoff": str(story.get("ending", ""))[:900],
        "hook_promise": "", "viewer_question": "", "callback_seed": "",
        "topic_lane": "visual_grounded", "beats": [],
    }


def _writer(self, observations, story, duration, language, transcript=None, dialogue_mode=False, creative_plan=None):
    handoff = prepare_writer_phase(self.r)
    if handoff.get("attempted") and not handoff.get("remaining"):
        core.emit("setup", "5.5.7 Fast: đã nhường RAM/VRAM từ Visual Brain sang Writer.")
    result = visual.write_visual_srt_script_557(
        self, observations, story, duration, language,
        transcript=transcript or [], dialogue_mode=bool(dialogue_mode)
    )
    self.repeat_hard_remaining = []
    self.repeat_warnings = []
    return result


def _fast_vi_translation(self, script, source_language, creative_plan=None):
    """Fast Vietnamese review translation of final factual captions."""
    rows = []
    batch_size = 24
    label = "JP" if source_language == "ja" else "EN"
    glossary = {
        "bobber/bobbers": "phao câu", "buoy": "phao", "lure": "mồi giả",
        "mesh": "lưới/lưới thép tùy hình ảnh", "frame": "khung",
        "setup": "cách bố trí/cấu trúc tùy ngữ cảnh", "build": "công trình/quá trình xây dựng tùy ngữ cảnh",
        "ice hole": "lỗ câu trên băng", "line": "dây câu khi ngữ cảnh là câu cá",
        "hook/hooks": "lưỡi câu", "grate": "vỉ/lưới kim loại tùy ngữ cảnh"
    }

    def translate_batch(batch, start):
        count = len(batch)
        schema = {"type":"object","properties":{"items":{"type":"array","minItems":count,"maxItems":count,
                  "items":{"type":"object","properties":{"slot":{"type":"integer"},"vi":{"type":"string"}},
                  "required":["slot","vi"],"additionalProperties":False}}},"required":["items"],"additionalProperties":False}
        payload = [{"slot":start+i+1,"text":x["text"]} for i,x in enumerate(batch)]
        prompt = (
            "Dịch các caption sau sang tiếng Việt tự nhiên để kiểm tra nội dung hình ảnh. Giữ đúng ý và đúng slot; "
            "không thêm sự kiện, không viết viral/comedy, không dịch từng chữ. Không để sót ký tự Trung/Nhật/Cyrillic trong VI. "
            "Dùng glossary khi phù hợp. Chỉ trả JSON.\n" +
            json.dumps({"source_language":"Japanese" if source_language=="ja" else "US English",
                        "glossary":glossary,"captions":payload}, ensure_ascii=False)
        )
        def validator(obj):
            got = obj.get("items")
            if not isinstance(got,list) or len(got)!=count:
                raise ValueError("translation count mismatch")
            for expected,item in zip(range(start+1,start+count+1),got):
                if int(item.get("slot",0)) != expected:
                    raise ValueError("translation slot mismatch")
                issue = core.vi_translation_issue(item.get("vi",""))
                if issue:
                    raise ValueError(f"VI slot {expected}: {issue}")
        return self.r.chat(
            "Bạn dịch phụ đề video sang tiếng Việt tự nhiên. Chỉ trả JSON.", prompt,
            tokens=max(900,70*count), schema=schema, validator=validator,
            context=f"Vietnamese fast review {start+1}-{start+count}",
            diagnostics=self.work/"AI"/f"vi_fast_{start:04d}", num_ctx=4096, temperature=.18
        )

    for start in range(0,len(script),batch_size):
        batch = script[start:start+batch_size]
        try:
            obj = translate_batch(batch,start)
            for i,(src,tr) in enumerate(zip(batch,obj.get("items",[])),start+1):
                rows.append((i,src,str(tr.get("vi","")).strip()))
        except Exception as exc:
            core.emit("warning", f"Dịch Việt nhanh {start+1}-{start+len(batch)} chưa hoàn tất; chia nhỏ: {exc}")
            for sub in range(start,start+len(batch),6):
                sb = script[sub:min(start+len(batch),sub+6)]
                try:
                    obj = translate_batch(sb,sub)
                    for i,(src,tr) in enumerate(zip(sb,obj.get("items",[])),sub+1):
                        rows.append((i,src,str(tr.get("vi","")).strip()))
                except Exception as subexc:
                    core.emit("warning", f"Dịch Việt slot {sub+1}-{sub+len(sb)} chưa hoàn tất: {subexc}")
                    rows.extend((i,src,"[Không dịch được tự động]") for i,src in enumerate(sb,sub+1))

    rows.sort(key=lambda x:x[0])
    issues = []
    for i,src,vi in rows:
        issue = core.vi_translation_issue(vi) if not vi.startswith("[") else "translation unavailable"
        if issue:
            issues.append({"caption":i,"issue":issue,"source":src.get("text",""),"vi":vi})

    def ts(sec):
        m=int(sec//60); ss=sec-m*60
        return f"{m:02d}:{ss:05.2f}"

    out_lines=["BẢN DỊCH TIẾNG VIỆT - KIỂM TRA HÌNH ẢNH","",f"Nguồn: {label}",""]
    for i,src,vi in rows:
        out_lines += [f"{i}. [{ts(src['start'])}–{ts(src['end'])}]",f"{label}: {src['text']}",f"VI: {vi}",""]
    (self.out/"Vietnamese_Translation.txt").write_text("\n".join(out_lines),encoding="utf-8-sig")
    core.write_json(self.out/"Vietnamese_QA.json",{
        "version":"5.5.7-fast","source_language":source_language,"captions":len(rows),
        "issues":issues,"issue_count":len(issues),"glossary":glossary,
        "policy":"Fast meaning-first Vietnamese review translation of final Visual Continuity SRT."
    })
    return len(rows)


core.Pipeline.creative_plan = _plan
core.Pipeline.write_srt_script = _writer
core.Pipeline.write_vietnamese_translation = _fast_vi_translation

_original_execute = core.Pipeline.execute


def _stable_execute(self):
    report = prepare_consecutive_job(self.r)
    if not report.get("skipped"):
        if report.get("remaining"):
            core.emit("warning", "5.5.7: model video trước chưa giải phóng hoàn toàn: " + ", ".join(report["remaining"]) + ".")
        elif report.get("attempted"):
            core.emit("setup", "5.5.7 Fast: GPU/RAM đã sạch trước video tiếp theo.")
    try:
        return _original_execute(self)
    finally:
        finish_job(self.r)


core.Pipeline.execute = _stable_execute


def main():
    return core.main()


if __name__ == "__main__":
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr,"reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
