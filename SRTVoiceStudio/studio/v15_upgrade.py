"""SRT Voice Studio 1.5 workflow layer.

This module intentionally augments the stable 1.4.2 Window instead of
rewriting it.  The production renderer remains shared by one-file and batch
workflows; the new tabs are workflow helpers around that same engine.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, replace
from pathlib import Path
from types import MethodType

from PySide6.QtCore import QThread, Signal, QBuffer, QIODevice, QByteArray, QUrl, Qt
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox, QCheckBox)

from . import ui_text as vi
from .audio import wav_bytes, Cancelled
from .backend import PREVIEW
from .render import Settings
from .voice_backends import synthesize_selected
from .timeline import read_srt, slots_for, RATE
from .v15_core import (BUILTIN_PRESETS, all_presets, load_custom_presets, save_custom_presets,
    settings_from_mapping, estimate_caption, load_batch_queue, save_batch_queue)


class CompareWorker(QThread):
    success = Signal(object, int, str)
    error = Signal(str)

    def __init__(self, backend, text, settings, label):
        super().__init__()
        self.backend, self.text, self.settings, self.label = backend, text, settings, label
        self.cancel = threading.Event()

    def run(self):
        try:
            samples, rate = synthesize_selected(self.backend, self.text, self.settings,
                                                self.cancel, lambda *_: None)
            self.success.emit(samples, int(rate), self.label)
        except Cancelled:
            self.error.emit('Đã hủy nghe thử.')
        except Exception as exc:
            self.error.emit(str(exc))


class VoiceComparePanel(QWidget):
    def __init__(self, window):
        super().__init__(); self.window = window; self.worker = None; self.device = None
        self.player = QMediaPlayer(self); self.audio = QAudioOutput(self); self.player.setAudioOutput(self.audio)
        layout = QVBoxLayout(self)
        head = QLabel('So sánh Voice A / B / C / D · cùng nội dung · không emotion/FX')
        head.setStyleSheet('font-size:17px;font-weight:650;'); layout.addWidget(head)
        top = QHBoxLayout(); top.addWidget(QLabel('Ngôn ngữ'))
        self.language = QComboBox()
        for value, label in vi.LANGUAGES.items(): self.language.addItem(label, value)
        top.addWidget(self.language); top.addStretch(); layout.addLayout(top)
        self.text = QPlainTextEdit(); self.text.setMaximumHeight(105); layout.addWidget(self.text)
        grid = QGridLayout(); self.choices=[]; self.buttons=[]
        for row, letter in enumerate('ABCD'):
            label=QLabel(letter); label.setStyleSheet('font-size:20px;font-weight:700;')
            combo=QComboBox(); button=QPushButton(f'▶ Nghe {letter}')
            button.clicked.connect(lambda checked=False, n=row: self.play(n))
            grid.addWidget(label,row,0);grid.addWidget(combo,row,1);grid.addWidget(button,row,2)
            self.choices.append(combo);self.buttons.append(button)
        layout.addLayout(grid)
        self.status=QLabel('Chọn 2–4 giọng rồi nghe cùng một câu để so sánh trực tiếp.')
        self.status.setWordWrap(True);layout.addWidget(self.status);layout.addStretch()
        self.language.currentIndexChanged.connect(self.refresh)
        current=window.language.currentData();idx=self.language.findData(current)
        if idx>=0:self.language.setCurrentIndex(idx)
        self.refresh()

    def refresh(self,*_):
        language=self.language.currentData()
        if not self.text.toPlainText().strip() or self.text.toPlainText() in PREVIEW.values():
            self.text.setPlainText(PREVIEW[language])
        voices=[v for v in self.window.backend.list_voices() if v.language==language]
        for n,combo in enumerate(self.choices):
            previous=combo.currentData();combo.clear()
            for voice in voices:
                label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
                combo.addItem(label,voice.id)
            idx=combo.findData(previous)
            combo.setCurrentIndex(idx if idx>=0 else min(n,max(0,combo.count()-1)))
        installed=len(voices)
        self.status.setText(f'{installed} giọng đã cài có thể so sánh. Aivis chỉ xuất hiện ở đây sau khi tải model.')

    def play(self,index):
        if self.worker is not None or self.window.busy():
            self.status.setText('Đang có tác vụ khác. Hãy chờ tác vụ hiện tại kết thúc.')
            return
        text=self.text.toPlainText().strip();voice=self.choices[index].currentData()
        if not text or not voice:return
        language=self.language.currentData()
        settings=replace(self.window.settings(),language=language,voice=voice,native_style=None,
                         emotion_mode='Manual',emotion='Natural',effect='None',speed=1.0,
                         continuous=False)
        label=self.choices[index].currentText()
        for button in self.buttons:button.setEnabled(False)
        self.window.generate.setEnabled(False)
        self.status.setText(f'Đang tạo bản nghe thử {chr(65+index)} · {label}…')
        self.worker=CompareWorker(self.window.backend,text,settings,label)
        self.worker.success.connect(self._play_result);self.worker.error.connect(self._error)
        self.worker.finished.connect(self._finished);self.worker.start()

    def _play_result(self,samples,rate,label):
        self.player.stop();self.player.setSource(QUrl())
        if self.device is not None:self.device.close();self.device.deleteLater()
        self.device=QBuffer(self);self.device.setData(QByteArray(wav_bytes(samples,rate)));self.device.open(QIODevice.ReadOnly)
        self.player.setSourceDevice(self.device);self.player.play()
        self.status.setText(f'Đang nghe: {label} · {len(samples)/rate:.3f} giây')

    def _error(self,message):self.status.setText('Không nghe được: '+message)
    def _finished(self):
        worker=self.worker;self.worker=None
        if worker is not None:worker.deleteLater()
        for button in self.buttons:button.setEnabled(True)
        self.window.generate.setEnabled(not self.window.busy())


class TimelineInspectorPanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self)
        head=QHBoxLayout();self.analyze=QPushButton('Phân tích SRT');self.optimize=QPushButton('Áp dụng cài đặt Smart Fit 2.0')
        self.first_risk=QPushButton('Mở câu rủi ro đầu tiên')
        for b in (self.analyze,self.optimize,self.first_risk):head.addWidget(b)
        head.addStretch();layout.addLayout(head)
        self.note=QLabel('Đây là preflight nhanh theo mật độ chữ. Kết quả cuối vẫn dùng thời lượng TTS thực khi render.')
        self.note.setWordWrap(True);layout.addWidget(self.note)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['Câu','Khung','Ước tính voice','Tỷ lệ','Trạng thái','Khuyến nghị'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers);self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5,QHeaderView.Stretch);layout.addWidget(self.table,1)
        self.summary=QLabel('Chưa phân tích.');layout.addWidget(self.summary)
        self.analyze.clicked.connect(self.refresh);self.optimize.clicked.connect(self.apply_safe)
        self.first_risk.clicked.connect(self.open_first_risk);self.risk_rows=[]

    def refresh(self,*_):
        path=Path(self.window.file.text().strip())
        if not path.is_file():
            self.table.setRowCount(0);self.summary.setText('Hãy chọn một tệp SRT ở tab Một tệp / Nghe thử trước.');return
        try:
            captions=read_srt(path);slots=slots_for(captions,self.window.gap.currentData());language=self.window.language.currentData()
            self.table.setRowCount(len(slots));counts={};self.risk_rows=[]
            for row,slot in enumerate(slots):
                info=estimate_caption(slot.caption.text,(slot.end-slot.start)/RATE,language);counts[info['status']]=counts.get(info['status'],0)+1
                if info['status']!='ỔN':self.risk_rows.append(row)
                values=[str(slot.caption.index),f"{info['slot_seconds']:.3f}s",f"{info['estimated_seconds']:.3f}s",f"{info['ratio']:.2f}×",info['status'],info['advice']]
                for col,value in enumerate(values):self.table.setItem(row,col,QTableWidgetItem(value))
            self.summary.setText(f"{len(slots)} câu · Ổn: {counts.get('ỔN',0)} · Hơi dài: {counts.get('HƠI DÀI',0)} · Nguy cơ cắt: {counts.get('NGUY CƠ CẮT',0)} · Quá ngắn: {counts.get('QUÁ NGẮN',0)}")
        except Exception as exc:self.summary.setText('Không phân tích được: '+str(exc))

    def apply_safe(self):
        self.window.adaptive.setChecked(True)
        idx=self.window.gap.findData(100)
        if idx>=0:self.window.gap.setCurrentIndex(idx)
        idx=self.window.overflow.findData('Safe Trim')
        if idx>=0:self.window.overflow.setCurrentIndex(idx)
        if hasattr(self.window,'continuous_voice'):self.window.continuous_voice.setChecked(True)
        if hasattr(self.window,'continuous_target'):
            idx=self.window.continuous_target.findData(100)
            if idx>=0:self.window.continuous_target.setCurrentIndex(idx)
        self.window.status.setText('Đã áp dụng Smart Fit 2.0: adaptive + gap 0.10s + Continuous Voice.')
        self.refresh()

    def open_first_risk(self):
        if not self.risk_rows:self.refresh()
        if not self.risk_rows:return
        row=self.risk_rows[0];self.table.selectRow(row)
        # caption_select index 0 is custom text; SRT rows start at index 1.
        if row+1<self.window.caption_select.count():self.window.caption_select.setCurrentIndex(row+1)
        self.window.tabs.setCurrentIndex(0)


class PresetPanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self)
        title=QLabel('Preset / Profile Manager · lưu toàn bộ voice + timing + emotion + Continuous Voice')
        title.setStyleSheet('font-size:17px;font-weight:650;');layout.addWidget(title)
        row=QHBoxLayout();self.preset=QComboBox();self.name=QLineEdit();self.name.setPlaceholderText('Tên preset mới…')
        row.addWidget(self.preset,2);row.addWidget(self.name,1);layout.addLayout(row)
        actions=QHBoxLayout();self.apply=QPushButton('Áp dụng');self.save=QPushButton('Lưu cấu hình hiện tại');self.delete=QPushButton('Xóa preset tự tạo')
        for b in (self.apply,self.save,self.delete):actions.addWidget(b)
        layout.addLayout(actions)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);layout.addWidget(self.details,1)
        self.status=QLabel('');layout.addWidget(self.status)
        self.preset.currentIndexChanged.connect(self.show_details);self.apply.clicked.connect(self.apply_selected)
        self.save.clicked.connect(self.save_current);self.delete.clicked.connect(self.delete_selected)
        self.reload()

    def reload(self,select=None):
        self.data=all_presets();self.preset.blockSignals(True);self.preset.clear()
        for name in self.data:self.preset.addItem(('★ ' if name in BUILTIN_PRESETS else '')+name,name)
        self.preset.blockSignals(False)
        if select:
            idx=self.preset.findData(select)
            if idx>=0:self.preset.setCurrentIndex(idx)
        self.show_details()

    def show_details(self,*_):
        name=self.preset.currentData();value=self.data.get(name,{})
        gap=value.get('gap_ms',-1)
        gap_label='Tự động' if gap < 0 else f'{gap/1000:.2f}s'
        lines=[f'Tên: {name}',f'Loại: {"Có sẵn" if name in BUILTIN_PRESETS else "Tự tạo"}',
            f"Ngôn ngữ: {value.get('language','—')}",f"Giọng: {value.get('voice','—')}",
            f"Speed: {value.get('speed',1):.2f}× · Gap: {gap_label}",
            f"Cảm xúc: {value.get('emotion','Natural')} · FX: {value.get('effect','None')}",
            f"Continuous Voice: {'Bật' if value.get('continuous') else 'Tắt'} · Target: {value.get('continuous_target_ms',100)} ms"]
        self.details.setPlainText('\n'.join(lines));self.delete.setEnabled(bool(name) and name not in BUILTIN_PRESETS)

    def apply_selected(self):
        name=self.preset.currentData()
        if not name:return
        settings=settings_from_mapping(self.data[name]);actual=apply_settings(self.window,settings)
        self.status.setText(f'Đã áp dụng {name}.'+(' Giọng preset chưa cài nên đã dùng giọng khả dụng đầu tiên.' if actual.voice!=settings.voice else ''))

    def save_current(self):
        name=self.name.text().strip()
        if not name:
            self.status.setText('Nhập tên preset trước khi lưu.');return
        if name in BUILTIN_PRESETS:
            self.status.setText('Tên này thuộc preset có sẵn; hãy chọn tên khác.');return
        custom=load_custom_presets();custom[name]=asdict(self.window.settings());save_custom_presets(custom)
        self.name.clear();self.reload(name);self.status.setText('Đã lưu preset: '+name)

    def delete_selected(self):
        name=self.preset.currentData()
        if not name or name in BUILTIN_PRESETS:return
        custom=load_custom_presets();custom.pop(name,None);save_custom_presets(custom);self.reload();self.status.setText('Đã xóa preset: '+name)


def _set_combo(control,value):
    idx=control.findData(value)
    if idx>=0:control.setCurrentIndex(idx);return True
    return False


def apply_settings(window,settings):
    _set_combo(window.language,settings.language)
    # language_changed is signal-driven, but process immediately for offscreen tests too.
    window.language_changed()
    voice_index=window.voice.findData(settings.voice)
    enabled=voice_index>=0 and window.voice.model().item(voice_index).isEnabled()
    if enabled:window.voice.setCurrentIndex(voice_index)
    else:
        for i in range(window.voice.count()):
            if window.voice.model().item(i).isEnabled():window.voice.setCurrentIndex(i);break
    _set_combo(window.native_style,settings.native_style)
    for name in ('emotion_mode','emotion','intensity','effect','strength','overflow'):_set_combo(getattr(window,name),getattr(settings,name))
    window.speed.setValue(settings.speed);_set_combo(window.gap,settings.gap_ms)
    window.adaptive.setChecked(bool(settings.adaptive));window.normalize.setChecked(bool(settings.loudness))
    if hasattr(window,'continuous_voice'):window.continuous_voice.setChecked(bool(settings.continuous))
    if hasattr(window,'continuous_target'):_set_combo(window.continuous_target,int(settings.continuous_target_ms))
    window.style_changed();return window.settings()


def _enhance_batch(window):
    panel=window.batch_panel
    restored=load_batch_queue()
    if restored.items:panel.queue=restored
    original_refresh=panel.refresh
    def refresh_and_save(self,*args):
        original_refresh(*args)
        try:save_batch_queue(self.queue)
        except OSError:pass
    panel.refresh=MethodType(refresh_and_save,panel)
    tools=QHBoxLayout();clear_done=QPushButton('Xóa hàng đã hoàn tất');save_now=QPushButton('Lưu hàng đợi')
    def clear_completed():
        if window.busy():return
        panel.queue.items=[i for i in panel.queue.items if i.state!='Hoàn tất'];panel.refresh()
    clear_done.clicked.connect(clear_completed)
    save_now.clicked.connect(lambda: (save_batch_queue(panel.queue),panel.summary.setText(panel.summary.text()+' · Đã lưu')))
    tools.addWidget(clear_done);tools.addWidget(save_now);tools.addStretch();panel.layout().insertLayout(1,tools)
    panel.edit_buttons.extend([clear_done,save_now]);panel.refresh()
    app=QApplication.instance()
    if app is not None:app.aboutToQuit.connect(lambda: save_batch_queue(panel.queue))


def enhance_window(window):
    """Attach 1.5 features to a fully constructed stable Window."""
    from .preferences import read as read_preferences, load_settings
    timeline_group=next((g for g in window.findChildren(QGroupBox) if g.title().startswith('⑤')),None)
    window.continuous_voice=QCheckBox('Continuous Voice Mode · giảm khoảng lặng và nối caption tự nhiên hơn')
    saved=read_preferences().get('settings',{})
    window.continuous_voice.setChecked(bool(saved.get('continuous',True)) if isinstance(saved,dict) else True)
    window.continuous_target=QComboBox()
    for ms in (80,100,120,150):window.continuous_target.addItem(f'Mục tiêu silence {ms/1000:.2f} giây',ms)
    target=int(saved.get('continuous_target_ms',100)) if isinstance(saved,dict) else 100
    idx=window.continuous_target.findData(target);window.continuous_target.setCurrentIndex(idx if idx>=0 else 1)
    if timeline_group is not None:
        row=QHBoxLayout();row.addWidget(window.continuous_voice,2);row.addWidget(window.continuous_target,1);timeline_group.layout().addLayout(row)
    base_settings=window.settings
    def settings_v15():
        return replace(base_settings(),continuous=window.continuous_voice.isChecked(),
                       continuous_target_ms=int(window.continuous_target.currentData() or 100))
    window.settings=settings_v15
    window.edit_controls.extend([window.continuous_voice,window.continuous_target])
    window.continuous_voice.toggled.connect(window.style_changed);window.continuous_target.currentIndexChanged.connect(window.style_changed)
    window.continuous_voice.toggled.connect(lambda checked:window.continuous_target.setEnabled(checked and not window.busy()))
    window.continuous_target.setEnabled(window.continuous_voice.isChecked())

    _enhance_batch(window)
    window.voice_compare_panel=VoiceComparePanel(window);window.tabs.addTab(window.voice_compare_panel,'So sánh giọng A/B/C/D')
    window.timeline_inspector=TimelineInspectorPanel(window);window.tabs.addTab(window.timeline_inspector,'Smart Timeline Fit 2.0')
    window.preset_panel=PresetPanel(window);window.tabs.addTab(window.preset_panel,'Preset 1.5')
    window.tabs.currentChanged.connect(lambda idx: window.timeline_inspector.refresh() if window.tabs.widget(idx) is window.timeline_inspector else None)

    # Existing save action already calls self.settings() dynamically, so it now
    # saves 1.5 fields. Existing load action is followed by this small 1.5 sync.
    for top in window.menuBar().actions():
        menu=top.menu()
        if menu and top.text()=='Cấu hình':
            for action in menu.actions():
                if action.text()=='Nạp cấu hình đã lưu':
                    action.triggered.connect(lambda: _load_continuous(window))
    window.status.setText('Sẵn sàng · 1.5: Batch Recovery + Continuous Voice + Smart Fit + Voice Compare + Preset')
    return window


def _load_continuous(window):
    from .preferences import load_settings
    value=load_settings();window.continuous_voice.setChecked(bool(value.continuous))
    _set_combo(window.continuous_target,int(value.continuous_target_ms))
