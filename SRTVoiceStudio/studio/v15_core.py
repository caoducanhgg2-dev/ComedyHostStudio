"""Non-UI helpers for SRT Voice Studio 1.5 workflow features."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, fields
from pathlib import Path

from .paths import data_dir
from .render import Settings
from .batch import QueueItem, BatchQueue, WAITING, RUNNING, DONE, FAILED, CANCELLED


BUILTIN_PRESETS = {
    'JP TikTok Comedy': dict(language='Japanese', voice='jf_alpha', speed=1.03, gap_ms=-1,
        adaptive=True, loudness=True, overflow='Safe Trim', emotion_mode='Manual',
        emotion='Funny / Playful', intensity='Medium', effect='None', strength='Medium',
        native_style=None, continuous=True, continuous_target_ms=100),
    'US Reviewer': dict(language='English US', voice='am_puck', speed=1.03, gap_ms=-1,
        adaptive=True, loudness=True, overflow='Safe Trim', emotion_mode='Manual',
        emotion='Funny / Playful', intensity='Medium', effect='None', strength='Medium',
        native_style=None, continuous=True, continuous_target_ms=100),
    'Renovation Calm': dict(language='English US', voice='af_heart', speed=1.0, gap_ms=-1,
        adaptive=True, loudness=True, overflow='Safe Trim', emotion_mode='Manual',
        emotion='Calm', intensity='Mild', effect='None', strength='Medium',
        native_style=None, continuous=True, continuous_target_ms=110),
    'Horror Narration': dict(language='English US', voice='am_onyx', speed=1.0, gap_ms=-1,
        adaptive=True, loudness=True, overflow='Safe Trim', emotion_mode='Manual',
        emotion='Narrator', intensity='Medium', effect='None', strength='Medium',
        native_style=None, continuous=True, continuous_target_ms=110),
    'Food Challenge': dict(language='English US', voice='am_puck', speed=1.05, gap_ms=-1,
        adaptive=True, loudness=True, overflow='Safe Trim', emotion_mode='Manual',
        emotion='Excited', intensity='Medium', effect='None', strength='Medium',
        native_style=None, continuous=True, continuous_target_ms=90),
}


def _atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.stem+'-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def settings_from_mapping(value):
    allowed = {f.name for f in fields(Settings)}
    source = value if isinstance(value, dict) else {}
    return Settings(**{k:v for k,v in source.items() if k in allowed})


def preset_path():
    return data_dir() / 'presets-v15.json'


def load_custom_presets(path=None):
    path = Path(path) if path else preset_path()
    try:
        value = json.loads(path.read_text('utf-8'))
        if not isinstance(value, dict):
            return {}
        result = {}
        for name, settings in value.items():
            if isinstance(name, str) and name.strip() and isinstance(settings, dict):
                result[name.strip()] = asdict(settings_from_mapping(settings))
        return result
    except (OSError, ValueError, TypeError):
        return {}


def save_custom_presets(value, path=None):
    path = Path(path) if path else preset_path()
    clean = {}
    for name, settings in dict(value).items():
        if not isinstance(name, str) or not name.strip():
            continue
        clean[name.strip()] = asdict(settings_from_mapping(settings))
    _atomic_json(path, clean)


def all_presets(path=None):
    result = {name: dict(value) for name, value in BUILTIN_PRESETS.items()}
    result.update(load_custom_presets(path))
    return result


def estimate_caption(text: str, slot_seconds: float, language: str):
    """Fast preflight estimate; final production fitting still uses real TTS."""
    slot_seconds = max(float(slot_seconds), 0.001)
    if language == 'Japanese':
        units = len(re.sub(r'\s+', '', text))
        estimated = 0.18 + units / 5.8
    else:
        units = len(re.findall(r"[A-Za-z0-9']+", text))
        estimated = 0.16 + units / 2.75
    punctuation = len(re.findall(r'[,.!?;:。！？、]', text))
    estimated += min(0.55, punctuation * 0.045)
    ratio = estimated / slot_seconds
    if ratio >= 1.25:
        status, advice = 'NGUY CƠ CẮT', 'Rút câu hoặc tăng thời lượng SRT; 1.20× có thể vẫn không đủ.'
    elif ratio > 1.03:
        status, advice = 'HƠI DÀI', 'Smart Fit sẽ ưu tiên tăng tốc trong giới hạn an toàn.'
    elif ratio < 0.45:
        status, advice = 'QUÁ NGẮN', 'Continuous Voice sẽ giảm khoảng lặng; có thể vẫn còn silence.'
    else:
        status, advice = 'ỔN', 'Có thể render với Smart Timeline Fit 2.0.'
    return dict(units=units, estimated_seconds=estimated, slot_seconds=slot_seconds,
                ratio=ratio, status=status, advice=advice)


def batch_state_path():
    return data_dir() / 'batch-queue-v15.json'


def save_batch_queue(queue: BatchQueue, path=None):
    path = Path(path) if path else batch_state_path()
    items = []
    for item in queue.items:
        items.append(dict(source=str(item.source), settings=asdict(item.settings), id=item.id,
            state=item.state, progress=item.progress, captions=item.captions,
            duration_ms=item.duration_ms, output=item.output, error=item.error,
            report=item.report if isinstance(item.report, dict) else {}))
    _atomic_json(path, {'version': 1, 'items': items})


def load_batch_queue(path=None):
    path = Path(path) if path else batch_state_path()
    queue = BatchQueue()
    try:
        value = json.loads(path.read_text('utf-8'))
        items = value.get('items', []) if isinstance(value, dict) else []
    except (OSError, ValueError, TypeError):
        return queue
    for raw in items:
        try:
            source = Path(raw['source'])
            if not source.is_file() or source.suffix.lower() != '.srt':
                continue
            item = QueueItem(source.resolve(), settings_from_mapping(raw.get('settings', {})), id=str(raw.get('id') or ''))
            if not item.id:
                import uuid
                item.id = uuid.uuid4().hex
            item.state = str(raw.get('state', WAITING))
            item.progress = int(raw.get('progress', 0))
            item.captions = int(raw.get('captions', 0))
            item.duration_ms = int(raw.get('duration_ms', 0))
            item.output = str(raw.get('output', ''))
            item.error = str(raw.get('error', ''))
            item.report = raw.get('report', {}) if isinstance(raw.get('report', {}), dict) else {}
            # A process crash must never leave a permanently RUNNING row.
            if item.state == RUNNING:
                item.state, item.progress, item.error = WAITING, 0, 'Khôi phục sau khi ứng dụng đóng giữa tác vụ.'
            if item.state == DONE and (not item.output or not Path(item.output).is_file()):
                item.state, item.progress, item.output = WAITING, 0, ''
            if item.state not in (WAITING, DONE, FAILED, CANCELLED):
                item.state, item.progress = WAITING, 0
            queue.items.append(item)
        except (KeyError, TypeError, ValueError, OSError):
            continue
    return queue
