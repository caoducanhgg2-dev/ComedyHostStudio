"""SRT Voice Studio 1.7 production-workspace integration."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MethodType

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
)

from .batch import WAITING, DONE, FAILED, CANCELLED
from .quality import format_quality
from .render_cache import TtsCache
from .v161_upgrade import enhance_window_v161


def _install_17_settings(window):
    timeline_group = next(
        (g for g in window.findChildren(QGroupBox) if g.title().startswith("⑤")), None)
    if timeline_group is None:
        raise RuntimeError("Không tìm thấy phần căn timeline cho Smart Fit 3.0.")

    row = QHBoxLayout()
    window.smart_fit3 = QCheckBox("Smart Fit 3.0 · làm mượt tốc độ giữa các câu")
    window.smart_fit3.setChecked(True)
    window.smart_fit3.setToolTip(
        "Giảm các bước nhảy tốc độ không cần thiết giữa caption liền nhau, "
        "nhưng không được tạo overflow.")
    window.render_cache_enabled = QCheckBox("Render Cache · tái sử dụng TTS đã tạo")
    window.render_cache_enabled.setChecked(True)
    window.render_cache_enabled.setToolTip(
        "Cache chỉ lưu raw TTS. Đổi Emotion/FX/Smart Fit/SFX vẫn xử lý lại an toàn.")
    row.addWidget(window.smart_fit3)
    row.addWidget(window.render_cache_enabled)
    timeline_group.layout().addLayout(row)

    base_settings = window.settings

    def settings_17(self):
        return replace(
            base_settings(),
            smart_fit3=bool(self.smart_fit3.isChecked()),
            use_render_cache=bool(self.render_cache_enabled.isChecked()),
        )

    window.settings = MethodType(settings_17, window)
    window.edit_controls.extend([window.smart_fit3, window.render_cache_enabled])


def _install_workspace_controls(window):
    panel = window.multi_file_panel
    panel.table.setSelectionMode(QAbstractItemView.ExtendedSelection)

    row = QHBoxLayout()
    panel.select_all_button = QPushButton("Chọn tất cả")
    panel.open_mp3_button = QPushButton("Mở MP3 tệp đang chọn")
    panel.retry_caption_button = QPushButton("Làm mới TTS câu đang chọn")
    panel.retry_caption_note = QLabel(
        "Retry caption dùng cache: chỉ câu được chọn bị xóa raw TTS; các câu cache khác được tái sử dụng.")
    panel.retry_caption_note.setWordWrap(True)
    row.addWidget(panel.select_all_button)
    row.addWidget(panel.open_mp3_button)
    row.addWidget(panel.retry_caption_button)
    row.addWidget(panel.retry_caption_note, 1)
    panel.layout().insertLayout(2, row)

    def selected_rows():
        return sorted({index.row() for index in panel.table.selectionModel().selectedRows()})

    def remove_selected_multi():
        if window.busy():
            return
        rows = selected_rows()
        if not rows:
            return
        for row_index in reversed(rows):
            if 0 <= row_index < len(panel.queue.items):
                panel.queue.items.pop(row_index)
        window.batch_panel.refresh()
        if panel.queue.items:
            panel.table.selectRow(min(rows[0], len(panel.queue.items) - 1))
            panel.activate_selected()
        else:
            panel._clear_active_file()

    try:
        panel.remove_button.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass
    panel.remove_button.clicked.connect(remove_selected_multi)

    panel.select_all_button.clicked.connect(panel.table.selectAll)

    def open_selected_mp3():
        item = panel.selected()
        if item is None or not item.output or not Path(item.output).is_file():
            window.status.setText("Tệp đang chọn chưa có MP3 hoàn tất.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(item.output).resolve())))

    panel.open_mp3_button.clicked.connect(open_selected_mp3)

    def retry_selected_caption():
        if window.busy():
            return
        item = panel.selected()
        caption_pos = window.caption_select.currentData()
        if item is None or caption_pos is None or not (0 <= caption_pos < len(window.captions)):
            window.status.setText("Hãy chọn một tệp và một caption cần tạo lại TTS.")
            return
        caption = window.captions[caption_pos]
        settings = window.settings()
        window._v17_retry_item_id = item.id
        window._v17_retry_caption = caption.index
        window.start("cache_caption", dict(text=caption.text, settings=settings))

    panel.retry_caption_button.clicked.connect(retry_selected_caption)

    window.edit_controls.extend([
        panel.select_all_button, panel.open_mp3_button, panel.retry_caption_button
    ])


def _install_quality_reporting(window):
    base_success = window.success

    def success_17(task, result):
        if task == "cache_caption" and isinstance(result, dict):
            item = next((x for x in window.multi_file_panel.queue.items
                         if x.id == getattr(window, "_v17_retry_item_id", None)), None)
            if item is not None and item.state in (DONE, FAILED, CANCELLED):
                item.state = WAITING
                item.progress = 0
                item.error = ""
                item.report = {}
                window.batch_panel.refresh()
            window.status.setText(
                f"Đã tạo lại TTS câu {getattr(window, '_v17_retry_caption', '?')} · "
                "các caption cache khác được giữ nguyên.")
            return
        base_success(task, result)
        if task == "render" and isinstance(result, dict):
            quality = dict(result.get("quality") or {})
            cache = (
                f"Render Cache: {int(result.get('cache_hits', 0))} hit · "
                f"{int(result.get('cache_misses', 0))} miss")
            smart = (
                f"Smart Fit 3.0: {int(result.get('smart_fit3_neighbor_adjusted', 0))} "
                "caption được làm mượt tốc độ")
            current = window.report.toPlainText().rstrip()
            window.report.setPlainText(
                current + ("\n\n" if current else "") +
                format_quality(quality) + "\n" + cache + "\n" + smart)
            window.status.setText(
                window.status.text() + f" · QC {quality.get('status', 'WARN')}")
        elif task == "batch":
            items = list(window.multi_file_panel.queue.items)
            done = [i for i in items if i.state == DONE and i.report]
            if done:
                lines = ["", "QC 1.7 theo từng MP3:"]
                for item in done:
                    q = dict(item.report.get("quality") or {})
                    lines.append(
                        f"• {item.source.name}: QC {q.get('status', 'WARN')} · "
                        f"cache {item.report.get('cache_hits', 0)}/"
                        f"{item.report.get('cache_hits', 0) + item.report.get('cache_misses', 0)} hit")
                window.report.setPlainText(window.report.toPlainText().rstrip() + "\n" + "\n".join(lines))

    window.success = success_17


def enhance_window_v17(window):
    window = enhance_window_v161(window)
    _install_17_settings(window)
    _install_workspace_controls(window)
    from .sfx_editor_ui import SfxEditorPanel
    window.sfx_editor_panel = SfxEditorPanel(window)
    window.tabs.addTab(window.sfx_editor_panel, "SFX Editor 1.7")
    def refresh_sfx_editor(index):
        if window.tabs.widget(index) is window.sfx_editor_panel:
            window.sfx_editor_panel.refresh()
    window.tabs.currentChanged.connect(refresh_sfx_editor)
    window.multi_file_panel.table.itemSelectionChanged.connect(
        lambda: window.sfx_editor_panel.refresh()
        if window.tabs.currentWidget() is window.sfx_editor_panel else None)
    _install_quality_reporting(window)
    window.status.setText(
        "Sẵn sàng · 1.7.0: Unified Workspace + Render Cache + Smart Fit 3.0 + Auto QC")
    return window
