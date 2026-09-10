"""Drive actual GUI controls asynchronously in the installed app."""
import json
import logging
import tempfile
import time
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog
from .paths import workspace, data_dir
from . import __version__

class UiChecks:
    def __init__(self,app,window):
        self.app,self.window=app,window
        self.temp=tempfile.TemporaryDirectory(prefix='job-',dir=workspace())
        self.folder=Path(self.temp.name)
        self.source=self.folder/'日本語 テスト.srt'
        self.source.write_text('1\n00:00:05,000 --> 00:00:06,500\nThis is the final voice preview.',encoding='utf-8-sig')
        self.output=self.folder/'日本語 テスト_Voice.mp3'
        self.stage=0;self.started=time.monotonic();self.calls=0;self.error=None
        original=window.backend.synthesize
        def counted(*args,**kwargs):
            self.calls+=1
            return original(*args,**kwargs)
        window.backend.synthesize=counted
        window.show_error=lambda message,details:self.fail(message+'\n'+details)
        self.timer=QTimer(window);self.timer.timeout.connect(self.advance);self.timer.start(100)

    def finish(self,passed,error=None):
        self.timer.stop()
        self.window.stop_preview()
        self.window.preview_cache.clear()
        self.temp.cleanup()
        report={'version':__version__,'passed':passed,'error':error,'base_synthesis_calls':self.calls,
                'checks':['defaults','C disabled without SRT','caption selection','A','B same base',
                          'C production fit','one MP3 via Generate button','preview cleanup']}
        (data_dir()/'ui-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        self.app.exit(0 if passed else 1)

    def fail(self,error):
        logging.error('UI check: %s',error)
        self.error=error

    def advance(self):
        w=self.window
        try:
            if time.monotonic()-self.started>180:
                raise RuntimeError('UI test timeout')
            if w.busy():
                return
            if self.error:
                raise RuntimeError(self.error)
            if self.stage==0:
                assert w.settings().emotion=='Natural' and w.settings().effect=='None'
                assert not w.preview_buttons[2].isEnabled()
                w.file.setText(str(self.source));w.load_captions();w.caption_select.setCurrentIndex(1)
                assert w.preview_buttons[2].isEnabled()
                w.preview_buttons[0].click()
            elif self.stage==1:
                assert self.calls==1 and w.preview_cache.base is not None
                w.emotion.setCurrentText('Dramatic');w.effect.setCurrentText('Cave');w.strength.setCurrentText('Strong')
                w.preview_buttons[1].click()
            elif self.stage==2:
                assert self.calls==1 and w.preview_cache.processed is not None
                w.preview_buttons[2].click()
            elif self.stage==3:
                assert self.calls==1 and w.preview_cache.final is not None
                assert 'Overlap: 0' in w.preview_details.text()
                from PySide6.QtWidgets import QScrollArea
                w.findChild(QScrollArea).ensureWidgetVisible(w.preview_details)
                w.grab().save(str(data_dir()/'ui-preview.png'))
                QFileDialog.getSaveFileName=lambda *a,**k:(str(self.output),'MP3 (*.mp3)')
                w.generate.click()
            elif self.stage==4:
                assert self.output.is_file() and len(list(self.folder.glob('*.mp3')))==1
                assert 'TIMELINE VALID' in w.report.toPlainText() and '0 overlaps' in w.report.toPlainText()
                assert w.preview_temp is None and w.preview_cache.base is None
                assert not list(self.folder.glob('*.wav'))
                self.finish(True)
                return
            self.stage+=1
        except Exception as exc:
            logging.exception('UI acceptance failed')
            self.finish(False,str(exc))
