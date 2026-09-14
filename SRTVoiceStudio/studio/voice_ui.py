"""Voice catalogue: license provenance and honest pending listening status."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QListWidget,QListWidgetItem,QLabel,QPushButton,QTextBrowser,QCheckBox
from . import preferences
from . import ui_text as vi


class VoicePanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.setMinimumHeight(590)
        saved=preferences.read().get('favorite_voices',[])
        self.favorites=set(x for x in saved if isinstance(x,str)) if isinstance(saved,list) else set()
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('THƯ VIỆN GIỌNG • Danh tính giọng và giấy phép được lưu riêng với cấu hình xử lý'))
        self.filter=QComboBox()
        for title,value in [('Đề xuất','recommended'),('Đã cài','installed'),('Tiếng Anh','en'),('Tiếng Nhật','ja'),('Tất cả','all'),('Yêu thích','favorites')]:self.filter.addItem(title,value)
        self.filter.setCurrentIndex(1);layout.addWidget(self.filter)
        self.list=QListWidget();layout.addWidget(self.list,2)
        self.details=QTextBrowser();self.details.setOpenExternalLinks(True);layout.addWidget(self.details,1)
        row=QHBoxLayout();self.use=QPushButton('Dùng giọng này');self.favorite=QPushButton('☆ Thêm yêu thích')
        row.addWidget(self.use);row.addWidget(self.favorite);layout.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        from .aivis_pack import LICENSE_NOTICE,LICENSE_URL
        notice=QLabel(LICENSE_NOTICE);notice.setWordWrap(True);layout.addWidget(notice)
        link=QLabel(f'<a style="color:#66b7ff" href="{LICENSE_URL}">Đọc giấy phép ACML đầy đủ</a>');link.setOpenExternalLinks(True);layout.addWidget(link)
        self.accept_license=QCheckBox('Tôi đã đọc và chấp nhận các điều kiện sử dụng gói Aivis');layout.addWidget(self.accept_license)
        self.install=QPushButton('Tải gói thử nghiệm Aivis • Mao + Kohaku');layout.addWidget(self.install)
        self.accept_license.toggled.connect(self.refresh_install);self.install.clicked.connect(self.install_pack)
        self.filter.currentIndexChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.selection)
        self.use.clicked.connect(self.select_voice);self.favorite.clicked.connect(self.toggle_favorite)
        self.refresh()
        self.refresh_install()

    def refresh_install(self):
        installed=self.window.aivis_pack.available()
        self.install.setText('Gói Aivis đã cài' if installed else 'Tải gói thử nghiệm Aivis • Mao + Kohaku')
        self.install.setEnabled(not installed and not self.window.busy() and self.accept_license.isChecked())

    def install_pack(self):
        if self.window.busy() or not self.accept_license.isChecked():return
        self.window.start('install_aivis',dict(pack=self.window.aivis_pack))

    def selected(self):
        item=self.list.currentItem()
        return self.voices.get(item.data(Qt.UserRole)) if item else None

    def refresh(self):
        previous=self.selected().id if hasattr(self,'voices') and self.selected() else None
        self.voices={v.id:v for v in self.window.backend.list_voices()}
        mode=self.filter.currentData();self.list.clear()
        for voice in self.voices.values():
            if mode=='recommended':continue  # No fabricated >=8/10 quality scores.
            if mode=='en' and voice.language!='English US':continue
            if mode=='ja' and voice.language!='Japanese':continue
            if mode=='favorites' and voice.id not in self.favorites:continue
            label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
            item=QListWidgetItem(f"{'★ ' if voice.id in self.favorites else ''}{label}  ·  {vi.display(voice.language)}  ·  {voice.engine}\nĐã cài • Đánh giá nghe: chưa xác nhận")
            item.setData(Qt.UserRole,voice.id);self.list.addItem(item)
            if voice.id==previous:self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentRow()<0:self.list.setCurrentRow(0)
        self.status.setText('Chưa có giọng đủ kết quả nghe kiểm chứng để gắn nhãn Đề xuất.' if mode=='recommended' else f'{self.list.count()} giọng • Các phong cách bản địa không được tính thành giọng mới.')
        self.selection()

    def selection(self,*_):
        import html
        voice=self.selected();self.use.setEnabled(bool(voice));self.favorite.setEnabled(bool(voice))
        if not voice:self.details.clear();return
        esc=html.escape
        self.favorite.setText('★ Bỏ yêu thích' if voice.id in self.favorites else '☆ Thêm yêu thích')
        self.details.setHtml(f'<b>{esc(voice.name)}</b><p>Mã giọng: {esc(voice.id)}<br>Bộ tạo giọng: {esc(voice.engine)}<br>Ngôn ngữ: {esc(vi.display(voice.language))}<br>Giấy phép: {esc(voice.license)}</p>'
            f'<p>Nguồn: <a href="{esc(voice.source,quote=True)}">{esc(voice.source)}</a></p>'
            '<p>Điểm tự nhiên, phát âm và biểu cảm: chưa được nghe chấm. Không dùng thông số kỹ thuật thay cho điểm chất lượng.</p>')

    def select_voice(self):
        if self.window.busy():return
        voice=self.selected()
        if not voice:return
        self.window.language.setCurrentIndex(self.window.language.findData(voice.language))
        self.window.voice.setCurrentIndex(self.window.voice.findData(voice.id))
        self.window.tabs.setCurrentIndex(0)

    def toggle_favorite(self):
        voice=self.selected()
        if not voice:return
        if voice.id in self.favorites:self.favorites.remove(voice.id)
        else:self.favorites.add(voice.id)
        value=preferences.read();value['favorite_voices']=sorted(self.favorites);preferences.write(value)
        self.refresh()
