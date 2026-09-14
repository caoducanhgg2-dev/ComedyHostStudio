import logging
import tempfile
import threading
import traceback
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QUrl, Qt, QBuffer, QIODevice, QByteArray
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QScrollArea, QGroupBox, QGridLayout, QPlainTextEdit, QTabWidget)
from .backend import Backend, EN_VOICES, JA_VOICES, PREVIEW
from .voice_backends import BackendRouter
from .render import render, Settings
from .paths import workspace
from .audio import Cancelled, wav_bytes
from .effects import EMOTIONS, EFFECTS, LEVELS
from .preview import PreviewCache
from .timeline import read_srt, slots_for, RATE
from . import __version__
from . import ui_text as vi

class Worker(QThread):
    progress = Signal(int, int, str)
    success = Signal(object)
    error = Signal(str, str)
    cancelled = Signal()
    queue_update = Signal()

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
            elif self.task == 'batch':
                params = dict(self.params); queue = params.pop('queue')
                result = queue.run(self.backend, **params, update=lambda _: self.queue_update.emit())
            elif self.task == 'install_aivis':
                result=self.params['pack'].install(self.cancel,self.progress.emit)
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

class PreviewText(QPlainTextEdit):
    textEdited = Signal()
    def __init__(self):
        super().__init__()
        self.textChanged.connect(self.textEdited.emit)
    def text(self):
        return self.toPlainText()
    def setText(self, text):
        old = self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(old)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SRT Voice Studio ' + __version__)
        available=self.screen().availableGeometry()
        self.setMinimumSize(min(980,max(700,available.width()-40)),min(690,max(460,available.height()-60)))
        self.resize(min(1340,max(self.minimumWidth(),available.width()-40)),
                    min(940,max(self.minimumHeight(),available.height()-60)))
        self.setAcceptDrops(True)
        self.backend = BackendRouter()
        from .aivis_pack import AivisPack
        self.aivis_pack=AivisPack()
        try:
            optional=self.aivis_pack.backend()
            if optional:self.backend.register(optional)
        except (OSError,ValueError,KeyError):logging.exception('Cannot load optional voice pack metadata')
        self.worker = None
        self.output = None
        self.preview_temp = None  # Compatibility: previews now use memory only.
        self.preview_device = None
        self.preview_cache = PreviewCache()
        self.captions = []
        self.loaded_fingerprint = None
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.playback_status)
        self.player.errorOccurred.connect(lambda *_: self.status.setText('Không phát được nghe thử: ' + self.player.errorString()))
        self.setStyleSheet("""
            QWidget { background: #091421; color: #e6eef9; font-family: 'Segoe UI'; font-size: 13px; }
            QGroupBox { background: #0d1b2a; border: 1px solid #22364c; border-radius: 9px;
                        margin-top: 12px; padding: 15px 12px 10px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 13px; padding: 0 5px; color: #e6f2ff; }
            QLabel { background: transparent; }
            QLineEdit, QPlainTextEdit, QComboBox, QDoubleSpinBox, QTextEdit {
                background: #17283b; border: 1px solid #35506b; border-radius: 6px;
                padding: 7px; color: #f0f5ff; selection-background-color: #1975df; }
            QComboBox { min-height: 22px; padding-right: 20px; }
            QComboBox QAbstractItemView { background: #17283b; selection-background-color: #2465a8; }
            QComboBox:disabled, QPushButton:disabled { color: #73859a; border-color: #273b50; }
            QPushButton { background: #20354b; border: 1px solid #375570; border-radius: 6px; padding: 9px; }
            QPushButton:hover { background: #2d4c6c; border-color: #4b84b9; }
            QPushButton#generate { background: #1172eb; border: 1px solid #338fff; font-size: 22px; font-weight: 700; }
            QPushButton#previewA { background: #125bbe; } QPushButton#previewB { border-color: #8060ca; }
            QPushButton#previewC { border-color: #21aa94; }
            QProgressBar { background: #17283b; border: none; border-radius: 5px; height: 14px; text-align: center; }
            QProgressBar::chunk { background: #11bfa8; border-radius: 5px; }
            QCheckBox { spacing: 7px; background: transparent; padding: 2px; }
            QScrollArea { border: none; } QScrollBar:vertical { width: 10px; background: #091421; }
            QScrollBar::handle:vertical { background: #34516f; border-radius: 4px; min-height: 30px; }
        """)
        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central); outer.setContentsMargins(18, 10, 18, 12); outer.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel(f'SRT Voice Studio <span style="color:#309fff">{__version__}</span>')
        title.setStyleSheet('font-size: 27px; font-weight: 700;')
        header.addWidget(title); header.addStretch()
        badge = QLabel('●  Ngoại tuyến · Trên máy')
        badge.setStyleSheet('color:#46dec2; background:#123b39; border-radius:14px; padding:7px 13px;')
        header.addWidget(badge); outer.addLayout(header)
        subtitle = QLabel('Tiếng Anh (Mỹ / Anh) / Tiếng Nhật · Chỉ xuất một MP3 · Giữ nguyên mốc SRT')
        subtitle.setObjectName('appSubtitle')
        subtitle.setStyleSheet('color:#9db1c9;'); outer.addWidget(subtitle)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); scroll.setWidget(body)
        self.tabs=QTabWidget();self.tabs.addTab(scroll,'Một tệp / Nghe thử');outer.addWidget(self.tabs,1)
        columns = QHBoxLayout(body); columns.setContentsMargins(0,0,0,0); columns.setSpacing(12)
        left_widget, right_widget = QWidget(), QWidget()
        left, right = QVBoxLayout(left_widget), QVBoxLayout(right_widget)
        for layout in (left,right): layout.setContentsMargins(0,0,0,0); layout.setSpacing(10)
        columns.addWidget(left_widget, 55); columns.addWidget(right_widget, 45)
        def group(title, parent):
            card = QGroupBox(title); box = QVBoxLayout(card); box.setSpacing(8); parent.addWidget(card)
            return box
        def combo(mapping, default=None):
            control = QComboBox()
            for value,label in mapping.items(): control.addItem(label,value)
            if default is not None: control.setCurrentIndex(control.findData(default))
            return control
        def field(layout, label, control):
            box = QVBoxLayout(); box.setSpacing(4); box.addWidget(QLabel(label)); box.addWidget(control)
            layout.addLayout(box)
        file_box = group('①  Tệp phụ đề SRT', left)
        file_row = QHBoxLayout()
        self.file = QLineEdit(); self.file.setPlaceholderText('Kéo thả tệp .srt hoặc chọn tệp…')
        browse = QPushButton('Chọn tệp'); browse.clicked.connect(self.browse)
        file_row.addWidget(self.file,1); file_row.addWidget(browse); file_box.addLayout(file_row)
        self.file_info = QLabel('Chưa chọn tệp · Hỗ trợ UTF-8 và tên tệp có dấu')
        self.file_info.setStyleSheet('color:#9db1c9;'); file_box.addWidget(self.file_info)
        voices_row = QHBoxLayout(); left.addLayout(voices_row)
        language_card = QGroupBox('②  Ngôn ngữ'); language_box = QVBoxLayout(language_card)
        self.language = combo(vi.LANGUAGES); language_box.addWidget(self.language)
        self.voice_count = QLabel(); self.voice_count.setStyleSheet('color:#9db1c9;'); language_box.addWidget(self.voice_count)
        voices_row.addWidget(language_card,2)
        voice_card = QGroupBox('③  Giọng đọc'); voice_box = QVBoxLayout(voice_card)
        self.voice = QComboBox(); voice_box.addWidget(self.voice)
        self.native_style=QComboBox();self.native_style.addItem('Phong cách bản địa: mặc định',None);voice_box.addWidget(self.native_style)
        self.voice_info = QLabel(); self.voice_info.setStyleSheet('color:#9db1c9;'); voice_box.addWidget(self.voice_info)
        voices_row.addWidget(voice_card,3)
        style_box = group('④  Phong cách giọng · tùy chọn', left)
        style_top, style_bottom = QHBoxLayout(), QHBoxLayout()
        self.emotion_mode = combo(vi.MODES)
        self.emotion = combo(vi.EMOTIONS)
        self.intensity = combo(vi.INTENSITIES,'Medium')
        self.effect = combo(vi.EFFECTS)
        self.strength = combo(vi.INTENSITIES,'Medium')
        for label,control in [('Chế độ',self.emotion_mode),('Cảm xúc',self.emotion),('Mức độ',self.intensity)]:
            field(style_top,label,control)
        for label,control in [('Hiệu ứng giọng',self.effect),('Độ mạnh',self.strength)]:
            field(style_bottom,label,control)
        style_box.addLayout(style_top); style_box.addLayout(style_bottom)
        note=QLabel('Chọn Tự nhiên + Không hiệu ứng để giữ giọng sạch. Cảm xúc và thì thầm được mô phỏng bằng xử lý âm thanh.')
        note.setWordWrap(True); note.setStyleSheet('color:#9db1c9; font-size:12px;'); style_box.addWidget(note)
        timeline_box = group('⑤  Mốc thời gian và căn giọng', left)
        timing_row = QHBoxLayout()
        self.speed = QDoubleSpinBox(); self.speed.setRange(1,1.2); self.speed.setSingleStep(.01); self.speed.setValue(1); self.speed.setSuffix('×')
        self.gap = QComboBox()
        for ms in (0,50,100,150,200): self.gap.addItem(f'{ms/1000:.2f} giây',ms)
        self.gap.setCurrentIndex(2)
        self.overflow = combo(vi.OVERFLOWS)
        self.overflow.setToolTip('Cắt an toàn có thể cắt từ cuối câu quá dài. Dừng và báo lỗi giữ nguyên MP3 cũ để bạn sửa SRT.')
        for label,control in [('Tốc độ gốc',self.speed),('Khoảng cách tối thiểu',self.gap),('Câu quá dài',self.overflow)]:
            field(timing_row,label,control)
        timeline_box.addLayout(timing_row)
        self.adaptive = QCheckBox('Tự căn câu ngắn / dài (0.88–1.20×)'); self.adaptive.setChecked(True)
        self.adaptive.setToolTip('Mục tiêu im lặng cuối khung 0.20 giây. Không chậm dưới 0.88×; câu quá ngắn vẫn có thể còn khoảng lặng.')
        self.normalize = QCheckBox('Cân bằng âm lượng'); self.normalize.setChecked(True)
        timeline_box.addWidget(self.adaptive); timeline_box.addWidget(self.normalize)
        for text in ('Khóa mốc bắt đầu theo SRT','Không chồng tiếng','Tự dọn âm thanh tạm'):
            check=QCheckBox(text); check.setChecked(True); check.setEnabled(False); timeline_box.addWidget(check)
        left.addStretch()
        preview_box = group('⑥  Nghe thử giọng A / B / C', right)
        preview_box.addWidget(QLabel('Nội dung nghe thử'))
        self.preview_text = PreviewText(); self.preview_text.setMinimumHeight(85); self.preview_text.setMaximumHeight(110)
        preview_box.addWidget(self.preview_text)
        buttons=QHBoxLayout(); self.preview_buttons=[]
        for stage,label in [('A','▶  A · Giọng gốc'),('B','▶  B · Đã xử lý'),('C','▶  C · Theo SRT')]:
            button=QPushButton(label); button.setObjectName('preview'+stage); button.setMinimumHeight(48)
            button.clicked.connect(lambda checked=False,stage=stage:self.preview_voice(stage))
            self.preview_buttons.append(button); buttons.addWidget(button)
        preview_box.addLayout(buttons)
        durations=QHBoxLayout(); self.duration_cards=[]
        for label,color in [('A · Giọng gốc','#35b5ff'),('B · Đã xử lý','#b493ff'),('C · Theo mốc SRT','#25d1a6')]:
            value=QLabel(label+'\n—'); value.setStyleSheet(f'border-left:3px solid {color}; padding:8px; font-size:16px;')
            durations.addWidget(value); self.duration_cards.append(value)
        preview_box.addLayout(durations)
        self.preview_details=QLabel('Chọn A để nghe giọng gốc. B dùng cùng giọng gốc sau xử lý.')
        self.preview_details.setWordWrap(True); self.preview_details.setMinimumHeight(95)
        self.preview_details.setStyleSheet('background:#122337; border:1px solid #28425c; border-radius:7px; padding:10px;')
        self.preview_details.setTextInteractionFlags(Qt.TextSelectableByMouse); preview_box.addWidget(self.preview_details)
        caption_box=group('⑦  Chọn câu SRT để nghe bản cuối',right)
        caption_row=QHBoxLayout()
        self.caption_select=QComboBox(); self.caption_select.addItem('Nội dung tự nhập · chưa chọn câu',None)
        self.previous_caption=QPushButton('‹'); self.next_caption=QPushButton('›')
        self.previous_caption.setFixedWidth(36); self.next_caption.setFixedWidth(36)
        self.previous_caption.clicked.connect(lambda:self.caption_select.setCurrentIndex(max(0,self.caption_select.currentIndex()-1)))
        self.next_caption.clicked.connect(lambda:self.caption_select.setCurrentIndex(min(self.caption_select.count()-1,self.caption_select.currentIndex()+1)))
        caption_row.addWidget(self.caption_select,1); caption_row.addWidget(self.previous_caption); caption_row.addWidget(self.next_caption)
        caption_box.addLayout(caption_row)
        self.caption_body=QLabel('Chọn SRT ở cột trái, sau đó chọn câu muốn kiểm tra.')
        self.caption_body.setTextFormat(Qt.PlainText); self.caption_body.setWordWrap(True); self.caption_body.setMinimumHeight(48)
        caption_box.addWidget(self.caption_body)
        self.slot_details=QLabel('Bắt đầu: —    Kết thúc cho phép: —\nThời gian khả dụng: —')
        self.slot_details.setWordWrap(True); self.slot_details.setStyleSheet('color:#a8c6e7; padding:5px;'); caption_box.addWidget(self.slot_details)
        right.addStretch()
        footer=QHBoxLayout()
        self.generate=QPushButton('▶  TẠO MP3'); self.generate.setObjectName('generate'); self.generate.setMinimumSize(285,58)
        self.generate.clicked.connect(self.generate_mp3)
        self.cancel_button=QPushButton('Hủy'); self.cancel_button.setMinimumHeight(58); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_job)
        footer.addWidget(self.generate,3); footer.addWidget(self.cancel_button,1)
        progress_box=QVBoxLayout()
        self.bar=QProgressBar(); self.bar.setValue(0); progress_box.addWidget(self.bar)
        self.status=QLabel('Sẵn sàng · Chọn tệp SRT để bắt đầu'); self.status.setWordWrap(True); progress_box.addWidget(self.status)
        footer.addLayout(progress_box,5)
        self.open_folder=QPushButton('Mở thư mục kết quả'); self.open_folder.setEnabled(False); self.open_folder.clicked.connect(self.open_output)
        footer.addWidget(self.open_folder,2); outer.addLayout(footer)
        self.report=QTextEdit(); self.report.setReadOnly(True); self.report.setFixedHeight(130)
        self.report.setPlaceholderText('Kết quả sẽ hiển thị ở đây: số câu, căn tốc độ, khoảng lặng và kiểm tra chồng tiếng.')
        outer.addWidget(self.report)
        self.diagnostic_action=self.menuBar().addMenu('Trợ giúp').addAction('Kiểm tra ứng dụng')
        self.diagnostic_action.triggered.connect(lambda:self.start('diagnose',{}))
        self.edit_controls=[browse,self.file,self.language,self.voice,self.native_style,self.preview_text,self.caption_select,
            self.previous_caption,self.next_caption,self.emotion_mode,self.emotion,self.intensity,self.effect,self.strength,
            self.speed,self.gap,self.overflow,self.adaptive,self.normalize]
        self.language.currentIndexChanged.connect(self.language_changed)
        self.file.editingFinished.connect(self.load_captions)
        self.caption_select.currentIndexChanged.connect(self.caption_changed)
        self.preview_text.textEdited.connect(self.custom_text_edited)
        self.voice.currentIndexChanged.connect(self.voice_changed)
        self.native_style.currentIndexChanged.connect(self.invalidate_base)
        for control in (self.emotion_mode,self.emotion,self.intensity,self.effect,self.strength,self.gap,self.overflow):
            control.currentIndexChanged.connect(self.style_changed)
        self.speed.valueChanged.connect(self.style_changed); self.adaptive.toggled.connect(self.style_changed); self.normalize.toggled.connect(self.style_changed)
        from .batch_ui import BatchPanel
        self.batch_panel=BatchPanel(self);self.tabs.addTab(self.batch_panel,'Hàng đợi xử lý')
        from .voice_ui import VoicePanel
        self.voice_panel=VoicePanel(self)
        voice_scroll=QScrollArea();voice_scroll.setWidgetResizable(True);voice_scroll.setWidget(self.voice_panel)
        self.tabs.addTab(voice_scroll,'Thư viện giọng')
        self.tabs.currentChanged.connect(self.tab_changed)
        self.language_changed(); self.refresh_controls()
        menu=self.menuBar().addMenu('Cấu hình')
        menu.addAction('Lưu cấu hình hiện tại').triggered.connect(self.save_preferences)
        menu.addAction('Nạp cấu hình đã lưu').triggered.connect(self.load_preferences)

    def tab_changed(self,index):
        self.generate.setVisible(index==0)
        self.open_folder.setVisible(index==0)
        self.report.setVisible(index==0)

    def save_preferences(self):
        from .preferences import save_settings
        save_settings(self.settings())
        self.status.setText('Đã lưu cấu hình cho các lần sử dụng sau.')

    def load_preferences(self):
        if self.busy():return
        from .preferences import load_settings
        value=load_settings()
        for key in ('language','voice','native_style','emotion_mode','emotion','intensity','effect','strength','overflow'):
            control=getattr(self,key);index=control.findData(getattr(value,key))
            if index>=0:control.setCurrentIndex(index)
        self.speed.setValue(value.speed if isinstance(value.speed,(float,int)) else 1)
        index=self.gap.findData(value.gap_ms)
        if index>=0:self.gap.setCurrentIndex(index)
        self.adaptive.setChecked(bool(value.adaptive));self.normalize.setChecked(bool(value.loudness))
        self.status.setText('Đã nạp cấu hình đã lưu.')

    def voice_changed(self, *_):
        self.voice_info.setText('Mã giọng: '+str(self.voice.currentData() or '—'))
        self.native_style.clear();self.native_style.addItem('Phong cách bản địa: mặc định',None)
        for style in self.backend.styles(self.voice.currentData()):self.native_style.addItem(style['name'],style['id'])
        self.native_style.setEnabled(not self.busy() and self.native_style.count()>1)
        self.invalidate_base()

    def language_changed(self, *_):
        language=self.language.currentData()
        choices=[v for v in self.backend.list_voices() if v.language==language]
        self.voice.clear()
        for voice in choices:self.voice.addItem(vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name,voice.id)
        self.voice_count.setText(f'{len(choices)} giọng · Chạy trên CPU')
        if self.caption_select.currentData() is None:self.preview_text.setText(PREVIEW[language])
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
        return self.worker is not None

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
        self.batch_panel.set_busy(True)
        self.voice_panel.install.setEnabled(False)
        self.worker.queue_update.connect(self.batch_panel.refresh)
        self.worker.progress.connect(self.progress)
        self.worker.success.connect(lambda result: self.success(task, result))
        self.worker.error.connect(self.show_error)
        self.worker.cancelled.connect(lambda: self.status.setText('Đã hủy. Không xuất MP3 mới.'))
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        worker=self.worker
        self.worker=None
        if worker is not None:worker.deleteLater()
        self.batch_panel.set_busy(False)
        self.voice_panel.refresh_install()
        for control in self.edit_controls + [self.generate] + self.preview_buttons:
            control.setEnabled(True)
        self.diagnostic_action.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.refresh_controls()

    def progress(self, done, total, message):
        self.bar.setValue(int(done * 100 / max(total, 1)))
        for mapping in (vi.EMOTIONS,vi.EFFECTS,vi.INTENSITIES):
            for source,label in mapping.items():
                message=message.replace(' • '+source+' • ',' • '+label+' • ')
                message=message.replace(' • '+source+' /',' • '+label+' /')
                message=message.replace('/ '+source+' •','/ '+label+' •')
        self.status.setText(vi.message(message))

    def settings(self):
        return Settings(language=self.language.currentData(), voice=self.voice.currentData(),
            speed=self.speed.value(), gap_ms=self.gap.currentData(), adaptive=self.adaptive.isChecked(),
            loudness=self.normalize.isChecked(), overflow=self.overflow.currentData(),
            emotion_mode=self.emotion_mode.currentData(), emotion=self.emotion.currentData(),
            intensity=self.intensity.currentData(), effect=self.effect.currentData(), strength=self.strength.currentData(),native_style=self.native_style.currentData())

    def refresh_controls(self):
        idle = not self.busy()
        self.native_style.setEnabled(idle and self.native_style.count()>1)
        self.emotion.setEnabled(idle and self.emotion_mode.currentData() == 'Manual')
        self.intensity.setEnabled(idle and self.emotion_mode.currentData() == 'Manual' and self.emotion.currentData() != 'Natural')
        self.strength.setEnabled(idle and self.effect.currentData() != 'None')
        self.preview_buttons[2].setEnabled(idle and self.caption_select.currentData() is not None)

    def invalidate_base(self, *_):
        if self.busy():
            return
        self.stop_preview()
        self.preview_cache.clear()
        self.clear_preview_details()

    def style_changed(self, *_):
        self.stop_preview()
        a = self.preview_cache.base
        self.clear_preview_details()
        if a is not None:self.duration_cards[0].setText(f'A · Giọng gốc\n{len(a)/self.preview_cache.rate:.3f} giây')
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
        file=Path(self.file.text().strip())
        fingerprint=(str(file),file.stat().st_mtime_ns) if file.is_file() else None
        if fingerprint is not None and fingerprint==self.loaded_fingerprint:return
        self.loaded_fingerprint=None
        self.captions = []
        self.caption_select.blockSignals(True)
        self.caption_select.clear()
        self.caption_select.addItem('Nội dung tự nhập · chọn câu để nghe C', None)
        try:
            if self.file.text().strip():
                self.captions = read_srt(Path(self.file.text().strip()))
                slots_for(self.captions, self.gap.currentData())
                for i, caption in enumerate(self.captions):
                    self.caption_select.addItem(f'Câu {caption.index} · {self.timestamp(caption.start*48)}', i)
                self.loaded_fingerprint=fingerprint
                self.file_info.setText(f'{len(self.captions)} câu · Thời lượng {self.timestamp(max(c.end for c in self.captions)*48)} · UTF-8')
        except Exception as exc:
            self.status.setText(vi.message(str(exc)))
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

    def clear_preview_details(self):
        for control,label in zip(self.duration_cards,('A · Giọng gốc','B · Đã xử lý','C · Theo mốc SRT')):
            control.setText(label+'\n—')
        self.preview_details.setText('Tốc độ cuối: — · Im lặng cuối khung: —\nChưa lấp đầy: — · Chồng tiếng: —')

    def show_slot(self):
        try:
            slot=self.selected_slot()
            if slot:
                self.caption_body.setText(slot.caption.text)
                self.slot_details.setText(f'Bắt đầu: {self.timestamp(slot.start)}\nKết thúc cho phép: {self.timestamp(slot.end)}\nKhả dụng: {(slot.end-slot.start)/RATE:.3f} giây')
            else:
                self.caption_body.setText('Chọn câu trong SRT để nghe C theo mốc thời gian.')
                self.slot_details.setText('Bắt đầu: — · Kết thúc cho phép: — · Khả dụng: —')
        except Exception as exc:
            self.slot_details.setText(vi.message(str(exc)))
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
        if task == 'install_aivis':
            optional=self.aivis_pack.backend()
            if optional:self.backend.register(optional)
            previous=self.voice.currentData();self.language_changed()
            index=self.voice.findData(previous)
            if index>=0:self.voice.setCurrentIndex(index)
            self.voice_panel.refresh();self.status.setText('Đã cài gói Aivis. Giọng mới nằm trong Tiếng Nhật; chưa có điểm nghe xác nhận.')
        elif task == 'preview':
            self.preview_device=QBuffer(self)
            self.preview_device.setData(QByteArray(wav_bytes(result.samples,result.rate)))
            self.preview_device.open(QIODevice.ReadOnly)
            self.player.setSourceDevice(self.preview_device)
            self.player.play()
            self.status.setText(f'Đang nghe {vi.PREVIEW_LABELS[result.stage]} · {vi.display(result.details["emotion"])} · {vi.display(result.details["effect"])}')
            d=result.details
            for control,label,key in zip(self.duration_cards,('A · Giọng gốc','B · Đã xử lý','C · Theo mốc SRT'),('original_seconds','processed_seconds','final_seconds')):
                value=d.get(key); control.setText(label+'\n'+('—' if value is None else f'{value:.3f} giây'))
            detail='B dùng cùng giọng gốc A; chỉ thay đổi phần xử lý âm thanh.'
            if 'speed' in d:
                detail=f'Tốc độ cuối: {d["speed"]:.3f}× · Đã cắt: {"Có" if d["trimmed"] else "Không"}\nChồng tiếng: {d["overlaps"]} · Im lặng cuối khung: {d["trailing_silence"]:.3f} giây\nChưa lấp đầy: {"CÓ" if d["underfilled"] else "KHÔNG"}'
                if d['warning']:detail+='\n'+vi.message(d['warning'])
            self.preview_details.setText(detail)
            self.show_slot()
        elif task == 'batch':
            self.stop_preview();self.preview_cache.clear();self.clear_preview_details()
            self.batch_panel.refresh()
            self.status.setText('Đã kết thúc hàng đợi')
            self.report.setPlainText(self.batch_panel.summary.text())
        elif task == 'diagnose':
            self.report.setPlainText('\n'.join(vi.message(line) for line in result))
            self.status.setText('Đã kiểm tra • Xem kết quả bên dưới')
        else:
            self.stop_preview()
            self.preview_cache.clear()
            self.clear_preview_details()
            self.output = result['output']
            self.open_folder.setEnabled(True)
            trimmed = result['safely_trimmed']
            underfilled = result['underfilled_captions']
            self.status.setText('HOÀN TẤT' + (f' · {trimmed} câu đã cắt an toàn' if trimmed else '')
                + (f' · {underfilled} câu chưa lấp đầy khung' if underfilled else ''))
            emotion_label=vi.display(result['emotion']) if result['emotion_mode']=='Manual' else 'Theo từng câu'
            self.report.setPlainText(f"MP3 cuối: {self.output}\nThời lượng: {result['duration']} · {result['total']} câu · {result['valid']} hợp lệ\n"
                f"Cảm xúc: {vi.display(result['emotion_mode'])} / {emotion_label} · Hiệu ứng: {vi.display(result['effect'])} / {vi.display(result['strength'])}\n"
                f"Tăng tốc: {result['speed_up_captions']} · Giảm tốc: {result['slow_down_captions']} · Cắt an toàn: {trimmed}\n"
                f"Chưa lấp đầy: {underfilled} · Còn thiếu ở giới hạn 0.88×: {result['underfilled_after_hard_minimum']}\n"
                f"Im lặng cuối khung — Trung bình: {result['average_trailing_silence']:.3f} giây · Trung vị: {result['median_trailing_silence']:.3f} giây · Lớn nhất: {result['maximum_trailing_silence']:.3f} giây\n"
                f"{result['overlaps']} chồng tiếng · MỐC THỜI GIAN HỢP LỆ")

    def cancel_job(self):
        if self.busy():
            if self.worker.task=='batch':self.batch_panel.queue.cancel_all()
            self.worker.cancel.set()
            self.status.setText('Đang hủy… chờ lượt suy luận hiện tại kết thúc.')

    def show_error(self, message, details):
        message=vi.message(message)
        self.status.setText('Không hoàn tất · ' + message)
        box = QMessageBox(QMessageBox.Critical, 'SRT Voice Studio', message, parent=self)
        box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.Ok)
        box.button(QMessageBox.Ok).setText('Đóng')
        box.exec()

    def playback_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.stop_preview()

    def stop_preview(self):
        self.player.stop()
        self.player.setSource(QUrl())
        if self.preview_device is not None:
            self.preview_device.close()
            self.preview_device.deleteLater()
            self.preview_device=None

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
            self.aivis_pack.close()
            event.accept()
