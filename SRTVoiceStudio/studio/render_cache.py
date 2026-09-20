"""Persistent raw-TTS cache for SRT Voice Studio 1.7.

The cache stores only backend output before Emotion/Voice FX/Smart Fit/SFX. This
means changing timing or SFX can reuse expensive TTS safely without reusing a
processed caption with the wrong effects.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from .paths import data_dir

CACHE_SCHEMA = "tts-cache-1.7-v1"
MAX_CACHE_ITEMS = 1200
MAX_CACHE_BYTES = 1_500_000_000


def _identity(settings, text: str) -> dict:
    return {
        "schema": CACHE_SCHEMA,
        "language": str(settings.language),
        "voice": str(settings.voice),
        "native_style": settings.native_style,
        "text": str(text),
    }


def cache_key(settings, text: str) -> str:
    raw = json.dumps(_identity(settings, text), ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class TtsCache:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else data_dir() / "cache" / "tts-v17"
        self.root.mkdir(parents=True, exist_ok=True)
        self._writes = 0

    def path_for(self, settings, text: str) -> Path:
        key = cache_key(settings, text)
        return self.root / key[:2] / (key + ".npz")

    def get(self, settings, text: str):
        path = self.path_for(settings, text)
        if not path.is_file():
            return None
        try:
            with np.load(path, allow_pickle=False) as value:
                samples = np.asarray(value["samples"], dtype=np.float32).reshape(-1).copy()
                rate = int(np.asarray(value["rate"]).reshape(-1)[0])
            if (not len(samples) or not np.isfinite(samples).all()
                    or not np.any(np.abs(samples) > 1e-7)
                    or not 8000 <= rate <= 192000):
                raise ValueError("invalid cached audio")
            os.utime(path, None)
            return samples, rate
        except (OSError, ValueError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def put(self, settings, text: str, samples, rate: int):
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if (not len(samples) or len(samples) > int(rate) * 90
                or not np.isfinite(samples).all()
                or not np.any(np.abs(samples) > 1e-7)
                or not 8000 <= int(rate) <= 192000):
            return False
        path = self.path_for(settings, text)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="tts-", suffix=".npz", dir=path.parent)
        os.close(fd)
        try:
            np.savez_compressed(temp_name, samples=samples, rate=np.asarray([int(rate)], dtype=np.int32))
            os.replace(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)
        self._writes += 1
        if self._writes == 1 or self._writes % 25 == 0:
            self.cleanup()
        return True

    def invalidate(self, settings, text: str) -> bool:
        path = self.path_for(settings, text)
        existed = path.exists()
        path.unlink(missing_ok=True)
        return existed

    def stats(self):
        try:
            files = [p for p in self.root.rglob("*.npz") if p.is_file()]
            return {
                "items": len(files),
                "bytes": sum(p.stat().st_size for p in files),
            }
        except OSError:
            return {"items": 0, "bytes": 0}

    def clear(self):
        removed = 0
        freed = 0
        try:
            files = [p for p in self.root.rglob("*.npz") if p.is_file()]
            for path in files:
                try:
                    size = path.stat().st_size
                    path.unlink()
                    removed += 1
                    freed += size
                except OSError:
                    continue
            for folder in sorted(
                    (p for p in self.root.rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts), reverse=True):
                try:
                    folder.rmdir()
                except OSError:
                    pass
        finally:
            self.root.mkdir(parents=True, exist_ok=True)
        return {"items": removed, "bytes": freed}

    def cleanup(self):
        try:
            files = [p for p in self.root.rglob("*.npz") if p.is_file()]
            total = sum(p.stat().st_size for p in files)
            if len(files) <= MAX_CACHE_ITEMS and total <= MAX_CACHE_BYTES:
                return
            files.sort(key=lambda p: p.stat().st_mtime)
            while files and (len(files) > MAX_CACHE_ITEMS or total > MAX_CACHE_BYTES):
                victim = files.pop(0)
                size = victim.stat().st_size
                victim.unlink(missing_ok=True)
                total -= size
        except OSError:
            # Cache maintenance must never fail a render.
            return


def regenerate_caption_cache(backend, text: str, settings, cancel, progress=lambda *_: None):
    """Regenerate exactly one raw-TTS cache entry in the background."""
    from .voice_backends import synthesize_selected
    cache = TtsCache()
    cache.invalidate(settings, text)
    progress(0, 1, "Đang tạo lại TTS cho caption đã chọn…")
    samples, rate = synthesize_selected(
        backend, text, settings, cancel,
        lambda msg: progress(0, 1, msg))
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if (not len(samples) or not np.isfinite(samples).all()
            or not np.any(np.abs(samples) > 1e-7)):
        raise RuntimeError("TTS caption trả về audio rỗng hoặc không hợp lệ.")
    if not cache.put(settings, text, samples, int(rate)):
        raise RuntimeError("Không thể lưu TTS caption vào Render Cache.")
    progress(1, 1, "Đã tạo lại TTS caption và lưu Render Cache.")
    return {
        "caption": int(getattr(settings, "_caption_index", 0) or 0),
        "text": str(text),
        "samples": int(len(samples)),
        "rate": int(rate),
        "cache_key": cache_key(settings, text),
    }
