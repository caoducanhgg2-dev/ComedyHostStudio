import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel
from studio.ui import Window
from studio import ui_text as vi
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
        subtitle=w.findChild(QLabel,'appSubtitle')
        assert subtitle is not None and subtitle.text().startswith('Tiếng Anh (Mỹ / Anh) / Tiếng Nhật')
        assert w.language.findData('English UK')>=0
        assert w.gap.currentData()==-1 and 'Tự động' in w.gap.currentText()
        w.language.setCurrentIndex(w.language.findData('English UK'))
        assert w.language.currentText()=='Tiếng Anh (Anh)'
        assert w.voice.count()==8 and w.voice.findData('bf_emma')>=0
        w.language.setCurrentIndex(w.language.findData('Japanese'))
        # 1.7.1: 5 Kokoro + 11 optional Aivis voices stay visible before install.
        assert w.voice.count()==16
        rinne=w.voice.findData('aivis:d2c99ca6-73e5-486c-994e-ee0ce2d74928')
        assert rinne>=0 and 'Rinne El' in w.voice.itemText(rinne) and 'Chưa cài' in w.voice.itemText(rinne)
        assert not w.voice.model().item(rinne).isEnabled()
        assert '16 giọng' in w.voice_count.text() and '11 chưa cài' in w.voice_count.text()
        w.voice.setCurrentIndex(w.voice.findData('jm_kumo'))
        assert w.settings().voice=='jm_kumo'
        assert 'Kumo' in w.voice.currentText() and 'Trầm vừa' in w.voice.currentText()
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

def test_voice_characteristic_labels_are_reference_hints_for_all_regions():
    assert vi.voice_label('jf_alpha')=='Alpha — Nữ · Sáng, trẻ trung, linh hoạt'
    assert 'hợp kể chuyện' in vi.voice_label('jf_gongitsune')
    assert 'hoạt hình' in vi.voice_label('jf_nezumi')
    assert 'điềm tĩnh' in vi.voice_label('jf_tebukuro')
    assert 'hợp thuyết minh' in vi.voice_label('jm_kumo')
    assert vi.voice_characteristic('af_heart')=='Ấm, thân thiện, tự nhiên'
    assert 'reviewer / comedy' in vi.voice_label('am_puck')
    assert 'thanh lịch' in vi.voice_label('bf_alice')
    assert 'chững chạc' in vi.voice_label('bm_george')

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
        # Default "Đã cài" remains 33 local Kokoro voices before Aivis install.
        assert p.list.count()==33
        p.filter.setCurrentIndex(p.filter.findData('us'))
        # US: 20 installed Kokoro + 12 CapCut reference profiles.
        assert p.list.count()==32
        assert any(p.list.item(i).data(256)=='af_heart' for i in range(p.list.count()))
        assert any('thân thiện' in p.list.item(i).text() for i in range(p.list.count()))
        assert any(p.list.item(i).data(256)=='capcut:us:jessie' for i in range(p.list.count()))
        assert '20 đã cài' in p.status.text() and '12 CapCut tham khảo' in p.status.text()

        p.filter.setCurrentIndex(p.filter.findData('uk'))
        # UK: 8 installed Kokoro + 6 CapCut reference profiles.
        assert p.list.count()==14
        assert any(p.list.item(i).data(256)=='bf_emma' for i in range(p.list.count()))
        assert any(p.list.item(i).data(256)=='capcut:uk:witty' for i in range(p.list.count()))
        assert '8 đã cài' in p.status.text() and '6 CapCut tham khảo' in p.status.text()

        p.filter.setCurrentIndex(p.filter.findData('ja'))
        # Japan: 5 installed Kokoro + 11 optional Aivis + 6 CapCut reference profiles.
        assert p.list.count()==22
        assert '22 giọng Nhật' in p.status.text() and '5 đã cài' in p.status.text()
        assert '11 chờ model' in p.status.text() and '6 CapCut tham khảo' in p.status.text()
        assert any('Sáng, trẻ trung' in p.list.item(i).text() for i in range(p.list.count()))
        assert any('Trầm vừa' in p.list.item(i).text() for i in range(p.list.count()))
        assert any('Rinne El' in p.list.item(i).text() and 'Chưa cài' in p.list.item(i).text() for i in range(p.list.count()))
        assert any('Aida Shigeru' in p.list.item(i).text() and 'Chưa cài' in p.list.item(i).text() for i in range(p.list.count()))
        capcut_index=next(i for i in range(p.list.count()) if p.list.item(i).data(256)=='capcut:jp:anime_girl')
        p.list.setCurrentRow(capcut_index)
        assert not p.use.isEnabled()
        assert 'CapCut tham khảo' in p.details.toPlainText()

        p.filter.setCurrentIndex(p.filter.findData('vi'))
        # Vietnam: 10 optional Korva + 7 CapCut reference profiles before Korva install.
        assert p.list.count()==17
        assert '17 giọng Việt' in p.status.text() and '0 đã cài' in p.status.text()
        assert '10 chờ model' in p.status.text() and '7 CapCut tham khảo' in p.status.text()
        assert any(p.list.item(i).data(256)=='korva:bao_kim' for i in range(p.list.count()))
        assert any(p.list.item(i).data(256)=='capcut:vn:confident_male' for i in range(p.list.count()))

        p.filter.setCurrentIndex(p.filter.findData('capcut'))
        assert p.list.count()==31
        assert '31 profile CapCut' in p.status.text()
        assert all(str(p.list.item(i).data(256)).startswith('capcut:') for i in range(p.list.count()))

        p.filter.setCurrentIndex(p.filter.findData('ja'))
        # Pick an installed Kokoro voice to verify favorite/use behavior remains intact.
        installed_index=next(i for i in range(p.list.count()) if p.list.item(i).data(256)=='jf_alpha')
        p.list.setCurrentRow(installed_index)
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
