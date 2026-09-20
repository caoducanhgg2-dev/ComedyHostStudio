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


def test_sfx_editor_is_per_file_and_disabled_cue_stays_reversible(app, tmp_path, monkeypatch):
    w = _window(app, tmp_path, monkeypatch)
    try:
        first = tmp_path / "first.srt"
        second = tmp_path / "second.srt"
        first.write_text("1\n00:00:00,000 --> 00:00:03,000\nついに完成しました。\n", encoding="utf-8")
        second.write_text("1\n00:00:00,000 --> 00:00:03,000\n次はここです。\n", encoding="utf-8")
        w.multi_file_panel.add_paths([first, second])

        w.multi_file_panel.table.selectRow(0)
        w.multi_file_panel.activate_selected()
        w.sfx_editor_panel.refresh()
        assert w.sfx_editor_panel.table.rowCount() >= 1

        first_item = w.multi_file_panel.queue.items[0]
        second_item = w.multi_file_panel.queue.items[1]
        from studio.batch import DONE, WAITING
        first_item.state = DONE
        w.sfx_editor_panel.table.selectRow(0)
        w.sfx_editor_panel.enabled.setChecked(False)
        w.sfx_editor_panel.apply_selected()
        assert first_item.state == WAITING
        assert len(first_item.sfx_overrides) == 1
        assert first_item.sfx_overrides[0]["enabled"] is False
        assert second_item.sfx_overrides == ()
        assert w.sfx_editor_panel.table.rowCount() >= 1
        assert "Tắt thủ công" in w.sfx_editor_panel.table.item(0, 3).text()

        w.sfx_editor_panel.table.selectRow(0)
        w.sfx_editor_panel.reset_selected()
        assert first_item.sfx_overrides == ()
    finally:
        w.close()


def test_sfx_overrides_survive_queue_save_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    source = tmp_path / "persist.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:02,500\n完成しました。\n", encoding="utf-8")
    from studio.batch import BatchQueue
    from studio.render import Settings
    from studio.v15_core import save_batch_queue, load_batch_queue

    q = BatchQueue()
    item = q.add([source], Settings(language="Japanese", voice="jf_alpha"))[0]
    item.sfx_overrides = ({"caption": 1, "enabled": True, "kind": "comic",
                           "offset_ms": 100, "gain_scale": 1.3},)
    state = tmp_path / "queue.json"
    save_batch_queue(q, state)
    restored = load_batch_queue(state)
    assert len(restored.items) == 1
    assert restored.items[0].sfx_overrides[0]["kind"] == "comic"
    assert restored.items[0].sfx_overrides[0]["gain_scale"] == 1.3
