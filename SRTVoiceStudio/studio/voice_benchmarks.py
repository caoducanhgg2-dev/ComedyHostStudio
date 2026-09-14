"""Audition evidence with unfilled perceptual ratings, never invented scores."""
import csv
import html
import json
from pathlib import Path
import tempfile
import time
import numpy as np
from .aivis_pack import AivisPack,LICENSE_NOTICE
from .voice_backends import BackendRouter
from .underfill_checks import SharedBase
from .render import Settings,render
from .audio import convert,encode,check_cancel
from .paths import workspace
from .stress import timestamp

TEXTS={
 'English US':[
  ('dialogue','Wait, you built all of this by yourself?'),
  ('review','The tiny cabin looks surprisingly warm and comfortable.'),
  ('comedy','That chair clearly skipped every single leg workout.'),
  ('narration','At sunrise, a quiet village slowly came to life.'),
  ('short','Well, that was unexpected.'),
  ('long','After three careful attempts, the team finally lifted the heavy wooden frame into place.'),
  ('numbers','On September twenty first, Michael packed twelve tools.'),
  ('punctuation','Really? A window here? Fine, let the sunshine in!')],
 'Japanese':[
  ('dialogue','えっ、これを全部一人で作ったんですか？'),
  ('review','小さな部屋ですが、意外と暖かそうですね。'),
  ('comedy','この椅子、脚の筋トレを忘れたみたいです。'),
  ('narration','朝日とともに、静かな村が目を覚ましました。'),
  ('short','まさか、そう来るとは。'),
  ('long','何度も確認を重ねた末に、ようやく大きな木の枠を持ち上げることができました。'),
  ('numbers','九月二十一日、田中さんは十二個の道具を用意しました。'),
  ('punctuation','本当に？ここに窓を？なるほど、明るくなりますね！')]
}
WEIGHTS={'naturalness':35,'pronunciation':25,'expression':15,'speed_fit':10,'audio_quality':10,'popularity':5}

def generate(folder,cancel):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    backend=BackendRouter();pack=AivisPack();optional=pack.backend()
    if optional:backend.register(optional)
    results=[];cards=[]
    try:
        for voice in backend.list_voices():
            check_cancel(cancel);started=time.monotonic()
            name=voice.id.replace(':','_');output=folder/name;output.mkdir(exist_ok=True)
            shared=SharedBase(backend);texts=TEXTS[voice.language];raw=[]
            with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as temporary:
                temp=Path(temporary)
                for category,text in texts:
                    a,rate=shared.synthesize(text,voice.language,voice.id,cancel)
                    raw.extend([convert(a,rate,1.0,temp,cancel),np.zeros(9600,dtype=np.float32)])
                master=temp/'raw.pcm';np.concatenate(raw).astype('<f4').tofile(master)
                encode(master,output/'A_original.mp3',cancel)
                source=temp/'benchmark.srt'
                source.write_text('\n\n'.join(f'{i+1}\n{timestamp(i*6100)} --> {timestamp(i*6100+6000)}\n{text}' for i,(_,text) in enumerate(texts)),encoding='utf-8')
                result=render(source,output/'C_final.mp3',Settings(language=voice.language,voice=voice.id),shared,cancel)
            assert result['overlaps']==0 and shared.count==len(texts)
            results.append(dict(voice=voice.id,name=voice.name,language=voice.language,engine=voice.engine,
                license=voice.license,source=voice.source,texts=texts,elapsed_seconds=time.monotonic()-started,
                naturalness=None,pronunciation=None,expression=None,speed_fit=None,audio_quality=None,popularity=None,
                weighted_score=None,listening_status='Pending human listening',recommended=False,
                average_trailing_silence=result['average_trailing_silence'],overlaps=0,records=result['records']))
            cards.append(f'<section><h2>{html.escape(voice.name)} · {html.escape(voice.id)}</h2><p>{html.escape(voice.license)}</p>'
                f'<p>A · Gốc</p><audio controls preload="none" src="{name}/A_original.mp3"></audio>'
                f'<p>C · Theo mốc SRT</p><audio controls preload="none" src="{name}/C_final.mp3"></audio></section>')
        (folder/'benchmark.json').write_text(json.dumps({'weights_percent':WEIGHTS,'voices':results},ensure_ascii=False,indent=2),encoding='utf-8')
        with (folder/'ratings.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f);writer.writerow(['voice',*WEIGHTS,'reviewer','notes'])
            for r in results:writer.writerow([r['voice'],*(['']*8)])
        (folder/'index.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Nghe thử giọng SRT Voice Studio</title>'
            '<style>body{background:#091421;color:#e6eef9;font:16px system-ui;max-width:960px;margin:32px auto}section{background:#17283b;padding:20px;margin:16px 0;border-radius:12px}audio{width:100%}</style>'
            '<h1>Nghe thử cùng văn bản</h1><p>Chưa chấm điểm cảm nhận. A là giọng gốc; C dùng chung bộ căn mốc với TẠO MP3. Khung thử dài 6 giây để kiểm tra câu ngắn và câu dài.</p><p>'
            +html.escape(LICENSE_NOTICE)+'</p>'+''.join(cards)+'</html>',encoding='utf-8')
        return dict(voices=len(results),technical_checks_passed=True,listening_certified=False,folder=str(folder),weights_percent=WEIGHTS)
    finally:pack.close()
