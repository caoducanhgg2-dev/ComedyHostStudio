# Comedy Host Studio 5.5.6 – Visual Quality + Consecutive-Run Stability

Release blockers discovered from the real 5.5.5 output:

- Do not repair a good factual sentence merely because it is 13–18 words.
- Ideal US range remains 8–12 words, but 7–14 is normal and 15–18 is allowed when the visible detail is useful.
- No raw clause trimming as emergency fallback.
- Detect real sentence fragments and incomplete endings such as `with ...`, `then ...`, `surrounded ...`, `... a wooden.`, `... path surrounded.`
- Exact duplicate repair is best-effort and never discards a correct caption or aborts the job.
- Emergency fallback is only for missing/invalid/hallucinated text, not ordinary word-count deviation.
- Keep Visual_Context.json as the rich evidence handoff for later ChatGPT rewriting.

Consecutive-run blocker from user screenshot:

- A later video in the same app session must not inherit a stale Writer/Ollama/GPU model state from the previous video.
- Before a new video starts, release any resident local-AI models and wait briefly for Ollama to report a clean model set.
- Reset per-job backend reporting state and collect Python garbage; preserve shared models/cache/runtime files.
- Failure to release a resident model is a warning/retry condition, not silent CPU fallback.

No 5.5.3f/g/h or VideoScriptAI source is used.
