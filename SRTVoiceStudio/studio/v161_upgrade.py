"""SRT Voice Studio 1.6.1 UI additions for Auto SFX audibility."""
from __future__ import annotations

from PySide6.QtCore import QBuffer, QIODevice, QByteArray
from PySide6.QtWidgets import QHBoxLayout, QLabel, QComboBox, QPushButton

from .audio import wav_bytes
from .timeline import RATE
from .sfx_161 import apply_patch, speaker_band_ratio

# Ensure the patched synthesis/mixer is installed even in tests that import this
# module directly instead of entering through main.py.
sfx = apply_patch()
from .v16_upgrade import enhance_window_v16


def format_sfx_result(result: dict) -> tuple[str, str]:
    """Return compact status and detailed human-readable SFX QA summary."""
    if not bool(result.get('auto_sfx', False)):
        return 'Auto SFX: TẮT', 'Auto SFX: TẮT · MP3 chỉ có voice.'
    planned = int(result.get('sfx_planned', 0))
    mixed = int(result.get('sfx_mixed', 0))
    rejected = int(result.get('sfx_rejected', 0))
    status = f'Auto SFX: {mixed}/{planned} đã trộn'
    if rejected:
        status += f' · {rejected} bị loại'
    lines = [
        f'Auto SFX 1.6.1: planned {planned} · mixed {mixed} · rejected {rejected}',
        f'Mật độ: {result.get("sfx_density", "—")} · Mức: {result.get("sfx_strength", "—")}',
    ]
    events = list(result.get('sfx_events') or [])
    if not events and planned:
        lines.append('Không có báo cáo chi tiết SFX dù có cue được lên kế hoạch.')
    for event in events:
        caption = event.get('caption', '?')
        label = event.get('label') or event.get('kind', 'SFX')
        if event.get('mixed'):
            rel = event.get('relative_rms')
            band = event.get('speaker_band_ratio')
            gain = event.get('gain')
            extra = []
            if gain is not None: extra.append(f'gain {float(gain):.3f}')
            if rel is not None: extra.append(f'SFX/voice RMS {float(rel):.2f}×')
            if band is not None: extra.append(f'speaker-band {float(band)*100:.1f}%')
            lines.append(f'  ✓ Câu {caption}: {label}' + (f' · {" · ".join(extra)}' if extra else ''))
        else:
            lines.append(f'  ✗ Câu {caption}: {label} · loại: {event.get("reason", "unknown") }')
    return status, '\n'.join(lines)


def _install_sfx_preview(window):
    panel = window.sfx_panel
    layout = panel.layout()

    row = QHBoxLayout()
    row.addWidget(QLabel('Nghe riêng SFX'))
    panel.preview_kind = QComboBox()
    for kind, label in sfx.KIND_LABELS.items():
        panel.preview_kind.addItem(label, kind)
    panel.preview_button = QPushButton('▶ Nghe thử SFX')
    panel.preview_note = QLabel('Nghe riêng để kiểm tra chất SFX; mức khi mix vẫn tự theo voice + headroom.')
    panel.preview_note.setWordWrap(True)
    row.addWidget(panel.preview_kind, 1)
    row.addWidget(panel.preview_button)
    row.addWidget(panel.preview_note, 2)
    layout.insertLayout(4, row)

    def preview_sfx():
        if window.busy():
            return
        kind = str(panel.preview_kind.currentData() or 'chime')
        samples = sfx.synthesize_sfx(kind, 'manual-preview', RATE)
        qa = sfx.inspect_sfx(samples, RATE)
        if not qa['passed']:
            panel.status.setText('Không phát SFX: QA không đạt · ' + ', '.join(qa['reasons']))
            return
        # Solo preview is intentionally louder than the in-mix version so the
        # user can judge the sound itself. It never changes render settings.
        preview_gain = {'Light': .58, 'Medium': .74, 'Strong': .88}.get(
            str(panel.strength.currentData() or 'Medium'), .74)
        audio = (samples * preview_gain).astype('float32')
        window.stop_preview()
        window.preview_device = QBuffer(window)
        window.preview_device.setData(QByteArray(wav_bytes(audio, RATE)))
        window.preview_device.open(QIODevice.ReadOnly)
        window.player.setSourceDevice(window.preview_device)
        window.player.play()
        panel.status.setText(
            f'Đang nghe riêng: {sfx.KIND_LABELS[kind]} · QA PASS · '
            f'speaker-band {speaker_band_ratio(samples)*100:.1f}%')

    panel.preview_button.clicked.connect(preview_sfx)
    window.edit_controls.extend([panel.preview_kind, panel.preview_button])


def _install_render_reporting(window):
    base_success = window.success

    def success_161(task, result):
        base_success(task, result)
        if task != 'render' or not isinstance(result, dict):
            return
        status, details = format_sfx_result(result)
        if bool(result.get('auto_sfx', False)):
            window.status.setText(window.status.text() + ' · ' + status)
        current = window.report.toPlainText().rstrip()
        window.report.setPlainText(current + ('\n\n' if current else '') + details)
        if hasattr(window, 'sfx_panel'):
            window.sfx_panel.status.setText(status + ' · xem báo cáo kết quả bên dưới tab Một tệp / Nghe thử.')

    # Worker.start() resolves self.success dynamically through its lambda, so an
    # instance-level wrapper is sufficient and avoids touching the verified UI.
    window.success = success_161


def enhance_window_v161(window):
    window = enhance_window_v16(window)
    index = window.tabs.indexOf(window.sfx_panel)
    if index >= 0:
        window.tabs.setTabText(index, 'Auto SFX 1.6.1')
    title = window.sfx_panel.layout().itemAt(0).widget()
    if title is not None:
        title.setText('Auto SFX 1.6.1 · rõ hơn trên loa điện thoại/laptop · anti-click · fail-closed QA')
    _install_sfx_preview(window)
    _install_render_reporting(window)
    window.status.setText('Sẵn sàng · 1.6.1: Auto SFX audibility + preview + báo cáo mixed/rejected')
    return window
