"""Offline performance presets. Kokoro has no native emotion/whisper parameter.

Only bundled FFmpeg filters and NumPy are used. Pitch uses resampling plus
inverse atempo (no optional rubberband library). All tails precede timeline fit.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import uuid
import numpy as np
from .audio import run, check_cancel
from .paths import executable

LEVELS = {'Mild': .55, 'Medium': 1.0, 'Strong': 1.45}
@dataclass(frozen=True)
class EmotionProfile:
    tempo: float = 1.0
    pitch: float = 0.0
    body: float = 0.0
    presence: float = 0.0
    compression: float = 1.0

EMOTIONS = {
    'Natural': EmotionProfile(), 'Happy': EmotionProfile(1.03,.35,0,1.2,1.3),
    'Excited': EmotionProfile(1.05,.65,-.2,1.8,1.7), 'Funny / Playful': EmotionProfile(1.03,.55,-.4,1.1,1.4),
    'Serious': EmotionProfile(.99,-.45,1.3,.5,1.5), 'Calm': EmotionProfile(.98,-.15,.4,-1.2,1.0),
    'Surprised': EmotionProfile(1.035,.85,-.3,1.5,1.3), 'Dramatic': EmotionProfile(.98,-.65,1.6,.6,1.0),
    'Sad': EmotionProfile(.97,-.35,.3,-1.6,1.0), 'Angry': EmotionProfile(1.035,-.2,.8,2.0,2.2),
    'Whisper-like': EmotionProfile(.99,.1,-3.0,2.0,1.0), 'Narrator': EmotionProfile(1.0,-.25,.5,1.0,1.3),
}
@dataclass(frozen=True)
class EffectProfile:
    name: str
    tail: bool = False
EFFECTS = {name: EffectProfile(name,name in ('Reverb','Cave','Echo')) for name in ('None','Deep Voice','Bright Voice','Radio','Telephone','Walkie-Talkie','Megaphone','Intercom','Robot','Reverb','Cave','Echo','Distortion','Cheap Microphone','Underwater','Old Tape')}
REQUIRED_FILTERS={'atempo','asetrate','aresample','equalizer','highpass','lowpass','acompressor','aecho','asoftclip','tremolo','vibrato'}

def auto_emotion(text,language):
    bang=text.count('!')+text.count('！'); question=text.count('?')+text.count('？'); density=(bang+question)/max(len(text),1)
    intensity='Strong' if bang+question>=3 or density>.12 else 'Medium'
    if language=='Japanese':
        rules=[('Surprised',('まさか','うそ','嘘','信じられない','何をして','大丈夫なのか','本当か')),('Dramatic',('大変','最悪','全てを失','すべてを失','突然','失敗','終わりだ')),('Angry',('ふざけるな','許さない','怒って','いい加減に')),('Sad',('悲しい','寂しい','残念','泣いて','つらい')),('Calm',('静か','穏やか','ゆっくり','落ち着','安心')),('Happy',('完成','成功','やった','嬉しい','うれしい','ありがとう','最高')),('Funny / Playful',('笑える','面白い','おもしろい','冗談','なんちゃって'))]; value=text
    else:
        value=text.casefold(); rules=[('Surprised',('no way','what is that','unbelievable','really?','are you kidding','cannot believe',"can't believe")),('Dramatic',('went wrong','disaster','suddenly','everything was lost','all was lost','terrible')),('Angry',('furious','how dare','hate this','stop it','angry')),('Sad',('sad','heartbroken','lonely','miss you','sorry','crying')),('Calm',('quiet','peaceful','calm','gently','relax','breathe')),('Happy',('finally','worked','success','completed','amazing','wonderful','thank you','happy')),('Funny / Playful',('hilarious','funny','joking','just kidding','ridiculous'))]
    if bang and question:return 'Surprised',intensity
    for emotion,phrases in rules:
        if any(p in value for p in phrases):return emotion,intensity
    if question:return 'Surprised','Mild' if not bang else intensity
    if bang:return 'Excited',intensity
    return 'Narrator','Mild'

def selected_emotion(settings,text):
    if settings.emotion_mode=='Auto':return auto_emotion(text,settings.language)
    if settings.emotion_mode!='Manual':raise ValueError('Emotion Mode không hợp lệ.')
    return settings.emotion,settings.intensity

def _pitch(rate,semitones):
    ratio=2**(semitones/12); shifted=round(rate*ratio)
    return [f'asetrate={shifted}',f'aresample={rate}',f'atempo={rate/shifted:.10f}']

class EffectProcessor:
    def __init__(self,folder,cancel):self.folder,self.cancel=Path(folder),cancel
    @staticmethod
    def validate_filters(cancel):
        listing=run([executable('ffmpeg'),'-hide_banner','-filters'],cancel)
        available={m.group(1) for line in listing.splitlines() if (m:=re.match(r'^\s*[.A-Z|]{3}\s+(\w+)\s',line))}
        missing=REQUIRED_FILTERS-available
        if missing:raise RuntimeError('FFmpeg thiếu filter: '+', '.join(sorted(missing)))
        return sorted(REQUIRED_FILTERS)
    def _process(self,samples,rate,filters,duration_samples=None):
        check_cancel(self.cancel); original=np.asarray(samples,dtype=np.float32).reshape(-1)
        if not len(original) or not np.isfinite(original).all():raise ValueError('Audio rỗng hoặc không hợp lệ.')
        if not filters:return original.copy()
        token=uuid.uuid4().hex
        source,target=self.folder/f'effect-in-{token}.raw',self.folder/f'effect-out-{token}.raw'
        try:
            original.astype('<f4').tofile(source)
            run([executable('ffmpeg'),'-nostdin','-v','error','-y','-f','f32le','-ar',str(rate),'-ac','1','-i',str(source),'-af',','.join(filters),'-ar',str(rate),'-ac','1','-f','f32le',str(target)],self.cancel)
            if not target.is_file() or target.stat().st_size<4:raise RuntimeError('Effect trả về audio không hợp lệ.')
            result=np.fromfile(target,dtype='<f4').copy()
            if not len(result) or not np.isfinite(result).all():raise RuntimeError('Effect trả về audio không hợp lệ.')
            if duration_samples is not None:result=np.pad(result,(0,max(0,duration_samples-len(result))))[:duration_samples]
            peak=float(np.max(np.abs(result)))
            if peak>.95:result*=.95/peak
            return result
        finally:
            source.unlink(missing_ok=True); target.unlink(missing_ok=True)
    def apply_emotion(self,samples,rate,emotion,intensity):
        profile,k=EMOTIONS[emotion],LEVELS[intensity]; tempo=1+(profile.tempo-1)*k
        if emotion=='Natural':return np.asarray(samples,dtype=np.float32).copy(),1.0
        filters=_pitch(rate,profile.pitch*k) if profile.pitch else []
        filters += [f'equalizer=f=220:t=q:w=1:g={profile.body*k:.5f}',f'equalizer=f=2800:t=q:w=1:g={profile.presence*k:.5f}']
        if profile.compression>1:filters += [f'acompressor=threshold=0.12:ratio={1+(profile.compression-1)*k:.5f}:attack=8:release=90:makeup=1']
        colored=self._process(samples,rate,filters,len(samples))
        if abs(tempo-1)>1e-9:colored=self._process(colored,rate,[f'atempo={tempo:.9f}'])
        return colored,tempo
    def apply_effect(self,samples,rate,effect,strength):
        EFFECTS[effect]; k=LEVELS[strength]; filters,exact=[],None
        if effect=='None':return np.asarray(samples,dtype=np.float32).copy()
        if effect=='Deep Voice':filters=_pitch(rate,-2.0*k)+[f'equalizer=f=210:t=q:w=1:g={1.2*k}']; exact=len(samples)
        elif effect=='Bright Voice':filters=_pitch(rate,.65*k)+[f'equalizer=f=2800:t=q:w=1:g={2*k}']; exact=len(samples)
        elif effect in ('Reverb','Cave','Echo'):
            if effect=='Reverb':delays=[round(x*(.65+.35*k)) for x in (43,79,127)]; decays=[min(.65,x*k) for x in (.19,.13,.08)]
            elif effect=='Cave':filters += [f'lowpass=f={int(6500-1200*k)}']; delays=[round(x*(.65+.35*k)) for x in (137,311,653,1013)]; decays=[min(.65,x*k) for x in (.30,.24,.17,.11)]
            else:delays=[round(x*(.65+.35*k)) for x in (310,620,930)]; decays=[min(.65,x*k) for x in (.34,.22,.13)]
            filters += ['aecho=0.8:0.85:'+'|'.join(map(str,delays))+':'+'|'.join(f'{d:.5f}' for d in decays)]
        elif effect=='Robot':filters=[f'tremolo=f={32+8*k}:d={.28*k:.5f}',f'equalizer=f=1500:t=q:w=1:g={1.4*k}']
        elif effect=='Distortion':filters=[f'asoftclip=type=tanh:threshold={.65-.17*k:.5f}:output=0.9:oversample=2']
        elif effect=='Underwater':filters=[f'lowpass=f={int(2600-600*k)}',f'equalizer=f=350:t=q:w=1:g={1.2*k}']
        elif effect=='Old Tape':filters=[f'highpass=f={50+20*k}',f'lowpass=f={int(7200-1800*k)}',f'vibrato=f=0.7:d={.12*k:.5f}',f'asoftclip=type=tanh:threshold={.85-.12*k:.5f}:output=0.95:oversample=2']
        else:
            bands={'Radio':(170,4400),'Telephone':(340,3200),'Walkie-Talkie':(480,2800),'Megaphone':(390,3500),'Intercom':(290,3800),'Cheap Microphone':(240,3400)}; lo,hi=bands[effect]
            filters=[f'highpass=f={lo*(.6+.4*k):.4f}',f'lowpass=f={hi/(.8+.2*k):.4f}',f'equalizer=f=1800:t=q:w=1:g={k*(2.5 if effect=="Megaphone" else 1):.4f}',f'acompressor=threshold=0.1:ratio={1.6+k:.5f}:attack=5:release=70:makeup=1']
            if effect in ('Walkie-Talkie','Megaphone','Cheap Microphone'):filters += [f'asoftclip=type=tanh:threshold={.65-.12*k:.5f}:output=0.95:oversample=2']
        return self._process(samples,rate,filters,exact)
    def process(self,samples,rate,settings,text):
        emotion,intensity=selected_emotion(settings,text); colored,tempo=self.apply_emotion(samples,rate,emotion,intensity); processed=self.apply_effect(colored,rate,settings.effect,settings.strength); return processed,tempo,emotion,intensity
