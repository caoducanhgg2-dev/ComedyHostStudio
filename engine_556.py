"""Comedy Host Studio 5.5.6 bootstrap.

Clean wrapper around the preserved 5.5.4 core. SRT-only routes to the 5.5.6
information-first writer. Consecutive jobs release stale local-AI model state.
"""
from __future__ import annotations

import sys

import engine_554_core as core
import visual_srt_556 as visual
from visual_rules_556 import fragment_issue
from runtime_stability_556 import prepare_consecutive_job, mark_job_finished

VERSION = "1.1.0-beta5.5.6-visual-quality-stability"
core.VERSION = VERSION

# Centralize the corrected sentence-completeness detector. All writer/fallback/QA
# functions in visual_srt_556 resolve this global at runtime.
visual._fragment_issue = fragment_issue


def _plan(self, story, duration):
    story = story or {}
    return {
        "version": "5.5.6-visual-quality-stability",
        "premise": str(story.get("setup", ""))[:900],
        "story_arc": "Visual evidence preserved in chronological order.",
        "verified_payoff": str(story.get("ending", ""))[:900],
        "hook_promise": "", "viewer_question": "", "callback_seed": "",
        "topic_lane": "visual_grounded", "beats": [],
    }


def _writer(self, observations, story, duration, language, transcript=None, dialogue_mode=False, creative_plan=None):
    result = visual.write_visual_srt_script_556(self, observations, story, duration, language,
                                                transcript=transcript or [], dialogue_mode=bool(dialogue_mode))
    self.repeat_hard_remaining = []
    self.repeat_warnings = []
    return result


core.Pipeline.creative_plan = _plan
core.Pipeline.write_srt_script = _writer

_original_execute = core.Pipeline.execute


def _stable_execute(self):
    report = prepare_consecutive_job(self.r)
    if not report.get("skipped"):
        if report.get("remaining"):
            core.emit("warning", "5.5.6: AI model từ video trước chưa giải phóng hoàn toàn: " + ", ".join(report["remaining"]) + ". Tiếp tục với Safe GPU Auto; nếu lỗi sẽ giữ log chẩn đoán.")
        elif report.get("attempted"):
            core.emit("setup", "5.5.6: đã giải phóng model AI của video trước trước khi phân tích video tiếp theo.")
        if report.get("errors"):
            core.emit("warning", "5.5.6 runtime cleanup: " + str(report["errors"][-1])[:500])
    try:
        return _original_execute(self)
    finally:
        mark_job_finished(self.r)


core.Pipeline.execute = _stable_execute


def main():
    return core.main()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
