"""Vietnamese queue controls, sharing the Window's one background worker."""
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QComboBox,
    QTableWidget,QTableWidgetItem,QFileDialog,QLabel,QDialog,QDialogButtonBox,QFormLayout,
    QAbstractItemView,QLineEdit,QHeaderView)
from .batch import BatchQueue, WAITING, RUNNING, DONE, FAILED, CANCELLED
from . import ui_text as vi
from .backend import EN_VOICES, JA_VOICES
from .timeline import display_time

class ItemEditor(QDialog):
    def __init__(self, item, parent):
        super().__init__(parent);self.setWindowTitle('Cấu hình riêng cho tệp')
        self.settings=item.settings;self.backend=parent.window.backend
        form=QFormLayout(self)
        self.controls={}
        for key,label,mapping in [('language','Ngôn ngữ',vi.LANGUAGES),('voice','Giọng đọc',{}),
            ('emotion_mode','Chế độ cảm xúc',vi.MODES),('emotion','Cảm xúc',vi.EMOTIONS),
            ('intensity','Mức cảm xúc',vi.INTENSITIES),('effect','Hiệu ứng',vi.EFFECTS),
            ('strength','Độ mạnh hiệu ứng',vi.INTENSITIES)]:
            combo=QComboBox();self.controls[key]=combo
            for value,text in mapping.items():combo.addItem(text,value)
            combo.setCurrentIndex(combo.findData(getattr(item.settings,key)))
            form.addRow(label,combo)
        self.controls['language'].currentIndexChanged.connect(self.voices)
        self.voices();self.controls['voice'].setCurrentIndex(self.controls['voice'].findData(item.settings.voice))
        self.controls['emotion_mode'].currentIndexChanged.connect(self.refresh)
        self.controls['effect'].currentIndexChanged.connect(self.refresh)
        buttons=QDialogButtonBox();buttons.addButton('Áp dụng',QDialogButtonBox.AcceptRole);buttons.addButton('Hủy',QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
        self.refresh()
    def voices(self):
        c=self.controls['voice'];c.clear()
        choices=[v for v in self.backend.list_voices() if v.language==self.controls['language'].currentData()]
        for voice in choices:c.addItem(vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name,voice.id)
    def refresh(self):
        manual=self.controls['emotion_mode'].currentData()=='Manual'
        for k in ('emotion','intensity'):self.controls[k].setEnabled(manual)
        self.controls['strength'].setEnabled(self.controls['effect'].currentData()!='None')
    def value(self):
        return replace(self.settings,**{k:c.currentData() for k,c in self.controls.items()})

class BatchPanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.queue=BatchQueue()
        layout=QVBoxLayout(self)
        top=QHBoxLayout();self.edit_buttons=[]
        for label,method in [('+ Thêm tệp',self.add_files),('+ Thêm thư mục',self.add_folder),('Sửa hàng đã chọn',self.edit_item),('Bỏ hàng đã chọn',self.remove_item),('Thử lại tệp lỗi / đã hủy',self.retry)]:
            button=QPushButton(label);button.clicked.connect(method);top.addWidget(button);self.edit_buttons.append(button)
        layout.addLayout(top)
        config=QHBoxLayout()
        self.mode=QComboBox();self.mode.addItems(['Áp dụng cấu hình hiện tại cho tất cả','Tùy chỉnh từng tệp'])
        config.addWidget(self.mode)
        self.destination=QLineEdit();self.destination.setPlaceholderText('Để trống: MP3 cạnh từng SRT')
        browse=QPushButton('Thư mục kết quả');browse.clicked.connect(self.choose_output)
        config.addWidget(self.destination,1);config.addWidget(browse);layout.addLayout(config)
        self.edit_buttons.extend([self.mode,self.destination,browse])
        layout.addWidget(QLabel('Mỗi lần xử lý một tệp • Một SRT → một MP3 • Một tệp lỗi không dừng hàng đợi'))
        self.table=QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels(['Tệp SRT','Ngôn ngữ','Giọng','Số câu','Thời lượng','Tiến độ','Trạng thái','MP3 / Lỗi'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7,QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(lambda *_:self.edit_item())
        layout.addWidget(self.table,1)
        bottom=QHBoxLayout()
        self.start_button=QPushButton('▶  BẮT ĐẦU XỬ LÝ HÀNG ĐỢI');self.start_button.clicked.connect(self.start)
        self.cancel_one=QPushButton('Hủy tệp đã chọn');self.cancel_one.clicked.connect(self.cancel_selected)
        self.cancel_all=QPushButton('Hủy toàn hàng đợi');self.cancel_all.clicked.connect(self.cancel_queue)
        self.open_button=QPushButton('Mở MP3 đã chọn');self.open_button.clicked.connect(self.open_output)
        for button in [self.start_button,self.cancel_one,self.cancel_all,self.open_button]:bottom.addWidget(button)
        layout.addLayout(bottom)
        self.summary=QLabel('Hàng đợi trống');layout.addWidget(self.summary)
    def selected(self):
        row=self.table.currentRow()
        return self.queue.items[row] if 0<=row<len(self.queue.items) else None
    def add_paths(self,paths):
        if self.window.busy():return
        self.queue.add(paths,self.window.settings());self.refresh()
    def add_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Thêm các tệp SRT','','SRT (*.srt)');self.add_paths(paths)
    def add_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Thêm thư mục SRT')
        if folder:self.add_paths(sorted(p for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower()=='.srt'))
    def choose_output(self):
        folder=QFileDialog.getExistingDirectory(self,'Chọn thư mục kết quả')
        if folder:self.destination.setText(folder)
    def edit_item(self):
        if self.window.busy():return
        item=self.selected()
        if item and item.state==WAITING:
            dialog=ItemEditor(item,self)
            if dialog.exec()==QDialog.Accepted:
                item.settings=dialog.value();self.mode.setCurrentIndex(1);self.refresh()
    def remove_item(self):
        if self.window.busy():return
        item=self.selected()
        if item:self.queue.items.remove(item);self.refresh()
    def retry(self):
        if not self.window.busy():self.queue.retry();self.refresh()
    def cancel_selected(self):
        item=self.selected()
        if item:self.queue.cancel_item(item.id);self.refresh()
    def cancel_queue(self):
        self.queue.cancel_all();self.refresh()
    def start(self):
        if self.window.busy() or not any(i.state==WAITING for i in self.queue.items):return
        self.window.start('batch',dict(queue=self.queue,output_dir=self.destination.text().strip() or None,
            common_settings=self.window.settings() if self.mode.currentIndex()==0 else None))
    def set_busy(self,busy):
        for b in self.edit_buttons+[self.start_button]:b.setEnabled(not busy)
    def refresh(self,*_):
        row=self.table.currentRow();self.table.setRowCount(len(self.queue.items))
        for n,item in enumerate(self.queue.items):
            values=[item.source.name,vi.LANGUAGES.get(item.settings.language,item.settings.language),
                vi.voice_label(item.settings.voice),str(item.captions),display_time(item.duration_ms),
                f'{item.progress}%',item.state,item.error or item.output]
            for col,text in enumerate(values):
                cell=QTableWidgetItem(text);cell.setToolTip(str(item.source) if col==0 else text)
                self.table.setItem(n,col,cell)
        if row>=0:self.table.selectRow(row)
        counts={s:sum(i.state==s for i in self.queue.items) for s in [WAITING,RUNNING,DONE,FAILED,CANCELLED]}
        self.summary.setText(f'Tổng số: {len(self.queue.items)} • '+ ' • '.join(f'{s}: {n}' for s,n in counts.items()))
    def open_output(self):
        item=self.selected()
        if item and item.state==DONE and Path(item.output).is_file():QDesktopServices.openUrl(QUrl.fromLocalFile(item.output))
