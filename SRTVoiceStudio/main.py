import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from studio import __version__
from studio.paths import data_dir, clean_stale, workspace

def main():
    # Set only this process's environment; never modify Windows user settings.
    for key in ('TEMP','TMP','TMPDIR'):
        os.environ[key] = str(workspace())
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    app.setApplicationName('SRT Voice Studio')
    app.setApplicationVersion(__version__)
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
        logging.info('SRT Voice Studio %s', __version__)
        clean_stale()
        # 1.6.1 patches Auto SFX before render/UI import so every path, including
        # frozen self-tests, uses the audibility-tuned mixer and synthesis.
        from studio.sfx_161 import apply_patch
        apply_patch()
        for name in ('batch','underfill-v2','install-voice','optional-voices','voice-benchmark'):
            if '--'+name+'-test' in sys.argv:
                from studio.upgrade_checks import run_test
                return run_test(name)
        if '--sfx-test' in sys.argv:
            from studio.sfx import self_test
            return self_test()
        if '--underfill-test' in sys.argv:
            from studio.underfill_checks import underfill_test
            return underfill_test()
        if '--stress-test' in sys.argv:
            from studio.stress import stress_test
            return stress_test()
        if '--self-test' in sys.argv:
            from studio.diagnostics import self_test
            return self_test()
        from studio.ui import Window
        from studio.v17_upgrade import enhance_window_v17
        from studio.hotfix_151 import stabilize_qactions
        window = stabilize_qactions(enhance_window_v17(Window()))
        window.show()
        if '--ui-smoke' in sys.argv:
            from studio.ui_checks import UiChecks
            checks = UiChecks(app, window)
        return app.exec()
    except Exception as exc:
        logging.exception('Startup error')
        if not any(arg.endswith('-test') for arg in sys.argv):
            QMessageBox.critical(None, 'Không mở được ứng dụng', str(exc))
        return 1
    finally:
        lock.unlock()

if __name__ == '__main__':
    raise SystemExit(main())
