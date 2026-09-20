"""Visual per-file quality-control dashboard for SRT Voice Studio 1.7."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QAbstractItemView,
)


class QualityPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)

        title = QLabel("QC 1.7 · kiểm tra tự động sau render")
        title.setStyleSheet("font-size:17px;font-weight:650;")
        layout.addWidget(title)

        note = QLabel(
            "QC chỉ báo các lỗi đo được: overlap, clipping, DC, caption bị cắt, "
            "voice quá ngắn, khoảng lặng dài và SFX bị loại. PASS không thay thế việc nghe kiểm tra nội dung/phát âm.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Tệp", "QC", "Vấn đề", "Trim", "Gap >0.8s", "SFX", "Cache", "Peak"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.open_workspace = QPushButton("Mở file trong Workspace")
        self.refresh_button = QPushButton("Làm mới QC")
        actions.addWidget(self.open_workspace)
        actions.addWidget(self.refresh_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(150)
        layout.addWidget(self.details)

        self.summary = QLabel("Chưa có kết quả render.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table.itemSelectionChanged.connect(self.show_selected)
        self.open_workspace.clicked.connect(self.open_in_workspace)
        self.refresh_button.clicked.connect(self.refresh)

    def _items(self):
        return list(self.window.multi_file_panel.queue.items)

    def refresh(self):
        items = self._items()
        current = self.table.currentRow()
        self.table.blockSignals(True)
        self.table.setRowCount(len(items))
        counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "—": 0}

        for row, item in enumerate(items):
            report = item.report if isinstance(item.report, dict) else {}
            quality = report.get("quality") if isinstance(report.get("quality"), dict) else {}
            status = str(quality.get("status") or ("—" if not report else "WARN"))
            if status not in counts:
                status = "WARN"
            counts[status] += 1

            issues = list(quality.get("issues") or [])
            metrics = report.get("master_metrics") if isinstance(report.get("master_metrics"), dict) else {}
            planned = int(report.get("sfx_planned", 0) or 0)
            mixed = int(report.get("sfx_mixed", 0) or 0)
            rejected = int(report.get("sfx_rejected", 0) or 0)
            hits = int(report.get("cache_hits", 0) or 0)
            misses = int(report.get("cache_misses", 0) or 0)
            peak = metrics.get("peak")
            values = [
                item.source.name,
                status,
                str(len(issues)) if quality else "—",
                str(report.get("safely_trimmed", "—")) if report else "—",
                str(report.get("transitions_over_08", "—")) if report else "—",
                (f"{mixed}/{planned} · loại {rejected}" if report.get("auto_sfx") else "Tắt") if report else "—",
                f"{hits} hit / {misses} miss" if report else "—",
                f"{float(peak):.3f}" if isinstance(peak, (float, int)) else "—",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setToolTip(str(item.source))
                self.table.setItem(row, col, cell)

        self.table.blockSignals(False)
        if items:
            self.table.selectRow(min(max(current, 0), len(items) - 1))
        else:
            self.details.clear()
        self.summary.setText(
            f"{len(items)} tệp · PASS {counts['PASS']} · WARN {counts['WARN']} · "
            f"FAIL {counts['FAIL']} · chưa có QC {counts['—']}")
        self.show_selected()

    def show_selected(self):
        row = self.table.currentRow()
        items = self._items()
        if not (0 <= row < len(items)):
            self.details.setPlainText("Chưa chọn kết quả QC.")
            return
        item = items[row]
        report = item.report if isinstance(item.report, dict) else {}
        if not report:
            self.details.setPlainText(
                f"{item.source.name}\nChưa có kết quả render/QC cho file này.")
            return
        quality = report.get("quality") if isinstance(report.get("quality"), dict) else {}
        issues = list(quality.get("issues") or [])
        lines = [
            f"{item.source.name}",
            f"QC: {quality.get('status', 'WARN')}",
            f"Output: {item.output or '—'}",
            f"Caption: {report.get('total', '—')} · trim {report.get('safely_trimmed', 0)} · "
            f"gap >0.8s {report.get('transitions_over_08', 0)}",
            f"Smart Fit 3: {report.get('smart_fit3_neighbor_adjusted', 0)} caption làm mượt",
            f"Render Cache: {report.get('cache_hits', 0)} hit · {report.get('cache_misses', 0)} miss",
            f"SFX: {report.get('sfx_mixed', 0)}/{report.get('sfx_planned', 0)} mixed · "
            f"{report.get('sfx_rejected', 0)} rejected",
        ]
        metrics = report.get("master_metrics") if isinstance(report.get("master_metrics"), dict) else {}
        if metrics:
            lines.append(
                f"Audio master: peak {float(metrics.get('peak', 0.0)):.3f} · "
                f"RMS {float(metrics.get('rms', 0.0)):.4f} · "
                f"DC {float(metrics.get('dc', 0.0)):.5f} · "
                f"clipping {int(metrics.get('clipping_samples', 0) or 0)}")
        if issues:
            lines.append("")
            lines.append("Vấn đề:")
            for issue in issues:
                lines.append("• " + str(issue.get("message") or issue.get("code") or "Issue"))
        else:
            lines.append("")
            lines.append("Không phát hiện lỗi đo được.")
        self.details.setPlainText("\n".join(lines))

    def open_in_workspace(self):
        row = self.table.currentRow()
        items = self._items()
        if not (0 <= row < len(items)):
            return
        target = items[row]
        try:
            index = self.window.multi_file_panel.queue.items.index(target)
        except ValueError:
            return
        self.window.tabs.setCurrentIndex(0)
        self.window.multi_file_panel.table.selectRow(index)
        self.window.multi_file_panel.activate_selected()
