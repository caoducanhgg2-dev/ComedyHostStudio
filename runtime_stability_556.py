"""Consecutive-video runtime hygiene for Comedy Host Studio 5.5.6."""
from __future__ import annotations

import gc
import time


def _active_models(runtime):
    data = runtime.api("/api/ps", timeout=5) or {}
    return data.get("models", []) or []


def release_resident_models(runtime, timeout=18.0):
    """Best-effort release of Ollama models before a later video begins.

    Returns a diagnostic dict. It never touches model files or analysis cache.
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
            # Ollama unload convention: keep_alive=0 with an empty generation.
            runtime.api("/api/generate", {"model": name, "prompt": "", "stream": False, "keep_alive": 0}, timeout=30)
        except Exception as first:
            try:
                runtime.api("/api/chat", {"model": name, "messages": [], "stream": False, "keep_alive": 0}, timeout=30)
            except Exception as second:
                report["errors"].append(f"{name}: {first}; fallback: {second}")

    deadline = time.monotonic() + max(2.0, float(timeout))
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
        time.sleep(.4)

    # These are presentation/diagnostic caches, not model files.
    if hasattr(runtime, "backend_reported_models"):
        runtime.backend_reported_models.clear()
    if hasattr(runtime, "backend_info"):
        runtime.backend_info.clear()
    gc.collect()
    return report


def prepare_consecutive_job(runtime):
    """Clean resident AI state only after at least one job has already run."""
    prior = int(getattr(runtime, "_chs_job_runs", 0) or 0)
    if prior <= 0:
        return {"skipped": True, "reason": "first job keeps successful GPU preflight model", "attempted": [], "remaining": [], "errors": []}
    report = release_resident_models(runtime)
    report["skipped"] = False
    return report


def mark_job_finished(runtime):
    runtime._chs_job_runs = int(getattr(runtime, "_chs_job_runs", 0) or 0) + 1
