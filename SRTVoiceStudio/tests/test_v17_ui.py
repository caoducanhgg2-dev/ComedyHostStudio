import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _window(app, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    from studio.sfx_161 import apply_patch
    apply_patch()
    from studio.ui import Window
    from studio.v17_upgrade import enhance_window_v17
    return enhance_window_v17(Window())


def test_17_workspace_exposes_shared_smartfit_cache_and_multiselect(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        assert w.smart_fit3.isChecked()
        assert w.render_cache_enabled.isChecked()
        settings = w.settings()
        assert settings.smart_fit3 is True
        assert settings.use_render_cache is True
        assert w.multi_file_panel.table.selectionMode() != w.multi_file_panel.table.SingleSelection
        assert w.multi_file_panel.select_all_button.text() == "Chọn tất cả"
        assert "TTS" in w.multi_file_panel.retry_caption_button.text()
    finally:
        w.close()


def test_17_retry_caption_invalidates_only_selected_cache(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        srt = tmp_path / "a.srt"
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n完成しました。\n\n"
            "2\n00:00:02,100 --> 00:00:04,000\n次へ進みます。\n",
            encoding="utf-8")
        w.multi_file_panel.add_paths([srt])
        w.caption_select.setCurrentIndex(1)
        from studio.render_cache import TtsCache
        cache = TtsCache()
        settings = w.settings()
        first = w.captions[0]
        second = w.captions[1]
        audio = np.ones(2400, dtype=np.float32) * .02
        cache.put(settings, first.text, audio, 48000)
        cache.put(settings, second.text, audio, 48000)
        assert cache.get(settings, first.text) is not None
        assert cache.get(settings, second.text) is not None
        w.multi_file_panel.retry_caption_button.click()
        assert cache.get(settings, first.text) is None
        assert cache.get(settings, second.text) is not None
    finally:
        w.close()
