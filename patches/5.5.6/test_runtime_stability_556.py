from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("runtime_stability_556", ROOT / "runtime_stability_556.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class FakeRuntime:
    def __init__(self):
        self.models = ["qwen3:8b-q4_K_M"]
        self.calls = []
        self.backend_reported_models = {"qwen3:8b-q4_K_M"}
        self.backend_info = {"qwen3:8b-q4_K_M": {"size_vram": 1}}
        self._chs_job_runs = 1

    def api(self, route, payload=None, timeout=0):
        self.calls.append((route, payload))
        if route == "/api/ps":
            return {"models": [{"name": x} for x in self.models]}
        if route in {"/api/generate", "/api/chat"}:
            if payload and payload.get("keep_alive") == 0:
                name = payload.get("model")
                self.models = [x for x in self.models if x != name]
            return {"done": True}
        raise AssertionError(route)


def test_first_job_skips_cleanup():
    r = FakeRuntime(); r._chs_job_runs = 0
    report = M.prepare_consecutive_job(r)
    assert report["skipped"] is True
    assert not r.calls


def test_second_job_unloads_resident_writer():
    r = FakeRuntime()
    report = M.prepare_consecutive_job(r)
    assert report["skipped"] is False
    assert report["attempted"] == ["qwen3:8b-q4_K_M"]
    assert report["remaining"] == []
    assert any(route == "/api/generate" and payload.get("keep_alive") == 0 for route,payload in r.calls if payload)
    assert r.backend_reported_models == set()
    assert r.backend_info == {}


def test_job_counter_advances_after_failure_or_success():
    r = FakeRuntime(); r._chs_job_runs = 0
    M.mark_job_finished(r); M.mark_job_finished(r)
    assert r._chs_job_runs == 2


if __name__ == "__main__":
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test(); print("PASS", test.__name__)
    print(f"{len(tests)}/{len(tests)} tests passed")
