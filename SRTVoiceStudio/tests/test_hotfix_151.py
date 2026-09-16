import gc
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from studio.hotfix_151 import stabilize_qactions
from studio.ui import Window
from studio.v15_upgrade import enhance_window


def test_diagnostic_action_survives_menu_wrapper_collection():
    app = QApplication.instance() or QApplication([])
    window = stabilize_qactions(enhance_window(Window()))
    try:
        gc.collect()
        app.processEvents()
        assert isValid(window.help_menu)
        assert isValid(window.diagnostic_action)
        window.diagnostic_action.setEnabled(False)
        assert not window.diagnostic_action.isEnabled()
        window.diagnostic_action.setEnabled(True)
        assert window.diagnostic_action.isEnabled()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
