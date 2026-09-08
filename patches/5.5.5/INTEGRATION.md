# Comedy Host Studio 5.5.5 — Visual-Grounded SRT

## Baseline

Use **only** the clean 5.5.4 source supplied by the user (`engine.py` version `1.1.0-beta5.5.4-clean-installer`).

Do not use or merge any 5.5.3f / 5.5.3g / 5.5.3h source, PowerShell injection patch, or VideoScriptAI / 6.0.x code.

## Product goal

The app is no longer responsible for producing the final viral/comedy script in SRT-only mode.

SRT-only now creates a **factually grounded, information-rich visual narrative** that can be rewritten later in ChatGPT Work/Projects.

US caption policy:

- Normal target: **8–12 words**.
- Preferred: **9–11 words**.
- 10 words is a midpoint, **not a hard rule**.
- Preserve concrete visual information over exact word count.
- No forced hook, joke, slang, catchphrase, payoff, or trend phrase.
- No raw Visual Brain paragraph may be exported as a caption.
- Same-action semantic similarity is allowed when the video genuinely repeats the action.
- Exact duplicate sentences are repaired.

Timeline stays:

- US active caption target: ~4.081 s.
- Inter-caption gap: 0.10 s.
- Full video coverage from 00:00 to exact end.

## New module

Add `visual_srt_555.py` beside `engine.py` in the installed application.

It implements:

`write_visual_srt_script_555(pipeline, observations, story, duration, language, transcript=None, dialogue_mode=False)`

The module:

1. Maps each fixed timeline slot to overlapping Visual Brain evidence.
2. Sends compact batches to Qwen3 Writer.
3. Validates only the batch structure globally.
4. Validates/retries each caption independently.
5. Never discards six good captions because one slot is imperfect.
6. Uses a per-slot Writer recovery before any deterministic fallback.
7. Never exports the full raw visual description as fallback.
8. Treats 8–12 words as a target band, not an exact-10 lock.
9. Repairs exact duplicates only; same-action similarity is QA information, not a failure.
10. Writes `Visual_Context.json` for the later ChatGPT rewrite workflow.
11. Writes `Visual_SRT_QA.json` and never crashes the entire SRT because one recoverable caption needs review.

## Clean source integration

### 1. Version

Change:

```python
VERSION = "1.1.0-beta5.5.4-clean-installer"
```

to:

```python
VERSION = "1.1.0-beta5.5.5-visual-grounded"
```

### 2. Import the new SRT module

Near the normal imports in `engine.py` add:

```python
from visual_srt_555 import write_visual_srt_script_555
```

This is a normal source module import, not runtime code injection.

### 3. SRT-only execution path

In `Pipeline.execute()`, keep Visual Brain and `self.story(observations)` unchanged.

Replace the current SRT-only block that calls `self.creative_plan(...)` followed by the old `self.write_srt_script(...)` with:

```python
if task == "srt_only":
    reserved = []
    creative_plan = {
        "version": "5.5.5-visual-grounded",
        "premise": str(story.get("setup", ""))[:900],
        "story_arc": "Visual evidence timeline preserved from beginning to end.",
        "verified_payoff": str(story.get("ending", ""))[:900],
        "hook_promise": "",
        "topic_lane": "visual_grounded",
    }
    stage_times["narrative_plan_seconds"] = 0.0

    _t = time.monotonic()
    script = write_visual_srt_script_555(
        self,
        observations,
        story,
        duration,
        language,
        transcript=transcript,
        dialogue_mode=dialogue_mode,
    )
    stage_times["writer_editor_seconds"] = round(time.monotonic()-_t, 2)
```

Continue using the existing `Script_Timeline.json`, `direct_srt(...)`, Vietnamese translation and Performance QA code after this point.

The old GoldStyle/StoryFlow method may remain temporarily for audio mode/history, but **SRT-only must not call it**.

### 4. SRT mode catalog

Replace the installed `voice_catalog.json` with the 5.5.5 version in this patch folder so the UI accurately states the new behavior.

### 5. Do not load trend/style data in the new SRT path

`trend_us.json` and GoldStyle files may stay installed for backward compatibility, but the 5.5.5 SRT-only writer does not consume them.

This avoids the previous conflict where the writer was encouraged to use phrases such as `DIY wizard`, `secret weapon`, `Boom`, and `heavy lifting`, then Anti-Repeat punished the same phrases later.

## Files intentionally unchanged

Do not modify:

- Visual Brain Qwen3-VL 4B.
- Qwen3 8B Writer selection on RTX 2070 / 16 GB profile.
- Safe GPU Auto / `num_gpu=-1`.
- `OLLAMA_NUM_PARALLEL=1`.
- `OLLAMA_MAX_LOADED_MODELS=1`.
- Vision context 4096 on the 8 GB GPU profile.
- Analysis cache/resume.
- Full Story/Event Map retention.
- Visual-only behavior when `Giữ thoại gốc` is off.
- Dialogue-as-context-only behavior when `Giữ thoại gốc` is on.
- Vietnamese Translation feature.

## QA pass criteria before installer build

### Required functional tests

- Video 8–20 s.
- Video around 60 s.
- Video around 3–5 min.
- Repetitive construction/action video.
- Walking/exploration video.
- Renovation before/after video.
- Video without audio.
- Video with audio, `Giữ thoại gốc` off.
- Video with audio, `Giữ thoại gốc` on.
- First Writer model download.
- Rerun with model already downloaded.
- Cancellation and rerun using existing visual cache.

### SRT acceptance

- First caption starts at 00:00.
- Last caption reaches the measured video end.
- Gap is 0.10 s within current timestamp tolerance.
- Raw Visual Brain paragraph count = 0.
- Fragment count = 0 target.
- Exact duplicate count = 0 target.
- US captions 8–12 words >= 90% target.
- 7/13-word complete factual lines may survive as warnings if rewriting would remove useful information.
- No caption over 14 words without `requires_review`.
- No batch failure may discard other valid captions.
- One bad caption may never abort the whole SRT.
- `Visual_Context.json` must contain the detailed evidence for every slot.

## Regression tests

Run:

```bash
python patches/5.5.5/test_visual_srt_555.py
```

Then run `python -m py_compile` on the integrated `engine.py` and `visual_srt_555.py` before building the installer.
