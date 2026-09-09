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
    QTextEdit, QFileDialog, QMessageBox)
from .backend import Backend, EN_VOICES, JA_VOICES, PREVIEW
from .render import render, Settings
from .paths import workspace
from .audio import Cancelled, write_wav

class Worker(QThread):
    progress = Signal(int, int, str)
    success = Signal(object)
    error = Signal(str, str)
    cancelled = Signal()

    def __init__(self, backend, task, params):
        super().__init__()
        self.backend, self.task, self.params = backend, task, params
        self.cancel = threading.Event()

    def run(self):
        try:
            if self.task == 'render':
                result = render(**self.params, backend=self.backend, cancel=self.cancel,
                                progress=self.progress.emit)
            elif self.task == 'preview':
                samples, rate = self.backend.synthesize(**self.params, cancel=self.cancel,
                    progress=lambda msg: self.progress.emit(0, 1, msg))
                result = (samples, rate)
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
        self.setWindowTitle('SRT Voice Studio')
        self.setMinimumSize(700, 760)
        self.setAcceptDrops(True)
        self.backend = Backend()
        self.worker = None
        self.output = None
        self.preview_temp = None
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
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 20, 28, 20)
        title = QLabel('SRT Voice Studio')
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
        form.addRow('Preview text', self.preview_text)
        self.preview = QPushButton('▶ Preview Voice')
        self.preview.clicked.connect(self.preview_voice)
        form.addRow('', self.preview)
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
        layout.addLayout(form)
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
            self.speed, self.gap, self.overflow, self.adaptive, self.normalize]
        self.language_changed('English US')

    def language_changed(self, language):
        self.voice.clear()
        self.voice.addItems(JA_VOICES if language == 'Japanese' else EN_VOICES)
        self.preview_text.setText(PREVIEW[language])

    def browse(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Chọn SRT', '', 'SRT (*.srt)')
        if file:
            self.file.setText(file)

    def dragEnterEvent(self, event):
        if not self.busy() and event.mimeData().hasUrls():
            if any(u.isLocalFile() and u.toLocalFile().lower().endswith('.srt') for u in event.mimeData().urls()):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.busy():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.srt'):
                    self.file.setText(url.toLocalFile())
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
        for control in self.edit_controls + [self.generate, self.preview]:
            control.setEnabled(False)
        self.diagnostic_action.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = Worker(self.backend, task, params)
        self.worker.progress.connect(self.progress)
        self.worker.success.connect(lambda result: self.success(task, result))
        self.worker.error.connect(self.show_error)
        self.worker.cancelled.connect(lambda: self.status.setText('Đã hủy. Không xuất MP3 mới.'))
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        for control in self.edit_controls + [self.generate, self.preview]:
            control.setEnabled(True)
        self.diagnostic_action.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def progress(self, done, total, message):
        self.bar.setValue(int(done * 100 / max(total, 1)))
        self.status.setText(message)

    def preview_voice(self):
        if not self.preview_text.text().strip():
            return
        self.start('preview', dict(text=self.preview_text.text(), language=self.language.currentText(),
                                   voice=self.voice.currentText()))

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
        settings = Settings(self.language.currentText(), self.voice.currentText(), self.speed.value(),
                            self.gap.currentData(), self.adaptive.isChecked(), self.normalize.isChecked(),
                            self.overflow.currentText())
        self.start('render', dict(srt=file, output=output, settings=settings))

    def success(self, task, result):
        self.bar.setValue(100)
        if task == 'preview':
            self.preview_temp = tempfile.TemporaryDirectory(prefix='job-', dir=workspace(), ignore_cleanup_errors=True)
            path = Path(self.preview_temp.name)/'preview.wav'
            write_wav(path, *result)
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            self.player.play()
            self.status.setText('Đang phát preview')
        elif task == 'diagnose':
            self.report.setPlainText('\n'.join(result))
            self.status.setText('Đã kiểm tra • Xem kết quả bên dưới')
        else:
            self.output = result['output']
            self.open_folder.setEnabled(True)
            trimmed = result['safely_trimmed']
            self.status.setText('SUCCESS' + (f' • {trimmed} câu đã Safe Trim, cần nghe kiểm tra' if trimmed else ''))
            self.report.setPlainText(f"Final MP3: {self.output}\nDuration (master): {result['duration']}\n"
                f"{result['total']} captions • {result['valid']} valid\n"
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
            event.accept()
