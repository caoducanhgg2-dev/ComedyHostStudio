from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("memory_guard_556", ROOT / "memory_guard_556.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_batch_policy_prefers_speed_when_ram_is_healthy():
    assert M._visual_batch(8.0) == 64
    assert M._writer_batch(8.0) == 128


def test_batch_policy_scales_down_before_oom():
    assert M._visual_batch(3.2) == 48
    assert M._visual_batch(2.0) == 24
    assert M._visual_batch(1.3) == 16
    assert M._writer_batch(3.2) == 96
    assert M._writer_batch(2.0) == 64
    assert M._writer_batch(1.3) == 32


def test_emergency_retry_batch_is_smallest_safe_mode():
    assert M._visual_batch(8.0, forced_low=True) == 24


class DummyCore:
    emitted=[]
    @staticmethod
    def emit(kind,text): DummyCore.emitted.append((kind,text))
    class Runtime:
        def __init__(self):
            self.force_gpu_offload=True
            self.hardware={"cpu_logical_threads":12}
            self.vision_context=4096
            self._chs_visual_call=False
            self._chs_preflight=False
            self.prewarms=0
        def _forced_gpu_options(self):
            return {"num_gpu":-1,"main_gpu":0,"num_thread":6}
        def _prewarm_vision_gpu(self):
            self.prewarms+=1
            return "ok"
        def _chat(self,system,prompt,images=None,tokens=1800,*,schema=None,validator=None,context="",diagnostics=None,model=None,num_ctx=None,temperature=None):
            return {"num_ctx":num_ctx,"options":self._forced_gpu_options(),"images":bool(images)}


def test_low_ram_chat_reduces_context_and_batch():
    old=M.available_phys_gib
    M.available_phys_gib=lambda:1.3
    try:
        class C(DummyCore):
            class Runtime(DummyCore.Runtime): pass
        M.install_memory_guard(C)
        r=C.Runtime()
        out=r._chat("s","p",images=["x"],num_ctx=4096)
        assert out["num_ctx"] == 2560
        assert out["options"]["num_batch"] == 16
        assert out["options"]["num_gpu"] == -1
    finally:
        M.available_phys_gib=old


if __name__ == "__main__":
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test(); print("PASS",test.__name__)
    print(f"{len(tests)}/{len(tests)} tests passed")
