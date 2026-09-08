"""Adaptive memory + speed guard for Comedy Host Studio 5.5.6.

Real log: Qwen3-VL failed with only ~1.2-1.6 GiB free physical RAM because
Ollama BatchSize=512 created a ~4.2 GiB CPU compute graph. The guard chooses the
largest safe prompt batch dynamically so the model can offload more layers to the
RTX 2070 instead of falling back to a huge CPU graph.
"""
from __future__ import annotations

import gc
import os
import time


def available_phys_gib():
    try:
        if os.name == "nt":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            st = MEMORYSTATUSEX(); st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return st.ullAvailPhys / (1024 ** 3)
        pages = os.sysconf("SC_AVPHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        return pages * size / (1024 ** 3)
    except Exception:
        return None


def _visual_batch(free, forced_low=False):
    # 64 is the fastest safe default for this 16GB/RTX2070 machine: much smaller
    # CPU graph than Ollama 512, while still feeding the GPU efficiently.
    if forced_low:
        return 24
    if free is None:
        return 64
    if free < 1.6:
        return 16
    if free < 2.5:
        return 24
    if free < 4.0:
        return 48
    return 64


def _writer_batch(free):
    # Text-only Qwen3 8B has a far smaller compute graph. Use a larger batch when
    # headroom exists for faster prompt evaluation, but never the 512 default.
    if free is None:
        return 128
    if free < 1.6:
        return 32
    if free < 2.5:
        return 64
    if free < 4.0:
        return 96
    return 128


def install_memory_guard(core):
    Runtime = core.Runtime
    original_forced = Runtime._forced_gpu_options
    original_prewarm = Runtime._prewarm_vision_gpu
    original_chat = Runtime._chat

    def guarded_forced(self):
        opts = dict(original_forced(self) or {})
        free = available_phys_gib()
        visual = bool(getattr(self, "_chs_visual_call", False) or getattr(self, "_chs_preflight", False))
        if visual:
            opts["num_batch"] = _visual_batch(free, bool(getattr(self, "_chs_force_low_batch_once", False)))
        else:
            opts["num_batch"] = _writer_batch(free)
        return opts

    def guarded_chat(self, system, prompt, images=None, tokens=1800, *, schema=None,
                     validator=None, context="", diagnostics=None, model=None,
                     num_ctx=None, temperature=None):
        previous = bool(getattr(self, "_chs_visual_call", False))
        self._chs_visual_call = bool(images)
        try:
            free = available_phys_gib()
            if images and free is not None:
                # Keep 4096 whenever possible for accuracy. Only reduce context under
                # severe pressure; this is preferable to CPU fallback or HTTP 500.
                if free < 1.6:
                    num_ctx = min(int(num_ctx or getattr(self, "vision_context", 4096)), 2560)
                elif free < 2.2:
                    num_ctx = min(int(num_ctx or getattr(self, "vision_context", 4096)), 3072)
            return original_chat(self, system, prompt, images, tokens, schema=schema,
                                 validator=validator, context=context, diagnostics=diagnostics,
                                 model=model, num_ctx=num_ctx, temperature=temperature)
        finally:
            self._chs_visual_call = previous

    def guarded_prewarm(self):
        free = available_phys_gib()
        self._chs_preflight = True
        if free is not None and free < 2.5:
            core.emit("setup", f"5.5.6 Memory Guard: RAM trống {free:.1f} GB; tự giảm Visual batch để vẫn dùng RTX.")
        try:
            try:
                return original_prewarm(self)
            except RuntimeError as exc:
                text = str(exc).lower()
                if "more system memory" not in text and "model requires more system memory" not in text:
                    raise
                # Retry exactly once with a small batch. Do not leave low mode sticky:
                # later calls may safely return to a faster batch when RAM recovers.
                self._chs_force_low_batch_once = True
                old_ctx = int(getattr(self, "vision_context", 4096))
                self.vision_context = min(old_ctx, 3072)
                gc.collect()
                time.sleep(.25)
                free2 = available_phys_gib()
                suffix = f" ({free2:.1f} GB RAM trống)" if free2 is not None else ""
                core.emit("setup", "5.5.6 Memory Guard: preflight thiếu RAM; thử lại batch nhỏ + context 3072" + suffix + "…")
                try:
                    return original_prewarm(self)
                finally:
                    self._chs_force_low_batch_once = False
                    # Restore normal context after the emergency preflight. Individual
                    # vision calls still reduce context dynamically only if RAM is low.
                    self.vision_context = old_ctx
        finally:
            self._chs_preflight = False

    Runtime._forced_gpu_options = guarded_forced
    Runtime._chat = guarded_chat
    Runtime._prewarm_vision_gpu = guarded_prewarm
    return Runtime
