"""Post-update smoke check; called with an isolated LOCALAPPDATA directory."""
import json
import tempfile
import threading
from pathlib import Path
from . import __version__
from .paths import workspace, executable, data_dir
from .audio import run
from .backend import Backend
from .render import render, Settings


def check(app):
    # Construct the real window to detect startup/import failures. No user
    # profile is opened: the updater supplies a separate LOCALAPPDATA.
    from .ui import Window
    window = Window()
    try:
        app.processEvents()
        cancel = threading.Event()
        run([executable('ffmpeg'), '-version'], cancel)
        with tempfile.TemporaryDirectory(prefix='job-health-', dir=workspace()) as temp:
            source = Path(temp)/'health.srt'
            source.write_text('1\n00:00:00,000 --> 00:00:05,000\nこれは音声の確認です。\n', encoding='utf-8')
            output = Path(temp)/'health.mp3'
            result = render(source, output, Settings(language='Japanese', voice='jf_alpha'),
                            Backend(), cancel)
            if not output.is_file() or result['overlaps'] != 0:
                raise RuntimeError('Japanese output health check failed')
        (data_dir()/'update-health.json').write_text(
            json.dumps({'passed':True,'version':__version__,'ui':True,'japanese_mp3':True}),encoding='utf-8')
        return 0
    finally:
        window.close(); window.deleteLater(); app.processEvents()
