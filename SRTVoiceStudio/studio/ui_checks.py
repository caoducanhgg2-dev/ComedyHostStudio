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
        self.source.write_text('1\n00:00:05,000 --> 00:00:06,500\nThis is the final voice preview.\n\n2\n00:00:06,600 --> 00:00:16,600\nThis short line keeps its original start.',encoding='utf-8-sig')
        self.output=self.folder/'日本語 テスト_Voice.mp3'
        self.stage=0;self.started=time.monotonic();self.calls=0;self.error=None
        original=window.backend.synthesize
        def counted(*args,**kwargs):
            self.calls+=1
            return original(*args,**kwargs)
        window.backend.synthesize=counted
        window.show_error=lambda message,details:self.fail(message+'\n'+details)
        window.player.errorOccurred.connect(lambda error,message:self.fail('Preview playback: '+message) if message else None)
        self.timer=QTimer(window);self.timer.timeout.connect(self.advance);self.timer.start(100)

    def finish(self,passed,error=None):
        self.timer.stop()
        if passed:
            for index,name in enumerate(('main','batch','voices')):
                self.window.tabs.setCurrentIndex(index);self.app.processEvents()
                self.window.grab().save(str(data_dir()/('ui-'+name+'.png')))
        self.window.stop_preview()
        self.window.preview_cache.clear()
        self.temp.cleanup()
        report={'version':__version__,'passed':passed,'error':error,'base_synthesis_calls':self.calls,
                'checks':['defaults','C disabled without SRT','caption selection','A','B same base',
                          'C production fit','C underfill warning','Vietnamese labels and stable voice IDs','one MP3 via Generate button','memory preview cleanup']}
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
                # Since 1.6.1 the production Generate button is queue-driven.
                # Exercise the same path as a real user instead of bypassing the
                # Unified Workspace by writing directly to the read-only file pointer.
                panel=getattr(w,'multi_file_panel',None)
                assert panel is not None
                panel.queue.items=[]
                w.batch_panel.refresh()
                added=panel.add_paths([self.source])
                assert len(added)==1
                assert panel.selected() is not None
                assert w.file.text().strip()==str(self.source)
                assert w.generate.isEnabled()
                w.caption_select.setCurrentIndex(1)
                assert w.preview_buttons[2].isEnabled()
                w.preview_buttons[0].click()
            elif self.stage==1:
                assert self.calls==1 and w.preview_cache.base is not None
                w.emotion.setCurrentIndex(w.emotion.findData('Dramatic'));w.effect.setCurrentIndex(w.effect.findData('Cave'));w.strength.setCurrentIndex(w.strength.findData('Strong'))
                w.preview_buttons[1].click()
            elif self.stage==2:
                assert self.calls==1 and w.preview_cache.processed is not None
                w.preview_buttons[2].click()
            elif self.stage==3:
                assert self.calls==1 and w.preview_cache.final is not None
                assert 'Chồng tiếng: 0' in w.preview_details.text()
                from PySide6.QtWidgets import QScrollArea
                w.findChild(QScrollArea).ensureWidgetVisible(w.preview_details)
                w.grab().save(str(data_dir()/'ui-preview.png'))
                w.caption_select.setCurrentIndex(2)
                w.emotion.setCurrentIndex(w.emotion.findData('Natural'))
                w.effect.setCurrentIndex(w.effect.findData('None'))
                w.preview_buttons[2].click()
            elif self.stage==4:
                assert self.calls==2
                details=w.preview_cache.details
                assert details['underfilled_at_hard_minimum'] is True
                assert abs(details['speed']-details['minimum_effective_speed']) < 1e-9
                assert 'SHORT SCRIPT' in details['warning']
                assert 'CÂU THOẠI NGẮN' in w.preview_details.text()
                assert w.voice.currentData()=='af_heart' and 'Heart' in w.voice.currentText()
                assert w.generate.isEnabled()
                w.grab().save(str(data_dir()/'ui-preview.png'))
                QFileDialog.getSaveFileName=lambda *a,**k:(str(self.output),'MP3 (*.mp3)')
                w.generate.click()
            elif self.stage==5:
                assert self.output.is_file() and len(list(self.folder.glob('*.mp3')))==1
                # Unified Workspace replaces the legacy single-render text report
                # with a queue summary. Validate the authoritative per-item render
                # report instead of depending on obsolete Vietnamese display text.
                done=[item for item in w.multi_file_panel.queue.items
                      if item.state=='Hoàn tất' and item.output]
                assert len(done)==1
                report=dict(done[0].report or {})
                assert int(report.get('overlaps',-1))==0
                assert int(report.get('valid',0))==int(report.get('total',-1))==2
                assert 'HÀNG ĐỢI HOÀN TẤT' in w.report.toPlainText()
                assert w.preview_temp is None and w.preview_device is None and w.preview_cache.base is None
                assert not list(self.folder.glob('*.wav'))
                self.finish(True)
                return
            self.stage+=1
        except Exception as exc:
            logging.exception('UI acceptance failed')
            self.finish(False,str(exc))
