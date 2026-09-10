import logging
import tempfile
import threading
import traceback
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QScrollArea, QGroupBox)
from .backend import Backend, EN_VOICES, JA_VOICES, PREVIEW
from .render import render, Settings
from .paths import workspace
from .audio import Cancelled, write_wav
from .effects import EMOTIONS, EFFECTS, LEVELS
from .preview import PreviewCache
from .timeline import read_srt, slots_for, RATE
from . import __version__

class Worker(QThread):
    progress = Signal(int, int, str)
    success = Signal(object)
    error = Signal(str, str)
    cancelled = Signal()

    def __init__(self, backend, task, params, preview_cache):
        super().__init__()
        self.backend, self.task, self.params = backend, task, params
        self.preview_cache = preview_cache
        self.cancel = threading.Event()

    def run(self):
        try:
            if self.task == 'render':
                result = render(**self.params, backend=self.backend, cancel=self.cancel,
                                progress=self.progress.emit)
            elif self.task == 'preview':
                result = self.preview_cache.get(**self.params, backend=self.backend, cancel=self.cancel,
                    progress=lambda msg: self.progress.emit(0, 1, msg))
            else:
                from .diagnostics import diagnose
                result = diagnose(self.backend, self.cancel,
                    lambda msg: self.progress.emit(0, 1, msg))
            self.success.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            logging.exception('Task failed')
            self.error.emit(str(exc), traceback.format_exc())

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SRT Voice Studio ' + __version__)
        self.setMinimumSize(720, 720)
        self.resize(840, 900)
        self.setAcceptDrops(True)
        self.backend = Backend()
        self.worker = None
        self.output = None
        self.preview_temp = None
        self.preview_cache = PreviewCache()
        self.captions = []
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.playback_status)
        self.player.errorOccurred.connect(lambda *_: self.status.setText('Không phát được preview: ' + self.player.errorString()))
        self.setStyleSheet('''
            QMainWindow, QWidget { background: #101826; color: #e8eef8; font-size: 14px; }
            QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit { background: #1e2a3d;
                border: 1px solid #3a4b66; border-radius: 6px; padding: 8px; }
            QPushButton { background: #263b55; border: 1px solid #46617c; padding: 10px; border-radius: 6px; }
            QPushButton:hover { background: #325271; } QPushButton:disabled { color: #738094; }
            QPushButton#generate { background: #246adb; font-size: 18px; font-weight: bold; padding: 16px; }
            QProgressBar { border: 1px solid #3a4b66; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background: #30b6a5; }
        ''')
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 12, 18, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel('SRT Voice Studio ' + __version__)
        title.setStyleSheet('font-size: 29px; font-weight: bold;')
        layout.addWidget(title)
        layout.addWidget(QLabel('Offline voices • English US / Japanese • One MP3'))
        self.file = QLineEdit()
        self.file.setPlaceholderText('Kéo file .srt vào đây hoặc bấm Browse')
        browse = QPushButton('Browse')
        browse.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.file)
        row.addWidget(browse)
        layout.addLayout(row)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItems(['English US', 'Japanese'])
        self.voice = QComboBox()
        self.preview_text = QLineEdit()
        self.language.currentTextChanged.connect(self.language_changed)
        form.addRow('Language', self.language)
        form.addRow('Voice', self.voice)
        layout.addLayout(form)
        style = QGroupBox('VOICE STYLE')
        style_form = QFormLayout(style)
        def combo(items, default=None):
            box = QComboBox()
            box.addItems(list(items))
            if default:
                box.setCurrentText(default)
            return box
        self.emotion_mode = combo(['Manual', 'Auto'])
        self.emotion = combo(EMOTIONS)
        self.intensity = combo(LEVELS, 'Medium')
        self.effect = combo(EFFECTS)
        self.strength = combo(LEVELS, 'Medium')
        for label, control in [('Emotion Mode',self.emotion_mode),('Emotion / Performance',self.emotion),
                ('Emotion Intensity',self.intensity),('Voice Effect',self.effect),('Effect Strength',self.strength)]:
            style_form.addRow(label,control)
        note = QLabel('Performance presets dùng DSP local. Whisper-like là mô phỏng bằng DSP.')
        note.setWordWrap(True)
        style_form.addRow(note)
        layout.addWidget(style)
        preview_group = QGroupBox('VOICE PREVIEW')
        preview_form = QFormLayout(preview_group)
        self.caption_select = QComboBox()
        self.caption_select.addItem('Custom text • chưa chọn caption', None)
        preview_form.addRow('Preview Caption', self.caption_select)
        preview_form.addRow('Preview Text', self.preview_text)
        self.preview_text.setMaxLength(4000)
        self.preview_buttons = []
        preview_row = QHBoxLayout()
        for stage, label in [('A','▶ A Original'),('B','▶ B Processed'),('C','▶ C Final Timeline')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, stage=stage: self.preview_voice(stage))
            self.preview_buttons.append(button)
            preview_row.addWidget(button)
        preview_form.addRow(preview_row)
        self.preview_details = QLabel('A: —    B: —    C: —')
        self.preview_details.setWordWrap(True)
        self.preview_details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        preview_form.addRow(self.preview_details)
        layout.addWidget(preview_group)
        timeline_group = QGroupBox('STRICT SRT TIMELINE')
        form = QFormLayout(timeline_group)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(1.0, 1.2)
        self.speed.setSingleStep(0.01)
        self.speed.setSuffix('x')
        self.speed.setValue(1.0)
        form.addRow('Speed', self.speed)
        self.gap = QComboBox()
        for ms in (0, 50, 100, 150, 200):
            self.gap.addItem(f'{ms/1000:.2f} sec', ms)
        self.gap.setCurrentIndex(2)
        form.addRow('Minimum Gap', self.gap)
        self.overflow = QComboBox()
        self.overflow.addItems(['Safe Trim', 'Stop and Report'])
        self.overflow.setToolTip('Safe Trim có thể cắt mất từ cuối câu quá dài. Stop and Report dừng để bạn sửa SRT.')
        form.addRow('Overflow', self.overflow)
        form.addRow('Compute', QLabel('CPU • Không cần CUDA'))
        form.addRow('Timeline mode', QLabel('STRICT SRT TIMELINE'))
        layout.addWidget(timeline_group)
        for text in ('Lock SRT Start Times', 'Never Overlap Voices', 'Delete Temporary Audio'):
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            layout.addWidget(checkbox)
        self.adaptive = QCheckBox('Adaptive Speed (1.00–1.15x; tối đa 1.20x)')
        self.adaptive.setChecked(True)
        self.normalize = QCheckBox('Normalize Loudness')
        self.normalize.setChecked(True)
        layout.addWidget(self.adaptive)
        layout.addWidget(self.normalize)
        layout.addStretch()
        layout = outer
        self.generate = QPushButton('GENERATE MP3')
        self.generate.setObjectName('generate')
        self.generate.clicked.connect(self.generate_mp3)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_job)
        row = QHBoxLayout()
        row.addWidget(self.generate, 3)
        row.addWidget(self.cancel_button, 1)
        layout.addLayout(row)
        self.bar = QProgressBar()
        layout.addWidget(self.bar)
        self.status = QLabel('Sẵn sàng • Chọn file SRT để bắt đầu')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(145)
        layout.addWidget(self.report)
        self.open_folder = QPushButton('Open Output Folder')
        self.open_folder.setEnabled(False)
        self.open_folder.clicked.connect(self.open_output)
        layout.addWidget(self.open_folder)
        self.diagnostic_action = self.menuBar().addMenu('Help').addAction('Run Diagnostics')
        self.diagnostic_action.triggered.connect(lambda: self.start('diagnose', {}))
        self.edit_controls = [browse, self.file, self.language, self.voice, self.preview_text,
            self.speed, self.gap, self.overflow, self.adaptive, self.normalize,
            self.emotion_mode, self.emotion, self.intensity, self.effect, self.strength, self.caption_select]
        self.file.editingFinished.connect(self.load_captions)
        self.caption_select.currentIndexChanged.connect(self.caption_changed)
        self.preview_text.textEdited.connect(self.custom_text_edited)
        self.voice.currentTextChanged.connect(self.invalidate_base)
        for control in (self.emotion_mode,self.emotion,self.intensity,self.effect,self.strength,self.gap,self.overflow):
            control.currentIndexChanged.connect(self.style_changed)
        self.speed.valueChanged.connect(self.style_changed)
        self.adaptive.toggled.connect(self.style_changed)
        self.normalize.toggled.connect(self.style_changed)
        self.language_changed('English US')
        self.refresh_controls()

    def language_changed(self, language):
        self.voice.clear()
        self.voice.addItems(JA_VOICES if language == 'Japanese' else EN_VOICES)
        if self.caption_select.currentData() is None:
            self.preview_text.setText(PREVIEW[language])
        self.invalidate_base()

    def browse(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Chọn SRT', '', 'SRT (*.srt)')
        if file:
            self.file.setText(file)
            self.load_captions()

    def dragEnterEvent(self, event):
        if not self.busy() and event.mimeData().hasUrls():
            if any(u.isLocalFile() and u.toLocalFile().lower().endswith('.srt') for u in event.mimeData().urls()):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.busy():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.srt'):
                    self.file.setText(url.toLocalFile())
                    self.load_captions()
                    event.acceptProposedAction()
                    break

    def busy(self):
        return self.worker is not None and self.worker.isRunning()

    def start(self, task, params):
        if self.busy():
            return
        self.stop_preview()
        self.report.clear()
        self.status.setText('Đang chuẩn bị…')
        self.bar.setValue(0)
        for control in self.edit_controls + [self.generate] + self.preview_buttons:
            control.setEnabled(False)
        self.diagnostic_action.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = Worker(self.backend, task, params, self.preview_cache)
        self.worker.progress.connect(self.progress)
        self.worker.success.connect(lambda result: self.success(task, result))
        self.worker.error.connect(self.show_error)
        self.worker.cancelled.connect(lambda: self.status.setText('Đã hủy. Không xuất MP3 mới.'))
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        for control in self.edit_controls + [self.generate] + self.preview_buttons:
            control.setEnabled(True)
        self.diagnostic_action.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.refresh_controls()

    def progress(self, done, total, message):
        self.bar.setValue(int(done * 100 / max(total, 1)))
        self.status.setText(message)

    def settings(self):
        return Settings(language=self.language.currentText(), voice=self.voice.currentText(),
            speed=self.speed.value(), gap_ms=self.gap.currentData(), adaptive=self.adaptive.isChecked(),
            loudness=self.normalize.isChecked(), overflow=self.overflow.currentText(),
            emotion_mode=self.emotion_mode.currentText(), emotion=self.emotion.currentText(),
            intensity=self.intensity.currentText(), effect=self.effect.currentText(), strength=self.strength.currentText())

    def refresh_controls(self):
        idle = not self.busy()
        self.emotion.setEnabled(idle and self.emotion_mode.currentText() == 'Manual')
        self.intensity.setEnabled(idle and self.emotion_mode.currentText() == 'Manual' and self.emotion.currentText() != 'Natural')
        self.strength.setEnabled(idle and self.effect.currentText() != 'None')
        self.preview_buttons[2].setEnabled(idle and self.caption_select.currentData() is not None)

    def invalidate_base(self, *_):
        if self.busy():
            return
        self.stop_preview()
        self.preview_cache.clear()
        self.preview_details.setText('A: —    B: —    C: —')

    def style_changed(self, *_):
        self.stop_preview()
        a = self.preview_cache.base
        self.preview_details.setText(f'A: {len(a)/self.preview_cache.rate:.3f} s    B: —    C: —' if a is not None else 'A: —    B: —    C: —')
        self.refresh_controls()
        self.show_slot()

    def custom_text_edited(self, *_):
        self.caption_select.blockSignals(True)
        self.caption_select.setCurrentIndex(0)
        self.caption_select.blockSignals(False)
        self.invalidate_base()
        self.refresh_controls()

    def load_captions(self):
        if self.busy():
            return
        self.captions = []
        self.caption_select.blockSignals(True)
        self.caption_select.clear()
        self.caption_select.addItem('Custom text • chọn caption để nghe C', None)
        try:
            if self.file.text().strip():
                self.captions = read_srt(Path(self.file.text().strip()))
                slots_for(self.captions, self.gap.currentData())
                for i, caption in enumerate(self.captions):
                    self.caption_select.addItem(f'#{caption.index} • {caption.text[:75]}', i)
        except Exception as exc:
            self.status.setText(str(exc))
        finally:
            self.caption_select.blockSignals(False)
        self.invalidate_base()
        self.refresh_controls()

    def caption_changed(self, *_):
        index = self.caption_select.currentData()
        if index is not None:
            self.preview_text.setText(self.captions[index].text)
        self.invalidate_base()
        self.refresh_controls()
        self.show_slot()

    def selected_slot(self):
        index = self.caption_select.currentData()
        if index is None:
            return None
        return slots_for(self.captions, self.gap.currentData())[index]

    @staticmethod
    def timestamp(samples):
        ms = round(samples/RATE*1000)
        return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'

    def show_slot(self):
        try:
            slot = self.selected_slot()
            if slot:
                self.preview_details.setText(f'Caption #{slot.caption.index} • Start {self.timestamp(slot.start)} • '
                    f'Allowed End {self.timestamp(slot.end)} • Available {(slot.end-slot.start)/RATE:.3f} s\n'
                    + self.preview_details.text().split('\n')[-1])
        except Exception as exc:
            self.preview_details.setText(str(exc))
            self.preview_buttons[2].setEnabled(False)

    def preview_voice(self, stage='A'):
        if not self.preview_text.text().strip():
            return
        try:
            slot = self.selected_slot()
            self.start('preview', dict(stage=stage, text=self.preview_text.text(), settings=self.settings(), slot=slot))
        except Exception as exc:
            self.show_error(str(exc), traceback.format_exc())

    def generate_mp3(self):
        file = Path(self.file.text().strip())
        if not file.is_file() or file.suffix.lower() != '.srt':
            QMessageBox.information(self, 'Chọn SRT', 'Hãy chọn một file .srt hợp lệ.')
            return
        from .timeline import read_srt, slots_for
        try:
            slots_for(read_srt(file), self.gap.currentData())
        except Exception as exc:
            self.show_error(str(exc), traceback.format_exc())
            return
        output, _ = QFileDialog.getSaveFileName(self, 'Lưu MP3', str(file.with_name(file.stem+'_Voice.mp3')), 'MP3 (*.mp3)')
        if not output:
            return
        if not output.lower().endswith('.mp3'):
            output += '.mp3'
        settings = self.settings()
        self.start('render', dict(srt=file, output=output, settings=settings))

    def success(self, task, result):
        self.bar.setValue(100)
        if task == 'preview':
            self.preview_temp = tempfile.TemporaryDirectory(prefix='job-', dir=workspace(), ignore_cleanup_errors=True)
            path = Path(self.preview_temp.name)/'preview.wav'
            write_wav(path, result.samples, result.rate)
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            self.player.play()
            self.status.setText(f'Đang phát {result.stage} • {result.details["emotion"]} • {result.details["effect"]}')
            d = result.details
            seconds = lambda value: '—' if value is None else f'{value:.3f} s'
            detail = f'A: {seconds(d["original_seconds"])}    B: {seconds(d.get("processed_seconds"))}    C: {seconds(d.get("final_seconds"))}'
            if 'speed' in d:
                detail += f'\nFinal Speed: {d["speed"]:.3f}x • Trim: {"Yes" if d["trimmed"] else "No"} • Overlap: {d["overlaps"]}'
            if 'caption' in d:
                detail = (f'Caption #{d["caption"]} • Start {self.timestamp(d["start_sample"])} • '
                    f'Allowed End {self.timestamp(d["allowed_end"])} • Available {d["available_seconds"]:.3f} s\n') + detail
            self.preview_details.setText(detail)
        elif task == 'diagnose':
            self.report.setPlainText('\n'.join(result))
            self.status.setText('Đã kiểm tra • Xem kết quả bên dưới')
        else:
            self.stop_preview()
            self.preview_cache.clear()
            self.preview_details.setText('A: —    B: —    C: —')
            self.output = result['output']
            self.open_folder.setEnabled(True)
            trimmed = result['safely_trimmed']
            self.status.setText('SUCCESS' + (f' • {trimmed} câu đã Safe Trim, cần nghe kiểm tra' if trimmed else ''))
            self.report.setPlainText(f"Final MP3: {self.output}\nDuration (master): {result['duration']}\n"
                f"{result['total']} captions • {result['valid']} valid\n"
                f"Emotion: {result['emotion_mode']} / {result['emotion']} • FX: {result['effect']} / {result['strength']}\n"
                f"{result['speed_adjusted']} speed adjusted • {trimmed} safely trimmed\n"
                f"{result['overlaps']} overlaps • TIMELINE VALID")

    def cancel_job(self):
        if self.busy():
            self.worker.cancel.set()
            self.status.setText('Đang hủy… chờ lượt suy luận hiện tại kết thúc.')

    def show_error(self, message, details):
        self.status.setText('Không hoàn tất • ' + message)
        box = QMessageBox(QMessageBox.Critical, 'SRT Voice Studio', message, parent=self)
        box.setDetailedText(details)
        box.exec()

    def playback_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.stop_preview()

    def stop_preview(self):
        self.player.stop()
        self.player.setSource(QUrl())
        if self.preview_temp:
            self.preview_temp.cleanup()
            self.preview_temp = None

    def open_output(self):
        if self.output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.output).parent)))

    def closeEvent(self, event):
        if self.busy():
            self.cancel_job()
            event.ignore()
            self.status.setText('Đang hủy. Hãy đóng cửa sổ sau khi tác vụ dừng.')
        else:
            self.stop_preview()
            self.preview_cache.clear()
            event.accept()
