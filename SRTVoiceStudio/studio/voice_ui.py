"""Voice catalogue: installed voices plus visible optional Japanese catalogue."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QListWidget,QListWidgetItem,QLabel,QPushButton,QTextBrowser,QCheckBox,QFileDialog
from . import preferences
from . import ui_text as vi
from .ratings import score,read_csv
from .voice_catalog import catalog_voices


class VoicePanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.setMinimumHeight(590)
        saved=preferences.read().get('favorite_voices',[])
        self.favorites=set(x for x in saved if isinstance(x,str)) if isinstance(saved,list) else set()
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('THƯ VIỆN GIỌNG • Giọng tùy chọn vẫn hiện trước khi tải model để bạn biết chính xác bản này có gì'))
        self.filter=QComboBox()
        for title,value in [('Đề xuất','recommended'),('Đã cài','installed'),('Tiếng Anh','en'),('Tiếng Nhật','ja'),('Tất cả','all'),('Yêu thích','favorites')]:self.filter.addItem(title,value)
        self.filter.setCurrentIndex(1);layout.addWidget(self.filter)
        self.list=QListWidget();layout.addWidget(self.list,2)
        self.details=QTextBrowser();self.details.setOpenExternalLinks(True);layout.addWidget(self.details,1)
        row=QHBoxLayout();self.use=QPushButton('Dùng giọng này');self.favorite=QPushButton('☆ Thêm yêu thích')
        row.addWidget(self.use);row.addWidget(self.favorite);layout.addLayout(row)
        self.import_scores=QPushButton('Nạp điểm nghe từ ratings.csv');layout.addWidget(self.import_scores)
        self.import_scores.clicked.connect(self.load_ratings)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        from .aivis_pack import LICENSE_NOTICE,LICENSE_URL
        notice=QLabel(LICENSE_NOTICE);notice.setWordWrap(True);layout.addWidget(notice)
        link=QLabel(f'<a style="color:#66b7ff" href="{LICENSE_URL}">Đọc giấy phép ACML đầy đủ</a>');link.setOpenExternalLinks(True);layout.addWidget(link)
        self.accept_license=QCheckBox('Tôi đã đọc và chấp nhận các điều kiện sử dụng gói Aivis');layout.addWidget(self.accept_license)
        self.install=QPushButton('Tải / cập nhật gói Aivis Nhật');layout.addWidget(self.install)
        self.accept_license.toggled.connect(self.refresh_install);self.install.clicked.connect(self.install_pack)
        self.filter.currentIndexChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.selection)
        self.use.clicked.connect(self.select_voice);self.favorite.clicked.connect(self.toggle_favorite)
        self.refresh();self.refresh_install()

    def refresh_install(self):
        installed=self.window.aivis_pack.available();complete=self.window.aivis_pack.complete()
        if complete:text='Aivis Nhật đã đầy đủ • 6/6 giọng • dùng offline'
        elif installed:text='Cập nhật Aivis Nhật • bổ sung đủ 6 giọng'
        else:text='Tải Aivis Nhật • 6 giọng • sau khi tải dùng offline'
        self.install.setText(text)
        self.install.setEnabled(not complete and not self.window.busy() and self.accept_license.isChecked())

    def install_pack(self):
        if self.window.busy() or not self.accept_license.isChecked():return
        self.window.start('install_aivis',dict(pack=self.window.aivis_pack))

    def selected(self):
        item=self.list.currentItem();return self.voices.get(item.data(Qt.UserRole)) if item else None

    def refresh(self):
        previous=self.selected().id if hasattr(self,'voices') and self.selected() else None
        installed={v.id:v for v in self.window.backend.list_voices()}
        self.installed_ids=set(installed)
        # Keep real registered backend metadata authoritative. Catalogue entries
        # are only added when the corresponding optional voice is not installed.
        self.voices=dict(installed)
        for voice in catalog_voices():self.voices.setdefault(voice.id,voice)
        saved=preferences.read().get('voice_ratings',{});self.ratings=saved if isinstance(saved,dict) else {}
        mode=self.filter.currentData();self.list.clear()
        for voice in self.voices.values():
            is_installed=voice.id in self.installed_ids
            rating=score(self.ratings.get(voice.id))
            if mode=='recommended' and (not is_installed or rating is None or rating<8):continue
            if mode=='installed' and not is_installed:continue
            if mode=='en' and voice.language not in ('English US','English UK'):continue
            if mode=='ja' and voice.language!='Japanese':continue
            if mode=='favorites' and voice.id not in self.favorites:continue
            label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
            assessment='Chưa chấm' if rating is None else f'{rating:.2f}/10 · Điểm nghe do người dùng cung cấp'
            state='Đã cài • dùng offline' if is_installed else 'Chưa cài • tải gói Aivis Nhật để dùng'
            item=QListWidgetItem(f"{'★ ' if voice.id in self.favorites else ''}{label}  ·  {vi.display(voice.language)}  ·  {voice.engine}\n{state} • {assessment}")
            item.setData(Qt.UserRole,voice.id);self.list.addItem(item)
            if voice.id==previous:self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentRow()<0:self.list.setCurrentRow(0)
        if mode=='recommended' and not self.list.count():
            text='Chưa có giọng đủ kết quả nghe kiểm chứng để gắn nhãn Đề xuất.'
        elif mode=='ja':
            installed_ja=sum(1 for v in self.voices.values() if v.language=='Japanese' and v.id in self.installed_ids)
            total_ja=sum(1 for v in self.voices.values() if v.language=='Japanese')
            text=f'{total_ja} giọng Nhật trong bản 1.4.1 • {installed_ja} đã cài • {total_ja-installed_ja} chờ tải model.'
        else:
            text=f'{self.list.count()} giọng • Chú thích đặc tính chỉ để chọn nhanh; không phải điểm chất lượng.'
        self.status.setText(text);self.selection()

    def selection(self,*_):
        import html
        voice=self.selected();is_installed=bool(voice and voice.id in self.installed_ids)
        self.use.setEnabled(bool(voice) and is_installed and not self.window.busy());self.favorite.setEnabled(bool(voice))
        self.use.setText('Dùng giọng này' if is_installed else 'Chưa cài • tải Aivis để dùng')
        if not voice:self.details.clear();return
        esc=html.escape;rating=score(self.ratings.get(voice.id))
        assessment='Điểm tự nhiên, phát âm và biểu cảm: chưa được nghe chấm. Chú thích đặc tính chỉ là mô tả tham khảo, không thay cho điểm chất lượng.'
        if rating is not None:
            record=self.ratings[voice.id];assessment=f'Điểm nghe do người dùng cung cấp: {rating:.2f}/10. Người chấm: {esc(record["reviewer"])}. {esc(record.get("notes", ""))}'
        self.favorite.setText('★ Bỏ yêu thích' if voice.id in self.favorites else '☆ Thêm yêu thích')
        label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
        state='Đã cài • sẵn sàng dùng offline' if is_installed else 'Chưa cài • cần tải gói Aivis Nhật một lần'
        trait=vi.voice_characteristic(voice.id)
        trait_line=f'<br>Chú thích: {esc(trait)}' if trait else ''
        self.details.setHtml(f'<b>{esc(label)}</b><p>Trạng thái: {esc(state)}<br>Mã giọng: {esc(voice.id)}<br>Bộ tạo giọng: {esc(voice.engine)}<br>Ngôn ngữ: {esc(vi.display(voice.language))}{trait_line}<br>Giấy phép: {esc(voice.license)}</p>'
            f'<p>Nguồn: <a href="{esc(voice.source,quote=True)}">{esc(voice.source)}</a></p><p>{assessment}</p>')

    def load_ratings(self):
        if self.window.busy():return
        path,_=QFileDialog.getOpenFileName(self,'Chọn bảng điểm nghe','','Bảng điểm CSV (*.csv)')
        if not path:return
        try:
            records=read_csv(path,set(self.voices));value=preferences.read();existing=value.get('voice_ratings',{})
            existing=dict(existing) if isinstance(existing,dict) else {};existing.update(records);value['voice_ratings']=existing
            preferences.write(value);self.refresh()
        except Exception as exc:self.window.show_error(str(exc),'Không thay đổi điểm đã lưu.')

    def select_voice(self):
        if self.window.busy():return
        voice=self.selected()
        if not voice or voice.id not in self.installed_ids:return
        self.window.language.setCurrentIndex(self.window.language.findData(voice.language))
        index=self.window.voice.findData(voice.id)
        if index>=0:self.window.voice.setCurrentIndex(index)
        self.window.tabs.setCurrentIndex(0)

    def toggle_favorite(self):
        voice=self.selected()
        if not voice:return
        if voice.id in self.favorites:self.favorites.remove(voice.id)
        else:self.favorites.add(voice.id)
        value=preferences.read();value['favorite_voices']=sorted(self.favorites);preferences.write(value);self.refresh()