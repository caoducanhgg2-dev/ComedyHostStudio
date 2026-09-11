"""Backends return mono PCM; timeline code never branches on engine type."""
from dataclasses import dataclass
from typing import Protocol
import io
import json
import wave
import urllib.request
import urllib.parse
import numpy as np
from .backend import Backend, EN_VOICES, JA_VOICES, PREVIEW
from .audio import check_cancel

@dataclass(frozen=True)
class VoiceInfo:
    id: str
    name: str
    language: str
    engine: str
    speaker_uuid: str = ''
    style_id: int = 0
    styles: tuple = ()
    license: str = ''
    source: str = ''

class VoiceBackend(Protocol):
    def list_voices(self): ...
    def synthesize(self,text,language,voice,cancel,progress=lambda _:None): ...
    def capabilities(self): ...
    def styles(self,voice): ...
    def license_info(self,voice): ...

def synthesize_selected(backend,text,settings,cancel,progress=lambda _:None):
    if settings.native_style is None:
        return backend.synthesize(text,settings.language,settings.voice,cancel,progress)
    return backend.synthesize_style(text,settings.language,settings.voice,settings.native_style,cancel,progress)

class KokoroBackend(Backend):
    def list_voices(self):
        return [VoiceInfo(v,v.split('_',1)[1].title(),lang,'Kokoro',license='Apache-2.0',source='https://huggingface.co/hexgrad/Kokoro-82M')
                for lang,voices in [('English US',EN_VOICES),('Japanese',JA_VOICES)] for v in voices]
    def capabilities(self):return dict(offline=True,cpu=True,native_styles=False)
    def styles(self,voice):return ()
    def license_info(self,voice):return dict(license='Apache-2.0',source='https://huggingface.co/hexgrad/Kokoro-82M')
    def preview(self,language,voice,cancel):return self.synthesize(PREVIEW[language],language,voice,cancel)

class LocalVoicevoxBackend:
    """VOICEVOX-compatible *local* engine, including Aivis; never cloud requests.
    Engine startup/model installation is owned by the pack manager.
    """
    def __init__(self,engine,port,voices=(),ensure_started=None):
        self.engine=engine
        if not isinstance(port,int) or not 1024<=port<=65535:raise ValueError('Cổng local không hợp lệ.')
        self.base=f'http://127.0.0.1:{port}'
        self.voices={v.id:v for v in voices}
        self.ensure_started=ensure_started
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(self,path,cancel,body=None,params=None):
        check_cancel(cancel)
        url=self.base+path+('?' + urllib.parse.urlencode(params) if params else '')
        data=json.dumps(body).encode() if body is not None else (b'' if path in ('/audio_query','/synthesis') else None)
        req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
        with self.opener.open(req,timeout=120) as response:
            result=response.read(64*1024*1024+1)
        check_cancel(cancel)
        if len(result)>64*1024*1024:raise RuntimeError('Audio phản hồi quá lớn.')
        return result
    def list_voices(self):return list(self.voices.values())
    def capabilities(self):return dict(offline=True,cpu=True,native_styles=True)
    def styles(self,voice):return self.voices[voice].styles
    def license_info(self,voice):
        v=self.voices[voice];return dict(license=v.license,source=v.source)
    def synthesize(self,text,language,voice,cancel,progress=lambda _:None):
        return self.synthesize_style(text,language,voice,None,cancel,progress)
    def synthesize_style(self,text,language,voice,style,cancel,progress=lambda _:None):
        v=self.voices.get(voice)
        if v is None or language!=v.language:raise ValueError('Giọng không khớp ngôn ngữ hoặc chưa được cài.')
        style_id=v.style_id if style is None else style
        if style is not None and (type(style) is not int or style not in {s['id'] for s in v.styles}):
            raise ValueError('Phong cách bản địa không thuộc giọng đã chọn.')
        if self.ensure_started:self.ensure_started(cancel,progress)
        query=json.loads(self.request('/audio_query',cancel,params={'text':text,'speaker':style_id}))
        query.update(speedScale=1.0,outputSamplingRate=48000,outputStereo=False)
        raw=self.request('/synthesis',cancel,query,{'speaker':style_id})
        with wave.open(io.BytesIO(raw)) as f:
            if f.getsampwidth()!=2:raise RuntimeError('Backend trả WAV không phải PCM16.')
            channels=f.getnchannels();rate=f.getframerate()
            if channels not in (1,2) or not 8000<=rate<=192000:
                raise RuntimeError('Định dạng PCM của backend không hợp lệ.')
            a=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
        if channels>1:a=a.reshape(-1,channels).mean(axis=1)
        if not len(a) or not np.isfinite(a).all() or not np.any(np.abs(a)>1e-7):
            raise RuntimeError('Backend trả về audio rỗng hoặc im lặng.')
        check_cancel(cancel)
        return a,rate
    def preview(self,language,voice,cancel):return self.synthesize(PREVIEW[language],language,voice,cancel)

class BackendRouter:
    def __init__(self):
        self.kokoro=KokoroBackend();self.engines={'Kokoro':self.kokoro};self.routes={v.id:'Kokoro' for v in self.kokoro.list_voices()}
    def register(self,engine):
        voices=engine.list_voices()
        if len({v.id for v in voices})!=len(voices):raise ValueError('Trùng mã giọng.')
        for voice in voices:
            if voice.id in self.routes and self.routes[voice.id]!=engine.engine:raise ValueError('Trùng mã giọng.')
        if engine.engine=='Kokoro':raise ValueError('Không thay thế backend Kokoro gốc.')
        self.routes={v:e for v,e in self.routes.items() if e!=engine.engine}
        self.engines[engine.engine]=engine
        for voice in voices:
            self.routes[voice.id]=engine.engine
    def synthesize(self,text,language,voice,cancel,progress=lambda _:None):
        if voice not in self.routes:raise ValueError('Giọng chưa được cài.')
        return self.engines[self.routes[voice]].synthesize(text,language,voice,cancel,progress)
    def list_voices(self):return [v for e in self.engines.values() for v in e.list_voices()]
    def styles(self,voice):return self.engines[self.routes[voice]].styles(voice) if voice in self.routes else ()
    def synthesize_style(self,text,language,voice,style,cancel,progress=lambda _:None):
        if voice not in self.routes:raise ValueError('Giọng chưa được cài.')
        backend=self.engines[self.routes[voice]]
        if not backend.capabilities()['native_styles']:raise ValueError('Giọng này không có phong cách bản địa.')
        return backend.synthesize_style(text,language,voice,style,cancel,progress)
    def load(self,cancel,progress):return self.kokoro.load(cancel,progress)
    @property
    def model(self):return self.kokoro.model
    @property
    def japanese(self):return self.kokoro.japanese
