"""SRT Voice Studio 1.6 workflow additions: conservative automatic SFX."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView)

from .v15_upgrade import enhance_window, apply_settings
from .preferences import read as read_preferences, load_settings
from .timeline import read_srt, display_time
from .sfx import DENSITIES, STRENGTHS, KIND_LABELS, plan_sfx
from . import v15_core


DENSITY_LABELS = {
    'Sparse': 'Thưa · chỉ cue mạnh',
    'Balanced': 'Cân bằng · khuyên dùng',
    'Energetic': 'Nhiều · TikTok năng lượng cao',
}
STRENGTH_LABELS = {
    'Light': 'Nhẹ · nằm sâu dưới voice',
    'Medium': 'Vừa · khuyên dùng',
    'Strong': 'Rõ · vẫn khóa headroom',
}


class AutoSfxPanel(QWidget):
    def __init__(self, window):
        super().__init__(); self.window = window
        layout = QVBoxLayout(self)
        title = QLabel('Auto SFX 1.6 · procedural 48 kHz · anti-click · fail-closed artifact guard')
        title.setStyleSheet('font-size:17px;font-weight:650;'); layout.addWidget(title)
        note = QLabel('SFX được tạo trực tiếp trong app, không time-stretch/resample. Hiệu ứng không đạt kiểm tra xè/rẹt/DC/clipping/high-frequency sẽ bị bỏ, voice vẫn xuất bình thường.')
        note.setWordWrap(True); layout.addWidget(note)

        row = QHBoxLayout()
        self.enabled = QCheckBox('Dùng Auto SFX · bật / tắt thủ công')
        self.enabled.setToolTip('Chỉ khi bạn tự bật nút này app mới chèn SFX. Preset không được tự ý thay đổi trạng thái SFX.')
        self.density = QComboBox(); self.strength = QComboBox()
        for key in DENSITIES: self.density.addItem(DENSITY_LABELS[key], key)
        for key in STRENGTHS: self.strength.addItem(STRENGTH_LABELS[key], key)
        row.addWidget(self.enabled); row.addWidget(QLabel('Mật độ')); row.addWidget(self.density, 1)
        row.addWidget(QLabel('Mức')); row.addWidget(self.strength, 1); layout.addLayout(row)

        actions = QHBoxLayout()
        self.safe = QPushButton('Dùng cấu hình an toàn')
        self.analyze = QPushButton('Phân tích SFX cho SRT hiện tại')
        actions.addWidget(self.safe); actions.addWidget(self.analyze); actions.addStretch(); layout.addLayout(actions)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Câu', 'Thời điểm', 'SFX', 'Điểm cue', 'Từ/cue kích hoạt'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.status = QLabel('Auto SFX: TẮT · MP3 chỉ có voice, không chèn hiệu ứng âm thanh.')
        self.status.setWordWrap(True); layout.addWidget(self.status)

        saved = read_preferences().get('settings', {})
        if not isinstance(saved, dict): saved = {}
        self.enabled.setChecked(bool(saved.get('auto_sfx', False)))
        self._set_combo(self.density, str(saved.get('sfx_density', 'Balanced')))
        self._set_combo(self.strength, str(saved.get('sfx_strength', 'Medium')))
        self.safe.clicked.connect(self.apply_safe)
        self.analyze.clicked.connect(self.refresh)
        self.enabled.toggled.connect(self._changed)
        self.density.currentIndexChanged.connect(self._changed)
        self.strength.currentIndexChanged.connect(self._changed)
        self._changed()

    @staticmethod
    def _set_combo(combo, value):
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def apply_safe(self):
        self.enabled.setChecked(True)
        self._set_combo(self.density, 'Balanced')
        self._set_combo(self.strength, 'Medium')
        self.status.setText('Auto SFX: BẬT · cấu hình an toàn Cân bằng + Mức vừa + artifact guard bắt buộc.')
        self.refresh()

    def _changed(self, *_):
        enabled = self.enabled.isChecked()
        self.density.setEnabled(enabled and not self.window.busy())
        self.strength.setEnabled(enabled and not self.window.busy())
        if enabled:
            self.status.setText('Auto SFX: BẬT · SFX lỗi sẽ bị bỏ thay vì đưa vào MP3.')
        else:
            self.status.setText('Auto SFX: TẮT · MP3 chỉ có voice, không chèn hiệu ứng âm thanh.')

    def refresh(self, *_):
        path = Path(self.window.file.text().strip())
        if not path.is_file():
            self.table.setRowCount(0); self.status.setText('Hãy chọn SRT ở tab Một tệp / Nghe thử trước.'); return
        try:
            captions = read_srt(path)
            events = plan_sfx(captions, self.window.language.currentData(), self.density.currentData())
            self.table.setRowCount(len(events))
            for row, event in enumerate(events):
                values = [str(event.caption_index), display_time(event.start_ms), KIND_LABELS[event.kind],
                          str(event.score), event.reason]
                for col, value in enumerate(values): self.table.setItem(row, col, QTableWidgetItem(value))
            if events:
                prefix = 'Đang BẬT' if self.enabled.isChecked() else 'Đang TẮT · chỉ xem trước kế hoạch'
                self.status.setText(f'Auto SFX {prefix}: dự kiến {len(events)} SFX. Khi render, từng SFX còn phải qua QA âm thanh và headroom guard.')
            else:
                self.status.setText('Không có cue đủ mạnh ở mật độ hiện tại. App sẽ không chèn SFX cưỡng ép.')
        except Exception as exc:
            self.table.setRowCount(0); self.status.setText('Không phân tích được SFX: ' + str(exc))

    def set_busy(self, busy: bool):
        self.enabled.setEnabled(not busy)
        self.safe.setEnabled(not busy)
        self.analyze.setEnabled(not busy)
        self.density.setEnabled(not busy and self.enabled.isChecked())
        self.strength.setEnabled(not busy and self.enabled.isChecked())


def _patch_builtin_presets():
    # Presets may suggest density/strength, but must never silently enable or
    # disable Auto SFX.  The on/off state belongs exclusively to the user toggle.
    values = {
        'JP TikTok Comedy': ('Balanced', 'Medium'),
        'US Reviewer': ('Balanced', 'Medium'),
        'Renovation Calm': ('Sparse', 'Light'),
        'Horror Narration': ('Sparse', 'Light'),
        'Food Challenge': ('Energetic', 'Medium'),
    }
    for name, (density, strength) in values.items():
        if name in v15_core.BUILTIN_PRESETS:
            v15_core.BUILTIN_PRESETS[name].pop('auto_sfx', None)
            v15_core.BUILTIN_PRESETS[name].update(sfx_density=density, sfx_strength=strength)


def _apply_sfx(window, settings):
    if not hasattr(window, 'sfx_panel'): return
    p = window.sfx_panel
    p.enabled.setChecked(bool(getattr(settings, 'auto_sfx', False)))
    p._set_combo(p.density, str(getattr(settings, 'sfx_density', 'Balanced')))
    p._set_combo(p.strength, str(getattr(settings, 'sfx_strength', 'Medium')))
    p._changed()


def _patch_preset_apply(window):
    panel = window.preset_panel
    try: panel.apply.clicked.disconnect()
    except (RuntimeError, TypeError): pass
    def apply_selected():
        name = panel.preset.currentData()
        if not name: return
        # Applying a preset must not silently switch Auto SFX on or off.
        manual_sfx_state = window.sfx_panel.enabled.isChecked()
        settings = v15_core.settings_from_mapping(panel.data[name])
        actual = apply_settings(window, settings)
        _apply_sfx(window, replace(settings, auto_sfx=manual_sfx_state))
        panel.status.setText(f'Đã áp dụng {name}. Auto SFX vẫn giữ {"BẬT" if manual_sfx_state else "TẮT"} theo lựa chọn của bạn.' + (' Giọng preset chưa cài nên đã dùng giọng khả dụng đầu tiên.' if actual.voice != settings.voice else ''))
    panel.apply.clicked.connect(apply_selected)


def _load_sfx(window):
    settings = load_settings(); _apply_sfx(window, settings)


def enhance_window_v16(window):
    """Build on verified 1.5.2 without rewriting its render/UI workflow."""
    window = enhance_window(window)
    _patch_builtin_presets()
    window.sfx_panel = AutoSfxPanel(window)
    window.tabs.addTab(window.sfx_panel, 'Auto SFX 1.6')

    base_settings = window.settings
    def settings_v16():
        return replace(base_settings(), auto_sfx=window.sfx_panel.enabled.isChecked(),
                       sfx_density=str(window.sfx_panel.density.currentData() or 'Balanced'),
                       sfx_strength=str(window.sfx_panel.strength.currentData() or 'Medium'))
    window.settings = settings_v16
    window.edit_controls.extend([window.sfx_panel.enabled, window.sfx_panel.density,
                                 window.sfx_panel.strength, window.sfx_panel.safe,
                                 window.sfx_panel.analyze])
    window.preset_panel.reload()
    _patch_preset_apply(window)

    # Existing config save calls self.settings() dynamically, so 1.6 fields are
    # stored automatically.  Add a post-load sync for the new controls.
    for top in window.menuBar().actions():
        menu = top.menu()
        if menu and top.text() == 'Cấu hình':
            for action in menu.actions():
                if action.text() == 'Nạp cấu hình đã lưu':
                    action.triggered.connect(lambda: _load_sfx(window))
    window.status.setText('Sẵn sàng · 1.6: Auto SFX tùy chọn + Smart Fit 2.0 + Batch + Voice Compare + Preset')
    return window
