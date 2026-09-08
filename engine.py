"""Comedy Host Studio 5.5.5 Visual-Grounded bootstrap.

Clean file-replacement integration for a verified 5.5.4 Clean installation.
The original 5.5.4 engine is preserved as engine_554_core.py by INSTALL_5.5.5.bat.
No PowerShell source injection or stacked hotfix is used.
"""
from __future__ import annotations

import sys

import engine_554_core as core
from visual_srt_555 import write_visual_srt_script_555

VERSION = "1.1.0-beta5.5.5-visual-grounded"
core.VERSION = VERSION


def _visual_grounded_plan(self, story, duration):
    """Lightweight SRT-only context; no GoldStyle/viral planning call."""
    story = story or {}
    return {
        "version": "5.5.5-visual-grounded",
        "premise": str(story.get("setup", ""))[:900],
        "story_arc": "Visual evidence timeline preserved from beginning to end.",
        "verified_payoff": str(story.get("ending", ""))[:900],
        "hook_promise": "",
        "viewer_question": "",
        "callback_seed": "",
        "topic_lane": "visual_grounded",
        "beats": [],
    }


def _visual_grounded_writer(self, observations, story, duration, language,
                            transcript=None, dialogue_mode=False, creative_plan=None):
    """Route SRT-only generation to the factual 5.5.5 writer."""
    result = write_visual_srt_script_555(
        self,
        observations,
        story,
        duration,
        language,
        transcript=transcript or [],
        dialogue_mode=bool(dialogue_mode),
    )
    # Keep legacy export metadata benign. Visual_SRT_QA.json is the authoritative
    # quality report for 5.5.5; exact-duplicate/review flags are recorded there.
    self.repeat_hard_remaining = []
    self.repeat_warnings = []
    return result


# Pipeline.execute in the clean 5.5.4 engine invokes these methods only for
# SRT-only mode. Audio+SRT behavior therefore remains on the original engine.
core.Pipeline.creative_plan = _visual_grounded_plan
core.Pipeline.write_srt_script = _visual_grounded_writer


def main():
    return core.main()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
