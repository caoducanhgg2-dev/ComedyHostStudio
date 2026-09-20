"""Sequential queue; every item uses the unchanged production renderer."""
from dataclasses import dataclass, field, replace
from pathlib import Path
import threading
import uuid
from .render import Settings, render
from .timeline import read_srt
from .audio import Cancelled

WAITING, RUNNING, DONE, FAILED, CANCELLED = 'Chờ', 'Đang xử lý', 'Hoàn tất', 'Lỗi', 'Đã hủy'

@dataclass
class QueueItem:
    source: Path
    settings: Settings
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: str = WAITING
    progress: int = 0
    captions: int = 0
    duration_ms: int = 0
    output: str = ''
    error: str = ''
    report: dict = field(default_factory=dict)
    sfx_overrides: tuple = field(default_factory=tuple)

    def inspect(self):
        try:
            captions = read_srt(self.source)
            self.captions = len(captions)
            self.duration_ms = max(c.end for c in captions)
        except Exception as exc:
            self.error = str(exc)  # Remains queued: failure is isolated by run().

class BatchQueue:
    def __init__(self):
        self.items = []
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.current_cancel = None
        self.current_id = None
        self.running = False

    def add(self, paths, settings):
        with self.lock:
            if self.running:
                raise RuntimeError('Hãy chờ hàng đợi kết thúc trước khi thêm tệp.')
            known = {str(i.source.resolve()).casefold() for i in self.items}
            added = []
            for path in paths:
                path = Path(path).resolve()
                if path.suffix.lower() != '.srt' or str(path).casefold() in known:
                    continue
                item = QueueItem(path, replace(settings))
                item.inspect()
                self.items.append(item); added.append(item)
                known.add(str(path).casefold())
            return added

    def cancel_item(self, item_id):
        with self.lock:
            for item in self.items:
                if item.id == item_id:
                    if item.state == RUNNING and self.current_cancel:
                        self.current_cancel.set()
                    elif item.state == WAITING:
                        item.state = CANCELLED
                    return

    def cancel_all(self):
        with self.lock:
            self.stop.set()
            if self.current_cancel:
                self.current_cancel.set()
            for item in self.items:
                if item.state == WAITING:
                    item.state = CANCELLED

    def retry(self, item_ids=None):
        with self.lock:
            if self.running:
                raise RuntimeError('Hàng đợi đang xử lý.')
            for item in self.items:
                if item.state in (FAILED, CANCELLED) and (item_ids is None or item.id in item_ids):
                    item.state, item.error, item.progress = WAITING, '', 0
            self.stop.clear()

    def run(self, backend, output_dir=None, common_settings=None, update=lambda _: None, renderer=render):
        with self.lock:
            if self.running:
                raise RuntimeError('Hàng đợi đã được khởi chạy.')
            self.running = True; self.stop.clear()
        reserved = set()
        try:
            for item in self.items:
                with self.lock:
                    if item.state != WAITING:
                        continue
                    if self.stop.is_set():
                        item.state = CANCELLED; update(item); continue
                    item.state = RUNNING
                    self.current_id = item.id
                    self.current_cancel = threading.Event()
                    cancel = self.current_cancel
                    settings = replace(
                        common_settings or item.settings,
                        sfx_overrides=tuple(item.sfx_overrides or ()))
                    item.settings = settings
                update(item)
                try:
                    folder = Path(output_dir) if output_dir else item.source.parent
                    folder.mkdir(parents=True, exist_ok=True)
                    existing = {p.name.casefold() for p in folder.iterdir()}
                    n = 1
                    while True:
                        suffix = '' if n == 1 else f'_{n}'
                        output = folder / (item.source.stem + '_Voice' + suffix + '.mp3')
                        key = str(output.resolve()).casefold()
                        if key not in reserved and output.name.casefold() not in existing:
                            reserved.add(key); break
                        n += 1
                    def progress(done, total, message):
                        item.progress = min(99, int(done * 100 / max(1, total)))
                        update(item)
                    report = renderer(item.source, output, settings, backend, cancel, progress)
                    item.report, item.output = report, str(output)
                    item.state, item.progress, item.error = DONE, 100, ''
                except Cancelled:
                    item.state, item.error = CANCELLED, ''
                except Exception as exc:
                    item.state, item.error = FAILED, str(exc)
                finally:
                    with self.lock:
                        self.current_cancel = None; self.current_id = None
                    update(item)
        finally:
            with self.lock:
                self.running = False
        return {state: sum(i.state == state for i in self.items)
                for state in (WAITING, RUNNING, DONE, FAILED, CANCELLED)}
