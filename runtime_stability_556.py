"""Fast consecutive-video/runtime hygiene for Comedy Host Studio 5.5.6."""
from __future__ import annotations

import gc
import time


def _active_models(runtime):
    data = runtime.api("/api/ps", timeout=4) or {}
    return data.get("models", []) or []


def release_resident_models(runtime, timeout=8.0):
    """Release resident Ollama models without restarting the local server.

    This keeps the server warm (fast next request) but frees model RAM/VRAM. It
    never deletes model files, analysis cache, or previous results.
    """
    report = {"attempted": [], "remaining": [], "errors": []}
    try:
        active = _active_models(runtime)
    except Exception as exc:
        report["errors"].append("ps-before: " + str(exc))
        return report

    for item in active:
        name = item.get("name") or item.get("model")
        if not name:
            continue
        report["attempted"].append(name)
        try:
            runtime.api("/api/generate", {"model": name, "prompt": "", "stream": False, "keep_alive": 0}, timeout=20)
        except Exception as first:
            try:
                runtime.api("/api/chat", {"model": name, "messages": [], "stream": False, "keep_alive": 0}, timeout=20)
            except Exception as second:
                report["errors"].append(f"{name}: {first}; fallback: {second}")

    deadline = time.monotonic() + max(1.5, float(timeout))
    while time.monotonic() < deadline:
        try:
            remaining = _active_models(runtime)
        except Exception as exc:
            report["errors"].append("ps-after: " + str(exc))
            break
        if not remaining:
            report["remaining"] = []
            break
        report["remaining"] = [m.get("name") or m.get("model") or "?" for m in remaining]
        time.sleep(.15)

    if hasattr(runtime, "backend_reported_models"):
        runtime.backend_reported_models.clear()
    if hasattr(runtime, "backend_info"):
        runtime.backend_info.clear()
    gc.collect()
    return report


def prepare_writer_phase(runtime):
    """Unload Visual Brain before Qwen3 Writer loads; avoids scheduler eviction/OOM."""
    return release_resident_models(runtime, timeout=6.0)


def prepare_consecutive_job(runtime):
    """Clean resident AI state only after at least one job has already run."""
    prior = int(getattr(runtime, "_chs_job_runs", 0) or 0)
    if prior <= 0:
        return {"skipped": True, "reason": "first job keeps successful GPU preflight model", "attempted": [], "remaining": [], "errors": []}
    report = release_resident_models(runtime, timeout=6.0)
    report["skipped"] = False
    return report


def finish_job(runtime):
    """Free the final Writer immediately so Windows RAM recovers before next video."""
    report = release_resident_models(runtime, timeout=5.0)
    runtime._chs_job_runs = int(getattr(runtime, "_chs_job_runs", 0) or 0) + 1
    return report


def mark_job_finished(runtime):
    # Compatibility for older tests/callers.
    runtime._chs_job_runs = int(getattr(runtime, "_chs_job_runs", 0) or 0) + 1
