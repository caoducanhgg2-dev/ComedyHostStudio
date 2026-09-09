import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from studio.paths import data_dir, clean_stale, workspace

def main():
    # Set only this process's environment; never modify Windows user settings.
    for key in ('TEMP','TMP','TMPDIR'):
        os.environ[key] = str(workspace())
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    app.setApplicationName('SRT Voice Studio')
    lock = QLockFile(str(data_dir()/'instance.lock'))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, 'SRT Voice Studio', 'Ứng dụng đã mở. Hãy kiểm tra thanh tác vụ.')
        return 0
    logdir = data_dir()/'logs'
    logdir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(logdir/'latest.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    try:
        clean_stale()
        if '--self-test' in sys.argv:
            from studio.diagnostics import self_test
            return self_test()
        from studio.ui import Window
        window = Window()
        window.show()
        if '--ui-smoke' in sys.argv:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, app.quit)
        return app.exec()
    except Exception as exc:
        logging.exception('Startup error')
        if '--self-test' not in sys.argv:
            QMessageBox.critical(None, 'Không mở được ứng dụng', str(exc))
        return 1
    finally:
        lock.unlock()

if __name__ == '__main__':
    raise SystemExit(main())
