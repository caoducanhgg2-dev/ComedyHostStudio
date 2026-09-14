import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QMessageBox
from studio.ui import Window
import pytest

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

def test_localized_ui_preserves_ids_and_caption(app,tmp_path):
    w=Window()
    try:
        assert w.settings().language=='English US' and w.settings().voice=='af_heart'
        assert w.settings().emotion=='Natural' and w.settings().effect=='None'
        assert w.language.currentText()=='Tiếng Anh (Mỹ)' and w.generate.text()=='▶  TẠO MP3'
        assert w.language.findData('English UK')>=0
        w.language.setCurrentIndex(w.language.findData('English UK'))
        assert w.language.currentText()=='Tiếng Anh (Anh)'
        assert w.voice.count()==8 and w.voice.findData('bf_emma')>=0
        w.language.setCurrentIndex(w.language.findData('Japanese'))
        w.voice.setCurrentIndex(w.voice.findData('jm_kumo'))
        assert w.settings().voice=='jm_kumo' and 'Kumo' in w.voice.currentText()
        assert w.height()<=w.screen().availableGeometry().height()
        assert not w.preview_buttons[2].isEnabled()
        w.emotion_mode.setCurrentIndex(w.emotion_mode.findData('Auto'))
        assert not w.emotion.isEnabled()
        source=tmp_path/'日本語.srt';source.write_text('1\n00:00:00,000 --> 00:00:04,000\nこれはテストです。',encoding='utf-8')
        w.file.setText(str(source));w.load_captions();w.caption_select.setCurrentIndex(1)
        assert w.preview_buttons[2].isEnabled() and w.preview_text.text()=='これはテストです。'
        w.preview_text.setPlainText('New text')
        assert not w.preview_buttons[2].isEnabled()
    finally:
        w.close();w.deleteLater();app.processEvents()

def test_error_dialog_has_localized_close_button(app,monkeypatch):
    seen=[]
    monkeypatch.setattr(QMessageBox,'exec',lambda box:seen.append((box.button(QMessageBox.Ok).text(),box.text())))
    w=Window()
    try:
        w.show_error('CAPTION 1 TOO LONG','technical details')
        assert seen==[('Đóng','CÂU 1 QUÁ DÀI')]
    finally:
        w.close();w.deleteLater();app.processEvents()

def test_voice_catalog_filters_favorites_and_selects_same_backend(app,tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    w=Window()
    try:
        p=w.voice_panel
        assert p.list.count()==33
        p.filter.setCurrentIndex(p.filter.findData('en'))
        assert p.list.count()==28
        assert any(p.list.item(i).data(256)=='bf_emma' for i in range(p.list.count()))
        p.filter.setCurrentIndex(p.filter.findData('ja'))
        assert p.list.count()==5
        selected=p.selected().id;p.toggle_favorite()
        p.filter.setCurrentIndex(p.filter.findData('favorites'))
        assert p.list.count()==1 and p.selected().id==selected
        p.select_voice()
        assert w.settings().voice==selected and w.settings().language=='Japanese'
        p.filter.setCurrentIndex(p.filter.findData('recommended'))
        assert p.list.count()==0 and 'Chưa có' in p.status.text()
        from studio.preferences import read
        assert read()['favorite_voices']==[selected]
    finally:
        w.close();w.deleteLater();app.processEvents()
