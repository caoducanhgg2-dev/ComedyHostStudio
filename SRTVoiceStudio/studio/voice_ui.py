"""Voice catalogue: installed voices plus visible optional Japanese catalogue."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QListWidget,QListWidgetItem,QLabel,QPushButton,QTextBrowser,QCheckBox,QFileDialog
from . import preferences
from . import ui_text as vi
from .backend import PREVIEW
from .ratings import score,read_csv
from .voice_catalog import catalog_voices,capcut_reference_voices,is_capcut_reference,capcut_reference_meta,CAPCUT_NOTICE


class VoicePanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.setMinimumHeight(590)
        # 1.4.2: the main Japanese voice dropdown must expose the complete
        # catalogue, not just backends whose model files are already installed.
        # Missing Aivis entries stay disabled, so rendering can never route to
        # an unavailable model accidentally.
        try:self.window.language.currentIndexChanged.disconnect(self.window.language_changed)
        except (TypeError,RuntimeError):pass
        self.window.language_changed=self.refresh_main_language
        self.window.language.currentIndexChanged.connect(self.window.language_changed)
        saved=preferences.read().get('favorite_voices',[])
        self.favorites=set(x for x in saved if isinstance(x,str)) if isinstance(saved,list) else set()
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('THƯ VIỆN GIỌNG 1.8.0 • Local TTS + CapCut tham khảo theo thị trường'))
        self.filter=QComboBox()
        for title,value in [('Đề xuất','recommended'),('Đã cài','installed'),('Mỹ / English US','us'),('Anh / English UK','uk'),('Nhật Bản','ja'),('Việt Nam','vi'),('CapCut','capcut'),('Tất cả','all'),('Yêu thích','favorites')]:self.filter.addItem(title,value)
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
        self.accept_license=QCheckBox('Tôi đã đọc và chấp nhận điều kiện của gói Aivis Nhật');layout.addWidget(self.accept_license)
        self.install=QPushButton('Tải / cập nhật gói Aivis Nhật');layout.addWidget(self.install)
        self.accept_license.toggled.connect(self.refresh_install);self.install.clicked.connect(self.install_pack)

        from .korva_pack import LICENSE_NOTICE as KORVA_NOTICE, LICENSE_URL as KORVA_LICENSE_URL
        korva_notice=QLabel(KORVA_NOTICE);korva_notice.setWordWrap(True);layout.addWidget(korva_notice)
        korva_link=QLabel(f'<a style="color:#66b7ff" href="{KORVA_LICENSE_URL}">Đọc giấy phép KorvaTTS / Apache-2.0</a>')
        korva_link.setOpenExternalLinks(True);layout.addWidget(korva_link)
        self.accept_korva=QCheckBox('Tôi đã đọc thông tin giấy phép của gói giọng Việt Korva');layout.addWidget(self.accept_korva)
        self.install_korva=QPushButton('Tải / cập nhật gói Korva Việt');layout.addWidget(self.install_korva)
        self.accept_korva.toggled.connect(self.refresh_install);self.install_korva.clicked.connect(self.install_korva_pack)
        self.filter.currentIndexChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.selection)
        self.use.clicked.connect(self.select_voice);self.favorite.clicked.connect(self.toggle_favorite)
        self.refresh();self.refresh_install()

    def refresh_main_language(self,*_):
        """Populate the main dropdown with installed voices plus Aivis stubs.

        The backend router remains authoritative for synthesis. Catalogue-only
        voices are deliberately disabled until their local model pack exists.
        """
        w=self.window
        language=w.language.currentData()
        installed_list=[v for v in w.backend.list_voices() if v.language==language]
        installed={v.id:v for v in installed_list}
        choices=list(installed_list)
        for voice in catalog_voices(language):
            if voice.id not in installed:choices.append(voice)
        old=w.voice.blockSignals(True)
        w.voice.clear()
        for voice in choices:
            is_installed=voice.id in installed
            if voice.engine=='Kokoro':
                label=vi.voice_label(voice.id)
            elif is_installed:
                label=voice.name+f'  ·  {voice.engine}'
            else:
                label=voice.name+f'  ·  [{voice.engine} • Chưa cài]'
            w.voice.addItem(label,voice.id)
            index=w.voice.count()-1
            w.voice.setItemData(index,
                'Sẵn sàng dùng offline' if is_installed else
                f'Chưa cài model {voice.engine} • Mở tab Thư viện giọng để cài gói phù hợp',
                Qt.ToolTipRole)
            if not is_installed:
                item=w.voice.model().item(index)
                if item is not None:item.setEnabled(False)
        if not installed_list:
            w.voice.setCurrentIndex(-1)
        w.voice.blockSignals(old)
        missing=max(0,len(choices)-len(installed_list))
        if missing:
            w.voice_count.setText(
                f'{len(choices)} giọng · {len(installed_list)} đã cài · {missing} chưa cài')
        else:
            w.voice_count.setText(f'{len(choices)} giọng · Chạy trên CPU')
        if w.caption_select.currentData() is None:w.preview_text.setText(PREVIEW[language])
        w.voice_changed();w.invalidate_base()

    def refresh_install(self):
        installed=self.window.aivis_pack.available();complete=self.window.aivis_pack.complete()
        if complete:text='Aivis Nhật đã đầy đủ • 11/11 giọng tùy chọn • offline'
        elif installed:text='Cập nhật Aivis Nhật • bổ sung từ 6 lên 11 giọng'
        else:text='Tải Aivis Nhật • 11 giọng tùy chọn • offline sau khi tải'
        self.install.setText(text)
        self.install.setEnabled(not complete and not self.window.busy() and self.accept_license.isChecked())

        korva_complete=self.window.korva_pack.complete()
        self.install_korva.setText(
            'Korva Việt đã đầy đủ • 10/10 giọng • offline'
            if korva_complete else 'Tải Korva Việt • 10 giọng • khoảng 400 MB')
        self.install_korva.setEnabled(
            not korva_complete and not self.window.busy() and self.accept_korva.isChecked())

    def install_pack(self):
        if self.window.busy() or not self.accept_license.isChecked():return
        self.window.start('install_aivis',dict(pack=self.window.aivis_pack))

    def install_korva_pack(self):
        if self.window.busy() or not self.accept_korva.isChecked():return
        self.window.start('install_korva',dict(pack=self.window.korva_pack))

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
        for voice in capcut_reference_voices():self.voices.setdefault(voice.id,voice)
        saved=preferences.read().get('voice_ratings',{});self.ratings=saved if isinstance(saved,dict) else {}
        mode=self.filter.currentData();self.list.clear()
        for voice in self.voices.values():
            is_installed=voice.id in self.installed_ids
            rating=score(self.ratings.get(voice.id))
            if mode=='recommended' and (not is_installed or rating is None or rating<8):continue
            if mode=='installed' and not is_installed:continue
            if mode=='us' and voice.language!='English US':continue
            if mode=='uk' and voice.language!='English UK':continue
            if mode=='ja' and voice.language!='Japanese':continue
            if mode=='vi' and voice.language!='Vietnamese':continue
            if mode=='capcut' and not is_capcut_reference(voice):continue
            if mode=='favorites' and voice.id not in self.favorites:continue
            label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
            assessment='Chưa chấm' if rating is None else f'{rating:.2f}/10 · Điểm nghe do người dùng cung cấp'
            if is_capcut_reference(voice):state='CapCut tham khảo • dùng trong CapCut • không render trực tiếp'
            else:state='Đã cài • dùng offline' if is_installed else f'Chưa cài • cần gói {voice.engine}'
            item=QListWidgetItem(f"{'★ ' if voice.id in self.favorites else ''}{label}  ·  {vi.display(voice.language)}  ·  {voice.engine}\n{state} • {assessment}")
            item.setData(Qt.UserRole,voice.id);self.list.addItem(item)
            if voice.id==previous:self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentRow()<0:self.list.setCurrentRow(0)
        if mode=='recommended' and not self.list.count():
            text='Chưa có giọng đủ kết quả nghe kiểm chứng để gắn nhãn Đề xuất.'
        elif mode in ('us','uk','ja','vi'):
            language={'us':'English US','uk':'English UK','ja':'Japanese','vi':'Vietnamese'}[mode]
            label={'us':'Mỹ','uk':'Anh','ja':'Nhật','vi':'Việt'}[mode]
            installed_count=sum(1 for v in self.voices.values()
                                if v.language==language and v.id in self.installed_ids)
            total_count=sum(1 for v in self.voices.values() if v.language==language)
            reference_count=sum(1 for v in self.voices.values() if v.language==language and is_capcut_reference(v))
            local_pending=max(0,total_count-installed_count-reference_count)
            text=f'{total_count} giọng {label} • {installed_count} đã cài • {local_pending} chờ model • {reference_count} CapCut tham khảo.'
        elif mode=='capcut':
            text=f'{self.list.count()} profile CapCut • phân theo thị trường • availability tùy tài khoản/khu vực/phiên bản.'
        else:
            text=f'{self.list.count()} giọng • Chú thích đặc tính chỉ để chọn nhanh; không phải điểm chất lượng.'
        self.status.setText(text);self.selection()

    def selection(self,*_):
        import html
        voice=self.selected();is_installed=bool(voice and voice.id in self.installed_ids)
        reference=bool(voice and is_capcut_reference(voice))
        self.use.setEnabled(bool(voice) and is_installed and not reference and not self.window.busy());self.favorite.setEnabled(bool(voice))
        self.use.setText('Dùng giọng này' if is_installed and not reference else
                         'Dùng tên này trong CapCut' if reference else
                         f'Chưa cài • cần gói {voice.engine}' if voice else 'Chưa cài')
        if not voice:self.details.clear();return
        esc=html.escape;rating=score(self.ratings.get(voice.id))
        assessment='Điểm tự nhiên, phát âm và biểu cảm: chưa được nghe chấm. Chú thích đặc tính chỉ là mô tả tham khảo, không thay cho điểm chất lượng.'
        if rating is not None:
            record=self.ratings[voice.id];assessment=f'Điểm nghe do người dùng cung cấp: {rating:.2f}/10. Người chấm: {esc(record["reviewer"])}. {esc(record.get("notes", ""))}'
        self.favorite.setText('★ Bỏ yêu thích' if voice.id in self.favorites else '☆ Thêm yêu thích')
        label=vi.voice_label(voice.id) if voice.engine=='Kokoro' else voice.name
        state=('CapCut tham khảo • tìm/chọn trong CapCut; không render trực tiếp bằng SRT Voice Studio' if reference else
               'Đã cài • sẵn sàng dùng offline' if is_installed else f'Chưa cài • cần tải gói {voice.engine}')
        trait=vi.voice_characteristic(voice.id)
        trait_line=f'<br>Chú thích: {esc(trait)}' if trait else ''
        meta=capcut_reference_meta(voice) if reference else {}
        capcut_detail=(f'<br>Thị trường: {esc(meta.get("market",""))}'
                       f'<br>Phù hợp: {esc(meta.get("use_case",""))}'
                       f'<br><b>Lưu ý CapCut:</b> {esc(CAPCUT_NOTICE)}') if reference else ''
        self.details.setHtml(f'<b>{esc(label)}</b><p>Trạng thái: {esc(state)}<br>Mã giọng: {esc(voice.id)}<br>Bộ tạo giọng: {esc(voice.engine)}<br>Ngôn ngữ: {esc(vi.display(voice.language))}{trait_line}{capcut_detail}<br>Giấy phép / điều khoản: {esc(voice.license)}</p>'
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
