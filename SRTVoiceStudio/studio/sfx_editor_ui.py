"""Per-file manual SFX editor for SRT Voice Studio 1.7."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QComboBox, QSpinBox, QPushButton,
)

from .sfx import KIND_LABELS, plan_sfx
from .sfx_editor import apply_sfx_overrides, EditedSfxEvent
from .timeline import read_srt, display_time
from .batch import DONE, FAILED, CANCELLED, WAITING


class SfxEditorPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.events = []
        layout = QVBoxLayout(self)

        title = QLabel("SFX Editor 1.7 · chỉnh cue theo từng file")
        title.setStyleSheet("font-size:17px;font-weight:650;")
        layout.addWidget(title)
        note = QLabel(
            "Auto SFX vẫn lên kế hoạch trước. Tại đây bạn có thể tắt cue, đổi loại, "
            "dịch thời điểm ±1.5 giây hoặc đổi mức riêng. Chỉnh sửa chỉ áp dụng cho file đang chọn.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Câu", "Thời điểm", "SFX", "Nguồn", "Mức riêng", "Cue"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        controls = QHBoxLayout()
        self.enabled = QCheckBox("Dùng cue này")
        self.enabled.setChecked(True)
        self.kind = QComboBox()
        for key, label in KIND_LABELS.items():
            self.kind.addItem(label, key)
        self.offset = QSpinBox()
        self.offset.setRange(-1500, 1500)
        self.offset.setSingleStep(50)
        self.offset.setSuffix(" ms")
        self.level = QComboBox()
        for text, value in [("Nhẹ 0.70×", .70), ("Vừa 1.00×", 1.0), ("Rõ 1.30×", 1.30)]:
            self.level.addItem(text, value)
        self.apply_button = QPushButton("Áp dụng cho câu")
        self.reset_button = QPushButton("Bỏ chỉnh sửa câu")
        self.add_button = QPushButton("Thêm cue cho caption đang chọn")
        controls.addWidget(self.enabled)
        controls.addWidget(QLabel("Loại"))
        controls.addWidget(self.kind)
        controls.addWidget(QLabel("Dịch"))
        controls.addWidget(self.offset)
        controls.addWidget(QLabel("Mức"))
        controls.addWidget(self.level)
        controls.addWidget(self.apply_button)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.add_button)
        layout.addLayout(controls)

        self.status = QLabel("Chọn một file trong Workspace để chỉnh SFX.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.table.itemSelectionChanged.connect(self.load_selected)
        self.apply_button.clicked.connect(self.apply_selected)
        self.reset_button.clicked.connect(self.reset_selected)
        self.add_button.clicked.connect(self.add_current_caption)

    def current_item(self):
        return self.window.multi_file_panel.selected()

    def _overrides(self):
        item = self.current_item()
        return list(item.sfx_overrides or ()) if item is not None else []

    def _set_override(self, value):
        item = self.current_item()
        if item is None:
            return
        caption = int(value["caption"])
        values = [x for x in self._overrides()
                  if isinstance(x, dict) and int(x.get("caption", -1)) != caption]
        values.append(dict(value))
        values.sort(key=lambda x: int(x.get("caption", 0)))
        item.sfx_overrides = tuple(values)
        if item.state in (DONE, FAILED, CANCELLED):
            item.state = WAITING
            item.progress = 0
            item.error = ""
            item.report = {}
        self.window.batch_panel.refresh()

    def _remove_override(self, caption):
        item = self.current_item()
        if item is None:
            return
        item.sfx_overrides = tuple(
            x for x in self._overrides()
            if not isinstance(x, dict) or int(x.get("caption", -1)) != int(caption))
        if item.state in (DONE, FAILED, CANCELLED):
            item.state = WAITING
            item.progress = 0
            item.error = ""
            item.report = {}
        self.window.batch_panel.refresh()

    def refresh(self):
        item = self.current_item()
        previous = self.selected_event()
        previous_caption = previous.caption_index if previous is not None else None
        self.events = []
        self.disabled_captions = set()
        self.table.setRowCount(0)
        if item is None:
            self.status.setText("Chọn một file trong Workspace để chỉnh SFX.")
            return
        self.table.blockSignals(True)
        try:
            captions = read_srt(item.source)
            settings = self.window.settings()
            base = plan_sfx(captions, settings.language, settings.sfx_density)
            self.events = apply_sfx_overrides(
                base, captions, item.sfx_overrides, settings.language)
            raw_overrides = [x for x in item.sfx_overrides if isinstance(x, dict)]
            self.disabled_captions = {
                int(x.get("caption")) for x in raw_overrides
                if str(x.get("caption", "")).isdigit() and not bool(x.get("enabled", True))
            }
            rendered_captions = {e.caption_index for e in self.events}
            for event in base:
                if event.caption_index in self.disabled_captions and event.caption_index not in rendered_captions:
                    self.events.append(event)
                    rendered_captions.add(event.caption_index)
            by_caption = {c.index: c for c in captions}
            for override in raw_overrides:
                if bool(override.get("enabled", True)):
                    continue
                try:
                    caption_index = int(override.get("caption"))
                except (TypeError, ValueError):
                    continue
                if caption_index in rendered_captions or caption_index not in by_caption:
                    continue
                caption = by_caption[caption_index]
                kind = str(override.get("kind") or "accent")
                if kind not in KIND_LABELS:
                    kind = "accent"
                self.events.append(EditedSfxEvent(
                    caption_index=caption_index,
                    start_ms=int(caption.start + 120),
                    kind=kind,
                    score=0,
                    reason="manual:disabled",
                    gain_scale=float(override.get("gain_scale", 1.0) or 1.0),
                    manual=True))
            self.events.sort(key=lambda e: (e.start_ms, e.caption_index))
        except Exception as exc:
            self.table.blockSignals(False)
            self.status.setText("Không phân tích được SFX: " + str(exc))
            return

        overrides = {int(x.get("caption")): x for x in self._overrides()
                     if isinstance(x, dict) and str(x.get("caption", "")).isdigit()}
        self.table.setRowCount(len(self.events))
        for row, event in enumerate(self.events):
            override = overrides.get(event.caption_index, {})
            values = [
                str(event.caption_index),
                display_time(event.start_ms),
                KIND_LABELS.get(event.kind, event.kind),
                ("Tắt thủ công" if event.caption_index in self.disabled_captions
                 else ("Thủ công" if getattr(event, "manual", False) else "Auto")),
                ("—" if event.caption_index in self.disabled_captions
                 else f"{float(getattr(event, 'gain_scale', 1.0)):.2f}×"),
                event.reason,
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        selected_row = next(
            (row for row, event in enumerate(self.events)
             if event.caption_index == previous_caption), -1)
        if selected_row < 0 and self.events:
            selected_row = 0
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.load_selected()
        self.status.setText(
            f"{item.source.name} · {len(self.events)} cue sau chỉnh sửa · "
            f"{len(overrides)} caption có override riêng.")

    def selected_event(self):
        row = self.table.currentRow()
        return self.events[row] if 0 <= row < len(self.events) else None

    def load_selected(self):
        event = self.selected_event()
        if event is None:
            return
        override = next(
            (x for x in self._overrides()
             if isinstance(x, dict) and int(x.get("caption", -1)) == event.caption_index),
            None)
        enabled = bool(override.get("enabled", True)) if override else (
            event.caption_index not in getattr(self, "disabled_captions", set()))
        kind = str(override.get("kind") or event.kind) if override else event.kind
        offset = int(override.get("offset_ms", 0) or 0) if override else 0
        level = (float(override.get("gain_scale", 1.0) or 1.0)
                 if override else float(getattr(event, "gain_scale", 1.0)))
        self.enabled.setChecked(enabled)
        index = self.kind.findData(kind)
        if index >= 0:
            self.kind.setCurrentIndex(index)
        self.offset.setValue(max(self.offset.minimum(), min(self.offset.maximum(), offset)))
        best = min(range(self.level.count()),
                   key=lambda i: abs(float(self.level.itemData(i)) - level))
        self.level.setCurrentIndex(best)

    def apply_selected(self):
        if self.window.busy():
            return
        event = self.selected_event()
        if event is None:
            self.status.setText("Hãy chọn một cue trong bảng.")
            return
        self._set_override(dict(
            caption=event.caption_index,
            enabled=bool(self.enabled.isChecked()),
            kind=str(self.kind.currentData()),
            offset_ms=int(self.offset.value()),
            gain_scale=float(self.level.currentData()),
        ))
        self.refresh()

    def reset_selected(self):
        if self.window.busy():
            return
        event = self.selected_event()
        if event is None:
            return
        self._remove_override(event.caption_index)
        self.refresh()

    def add_current_caption(self):
        if self.window.busy():
            return
        item = self.current_item()
        pos = self.window.caption_select.currentData()
        if item is None or pos is None or not (0 <= pos < len(self.window.captions)):
            self.status.setText("Ở tab Tệp / Nghe thử, hãy chọn caption muốn thêm SFX.")
            return
        caption = self.window.captions[pos]
        self._set_override(dict(
            caption=caption.index,
            enabled=True,
            kind=str(self.kind.currentData()),
            offset_ms=int(self.offset.value()),
            gain_scale=float(self.level.currentData()),
        ))
        self.refresh()
