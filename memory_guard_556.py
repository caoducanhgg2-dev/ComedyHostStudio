"""Adaptive memory guard for Comedy Host Studio 5.5.6.

The real user log showed Qwen3-VL failing before analysis because Windows had only
~1.2-1.6 GiB free physical RAM and Ollama's default BatchSize=512 produced a
~4.2 GiB CPU compute graph. This module lowers prompt batch size under the
16-GB profile and retries prewarm once in a more aggressive low-memory mode.
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


def install_memory_guard(core):
    Runtime = core.Runtime
    original_forced = Runtime._forced_gpu_options
    original_prewarm = Runtime._prewarm_vision_gpu
    original_chat = Runtime._chat

    def guarded_forced(self):
        opts = dict(original_forced(self) or {})
        free = available_phys_gib()
        visual = bool(getattr(self, "_chs_visual_call", False) or getattr(self, "_chs_preflight", False))
        low = bool(getattr(self, "_chs_low_memory_mode", False)) or (free is not None and free < 2.5)
        if visual:
            # Default Ollama BatchSize=512 created a ~4.2 GiB CPU graph in the
            # user's failing log. 64 is the stable 16-GB baseline; 32 is used
            # only under severe RAM pressure or after an actual prewarm failure.
            opts["num_batch"] = 32 if low else 64
        else:
            # Writer prompt evaluation can use a larger batch, but still avoid
            # the 512 default on the 16-GB workstation.
            opts["num_batch"] = 64 if low else 128
        return opts

    def guarded_chat(self, system, prompt, images=None, tokens=1800, *, schema=None,
                     validator=None, context="", diagnostics=None, model=None,
                     num_ctx=None, temperature=None):
        previous = bool(getattr(self, "_chs_visual_call", False))
        self._chs_visual_call = bool(images)
        try:
            free = available_phys_gib()
            if images and free is not None and free < 2.0:
                # Small context reduction saves KV/system headroom while keeping
                # enough room for the compact vision prompt used by this app.
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
            self._chs_low_memory_mode = True
            core.emit("setup", f"5.5.6 Memory Guard: RAM trống chỉ còn {free:.1f} GB; dùng Visual batch nhỏ để tránh HTTP 500.")
        try:
            try:
                return original_prewarm(self)
            except RuntimeError as exc:
                text = str(exc).lower()
                if "more system memory" not in text and "model requires more system memory" not in text:
                    raise
                # Actual Ollama memory-fit failure: retry once with even smaller
                # prompt batch and 3K vision context. No model files/cache deleted.
                self._chs_low_memory_mode = True
                self.vision_context = min(int(getattr(self, "vision_context", 4096)), 3072)
                gc.collect()
                time.sleep(.6)
                free2 = available_phys_gib()
                suffix = f" ({free2:.1f} GB RAM trống)" if free2 is not None else ""
                core.emit("setup", "5.5.6 Memory Guard: preflight thiếu RAM; đang thử lại batch 32 + context 3072" + suffix + "…")
                return original_prewarm(self)
        finally:
            self._chs_preflight = False

    Runtime._forced_gpu_options = guarded_forced
    Runtime._chat = guarded_chat
    Runtime._prewarm_vision_gpu = guarded_prewarm
    return Runtime
