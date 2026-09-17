import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def _write_srt(path: Path, text='テストです。'):
    path.write_text(
        '1\n00:00:00,000 --> 00:00:02,000\n' + text + '\n',
        encoding='utf-8')
    return path


def _window(app, tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    from studio.sfx_161 import apply_patch
    apply_patch()
    from studio.ui import Window
    from studio.v161_upgrade import enhance_window_v161
    return enhance_window_v161(Window())


def test_batch_tab_is_merged_into_first_tab(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        tabs = [w.tabs.tabText(i) for i in range(w.tabs.count())]
        assert all('Hàng đợi xử lý' not in text for text in tabs)
        assert '1 hoặc nhiều' in w.tabs.tabText(0)
        assert hasattr(w, 'multi_file_panel')
        assert w.tabs.indexOf(w.batch_panel) == -1
        assert w.file.isReadOnly()
        assert 'nhiều SRT' in w.findChild(type(w.file_info), 'appSubtitle').text()
    finally:
        w.close()


def test_multiple_files_share_current_settings_and_active_row_drives_preview(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        a = _write_srt(tmp_path / 'a.srt', '完成しました。')
        b = _write_srt(tmp_path / 'b.srt', '次はここです。')
        added = w.multi_file_panel.add_paths([a, b])
        assert len(added) == 2
        assert len(w.multi_file_panel.queue.items) == 2
        assert '2 TỆP' in w.generate.text()

        w.multi_file_panel.table.selectRow(1)
        w.multi_file_panel.activate_selected()
        assert Path(w.file.text()) == b.resolve()
        assert len(w.captions) == 1
        assert w.captions[0].text == '次はここです。'

        w.speed.setValue(1.07)
        w.sfx_panel.enabled.setChecked(True)
        captured = {}
        def fake_start(task, params):
            captured['task'] = task
            captured['params'] = params
        w.start = fake_start
        w.multi_file_panel.start()
        assert captured['task'] == 'batch'
        common = captured['params']['common_settings']
        assert common.speed == pytest.approx(1.07)
        assert common.auto_sfx is True
        assert all(item.settings.speed == pytest.approx(1.07) for item in w.multi_file_panel.queue.items)
        assert all(item.settings.auto_sfx is True for item in w.multi_file_panel.queue.items)
    finally:
        w.close()


def test_shared_mode_has_no_per_item_editing_and_retry_keeps_queue(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        a = _write_srt(tmp_path / 'one.srt')
        b = _write_srt(tmp_path / 'two.srt')
        w.multi_file_panel.add_paths([a, b])
        # The legacy per-item editor exists only inside the hidden compatibility panel.
        assert w.tabs.indexOf(w.batch_panel) == -1
        assert 'cấu hình dùng chung' in w.multi_file_panel.summary.text()
        first = w.multi_file_panel.queue.items[0]
        from studio.batch import FAILED, WAITING
        first.state = FAILED
        first.error = 'test failure'
        w.multi_file_panel.retry_failed()
        assert first.state == WAITING
        assert first.error == ''
    finally:
        w.close()
