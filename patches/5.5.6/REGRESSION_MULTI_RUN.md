# 5.5.6 regression: consecutive video runs

This regression was added after a real user run showed that a later video could surface an old runtime failure after a previous video had completed.

Mandatory release scenarios:

1. Launch app -> process video A -> completion -> process video B without restarting Windows.
2. Process video A -> completion -> wait 2 seconds -> process video B.
3. Process video A -> cancel during writer -> process video B.
4. Process video A -> writer/translation warning -> process video B.
5. Run three videos sequentially in one app session.
6. Verify old Work directory cleanup does not delete shared runtime/source files.
7. Verify local Ollama child/model state is fully reusable/restarted and no stale lock/port/process blocks the next job.
8. Verify CUDA/VRAM model unload between Vision and Writer and between jobs does not force silent CPU fallback.
9. Verify cache keys and per-job output/work paths are unique across videos.
10. A second-job failure must preserve its Process.log and must not corrupt the installed engine or previous output.

A build is not releasable until the exact second-video scenario passes.
