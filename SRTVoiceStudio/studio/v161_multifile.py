"""SRT Voice Studio 1.6.1 unified one/many-file workspace.

The old Batch tab remains as an internal queue/recovery engine, but the user
works from the first tab only. One or many SRT files share the current
voice/timing/emotion/SFX settings at the moment processing starts.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MethodType

from PySide6.QtCore import QObject, QEvent, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGroupBox,
)

from .batch import WAITING, RUNNING, DONE, FAILED, CANCELLED
from .timeline import display_time
from . import ui_text as vi


class _DropFilter(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel

    def eventFilter(self, obj, event):
        if event.type() == QEvent.DragEnter:
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if any(u.isLocalFile() and u.toLocalFile().lower().endswith('.srt') for u in urls):
                event.acceptProposedAction()
                return True
        if event.type() == QEvent.Drop:
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            paths = [u.toLocalFile() for u in urls
                     if u.isLocalFile() and u.toLocalFile().lower().endswith('.srt')]
            if paths:
                self.panel.add_paths(paths)
                event.acceptProposedAction()
                return True
        return False


class UnifiedFilePanel(QWidget):
    """Compact queue embedded in the former single-file card."""
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.queue = window.batch_panel.queue
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(7)

        note = QLabel(
            'Chọn 1 hoặc nhiều SRT. Tất cả tệp đang Chờ sẽ dùng CHUNG cấu hình '
            'Ngôn ngữ · Voice · Emotion/FX · Smart Fit · Continuous Voice · Auto SFX bên dưới.')
        note.setWordWrap(True)
        note.setStyleSheet('color:#a8c6e7;')
        layout.addWidget(note)

        actions = QHBoxLayout()
        self.add_files_button = QPushButton('+ Thêm tệp')
        self.add_folder_button = QPushButton('+ Thêm thư mục')
        self.remove_button = QPushButton('Bỏ tệp đã chọn')
        self.clear_done_button = QPushButton('Xóa tệp đã hoàn tất')
        self.retry_button = QPushButton('Thử lại tệp lỗi / đã hủy')
        for button in (self.add_files_button, self.add_folder_button, self.remove_button,
                       self.clear_done_button, self.retry_button):
            actions.addWidget(button)
        layout.addLayout(actions)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel('Kết quả'))
        self.destination = QLineEdit()
        self.destination.setPlaceholderText('Để trống: MP3 nằm cạnh từng SRT')
        self.output_button = QPushButton('Chọn thư mục')
        output_row.addWidget(self.destination, 1)
        output_row.addWidget(self.output_button)
        layout.addLayout(output_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ['Tệp SRT', 'Số câu', 'Thời lượng', 'Tiến độ', 'Trạng thái', 'MP3 / Lỗi'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setMinimumHeight(105)
        self.table.setMaximumHeight(190)
        layout.addWidget(self.table)

        self.summary = QLabel('Chưa có SRT trong danh sách.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.add_files_button.clicked.connect(self.add_files)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_done_button.clicked.connect(self.clear_completed)
        self.retry_button.clicked.connect(self.retry_failed)
        self.output_button.clicked.connect(self.choose_output)
        self.table.itemSelectionChanged.connect(self.activate_selected)

    def selected(self):
        row = self.table.currentRow()
        return self.queue.items[row] if 0 <= row < len(self.queue.items) else None

    def add_files(self):
        if self.window.busy():
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self.window, 'Chọn một hoặc nhiều SRT', '', 'SRT (*.srt)')
        self.add_paths(paths)

    def add_folder(self):
        if self.window.busy():
            return
        folder = QFileDialog.getExistingDirectory(self.window, 'Chọn thư mục chứa SRT')
        if folder:
            paths = sorted(p for p in Path(folder).rglob('*')
                           if p.is_file() and p.suffix.lower() == '.srt')
            self.add_paths(paths)

    def add_paths(self, paths):
        if self.window.busy():
            return []
        paths = [Path(p) for p in paths if str(p)]
        if not paths:
            return []
        added = self.queue.add(paths, self.window.settings())
        self.window.batch_panel.refresh()  # also persists queue + syncs this panel
        if added:
            first = self.queue.items.index(added[0])
            self.table.selectRow(first)
            self.activate_selected()
        else:
            self.window.status.setText('Không thêm tệp mới: tệp đã có trong danh sách hoặc không phải .srt.')
        return added

    def choose_output(self):
        if self.window.busy():
            return
        folder = QFileDialog.getExistingDirectory(self.window, 'Chọn thư mục kết quả MP3')
        if folder:
            self.destination.setText(folder)

    def remove_selected(self):
        if self.window.busy():
            return
        item = self.selected()
        if item is None:
            return
        self.queue.items.remove(item)
        self.window.batch_panel.refresh()
        if self.queue.items:
            self.table.selectRow(min(self.table.currentRow(), len(self.queue.items) - 1))
            self.activate_selected()
        else:
            self._clear_active_file()

    def clear_completed(self):
        if self.window.busy():
            return
        self.queue.items = [item for item in self.queue.items if item.state != DONE]
        self.window.batch_panel.refresh()
        if self.queue.items:
            self.table.selectRow(0)
            self.activate_selected()
        else:
            self._clear_active_file()

    def retry_failed(self):
        if self.window.busy():
            return
        self.queue.retry()
        self.window.batch_panel.refresh()

    def _clear_active_file(self):
        self.window.file.clear()
        self.window.loaded_fingerprint = None
        self.window.load_captions()
        self.window.file_info.setText('Chưa chọn tệp · có thể thêm một hoặc nhiều SRT')

    def activate_selected(self):
        item = self.selected()
        if item is None or self.window.busy():
            return
        path = str(item.source)
        if self.window.file.text().strip() != path:
            self.window.file.setText(path)
            self.window.loaded_fingerprint = None
            self.window.load_captions()
        self.window.status.setText(
            f'Đang xem trước: {item.source.name} · mọi tùy chọn hiện tại sẽ áp dụng chung khi xử lý.')

    def start(self):
        if self.window.busy():
            return
        waiting = [item for item in self.queue.items if item.state == WAITING]
        if not waiting:
            self.window.status.setText('Không có tệp đang Chờ. Thêm SRT mới hoặc bấm Thử lại tệp lỗi / đã hủy.')
            return
        settings = self.window.settings()
        # Make the UI semantics explicit before the worker starts: every pending
        # item receives the same snapshot. BatchQueue.run repeats this assignment
        # defensively through common_settings.
        for item in waiting:
            item.settings = replace(settings)
        self.window.batch_panel.refresh()
        self.window.start('batch', dict(
            queue=self.queue,
            output_dir=self.destination.text().strip() or None,
            common_settings=settings,
        ))

    def set_busy(self, busy: bool):
        for control in (self.add_files_button, self.add_folder_button, self.remove_button,
                        self.clear_done_button, self.retry_button, self.destination,
                        self.output_button):
            control.setEnabled(not busy)
        self.table.setEnabled(not busy)

    def refresh(self):
        current_id = self.selected().id if self.selected() is not None else None
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.queue.items))
        selected_row = -1
        for row, item in enumerate(self.queue.items):
            if item.id == current_id:
                selected_row = row
            values = [
                item.source.name,
                str(item.captions),
                display_time(item.duration_ms),
                f'{item.progress}%',
                item.state,
                item.error or item.output,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(str(item.source) if col == 0 else value)
                self.table.setItem(row, col, cell)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        self.table.blockSignals(False)

        counts = {state: sum(item.state == state for item in self.queue.items)
                  for state in (WAITING, RUNNING, DONE, FAILED, CANCELLED)}
        total = len(self.queue.items)
        self.summary.setText(
            f'{total} tệp · Chờ {counts[WAITING]} · Đang xử lý {counts[RUNNING]} · '
            f'Hoàn tất {counts[DONE]} · Lỗi {counts[FAILED]} · Đã hủy {counts[CANCELLED]} · '
            'cấu hình dùng chung')

        waiting = counts[WAITING]
        if total == 0:
            text = '▶  THÊM SRT ĐỂ BẮT ĐẦU'
        elif waiting == 1:
            text = '▶  TẠO MP3 · 1 TỆP'
        elif waiting > 1:
            text = f'▶  XỬ LÝ HÀNG ĐỢI · {waiting} TỆP'
        else:
            text = '✓  KHÔNG CÒN TỆP ĐANG CHỜ'
        self.window.generate.setText(text)
        self.window.generate.setEnabled(bool(waiting) and not self.window.busy())


def _install_queue_sync(window, unified):
    panel = window.batch_panel
    original_refresh = panel.refresh

    def refresh_and_sync(self, *args):
        original_refresh(*args)
        unified.refresh()

    panel.refresh = MethodType(refresh_and_sync, panel)


def _install_shared_generate(window, unified):
    try:
        window.generate.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass
    window.generate.clicked.connect(unified.start)


def _install_batch_success_report(window, unified):
    base_success = window.success

    def success_multifile(task, result):
        base_success(task, result)
        if task != 'batch':
            return
        unified.refresh()
        done = [item for item in unified.queue.items if item.state == DONE and item.output]
        failed = [item for item in unified.queue.items if item.state == FAILED]
        cancelled = [item for item in unified.queue.items if item.state == CANCELLED]
        if done:
            window.output = done[-1].output
            window.open_folder.setEnabled(True)
        lines = [
            f'HÀNG ĐỢI HOÀN TẤT · {len(done)} MP3 · {len(failed)} lỗi · {len(cancelled)} đã hủy',
            'Tất cả tệp được xử lý bằng cùng cấu hình tại thời điểm bấm bắt đầu.',
        ]
        for item in unified.queue.items:
            extra = ''
            if item.report:
                extra = (f" · SFX {item.report.get('sfx_mixed', 0)}/"
                         f"{item.report.get('sfx_planned', 0)}"
                         f" · rejected {item.report.get('sfx_rejected', 0)}")
            target = item.error or item.output or '—'
            lines.append(f'{item.state}: {item.source.name} → {target}{extra}')
        window.report.setPlainText('\n'.join(lines))
        window.status.setText(
            f'HOÀN TẤT HÀNG ĐỢI · {len(done)} MP3 · {len(failed)} lỗi · {len(cancelled)} đã hủy')

    window.success = success_multifile


def install_multifile_workspace(window):
    """Merge the legacy Batch tab into the first tab and enforce shared options."""
    file_group = next((g for g in window.findChildren(QGroupBox)
                       if g.title().startswith('①')), None)
    if file_group is None:
        raise RuntimeError('Không tìm thấy vùng chọn SRT để tích hợp hàng đợi.')

    # The old queue object/recovery logic stays alive, but its separate tab is removed.
    old_index = window.tabs.indexOf(window.batch_panel)
    if old_index >= 0:
        window.tabs.removeTab(old_index)
    window.tabs.setTabText(0, 'Tệp / Nghe thử · 1 hoặc nhiều')
    file_group.setTitle('①  Tệp phụ đề SRT · 1 hoặc nhiều tệp')

    subtitle = window.findChild(QLabel, 'appSubtitle')
    if subtitle is not None:
        subtitle.setText('Tiếng Anh (Mỹ / Anh) / Tiếng Nhật · 1 hoặc nhiều SRT · mỗi SRT → 1 MP3 · dùng chung tùy chọn')

    unified = UnifiedFilePanel(window)
    window.multi_file_panel = unified
    file_group.layout().addWidget(unified)

    # Keep the line edit as the active file pointer used by Preview/Smart Fit/SFX.
    window.file.setReadOnly(True)
    window.file.setPlaceholderText('Tệp đang chọn để nghe thử / Smart Fit')
    for button in file_group.findChildren(QPushButton):
        if button.text() == 'Chọn tệp':
            try:
                button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            button.setText('+ Thêm tệp')
            button.clicked.connect(unified.add_files)
            button.hide()  # unified toolbar already contains the same action
            break

    _install_queue_sync(window, unified)
    _install_shared_generate(window, unified)
    _install_batch_success_report(window, unified)

    controls = [unified.add_files_button, unified.add_folder_button, unified.remove_button,
                unified.clear_done_button, unified.retry_button, unified.destination,
                unified.output_button]
    window.edit_controls.extend(controls)

    window._multi_drop_filter = _DropFilter(unified)
    window.installEventFilter(window._multi_drop_filter)

    unified.refresh()
    if unified.queue.items:
        unified.table.selectRow(0)
        unified.activate_selected()
    else:
        window.file_info.setText('Chưa chọn tệp · có thể thêm một hoặc nhiều SRT')
    window.status.setText('Sẵn sàng · chọn 1 hoặc nhiều SRT · mọi tùy chọn dùng chung cho hàng đợi')
    return window
