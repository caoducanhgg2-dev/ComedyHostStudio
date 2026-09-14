"""Backends return mono PCM; timeline code never branches on engine type."""
from dataclasses import dataclass
from typing import Protocol
import io
import json
import wave
import urllib.request
import urllib.parse
import numpy as np
from .backend import Backend, EN_US_VOICES, EN_GB_VOICES, JA_VOICES, PREVIEW
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
        groups=(('English US',EN_US_VOICES),('English UK',EN_GB_VOICES),('Japanese',JA_VOICES))
        return [VoiceInfo(v,v.split('_',1)[1].title(),lang,'Kokoro',license='Apache-2.0',source='https://huggingface.co/hexgrad/Kokoro-82M')
                for lang,voices in groups for v in voices]
    def capabilities(self):return dict(offline=True,cpu=True,native_styles=False)
    def styles(self,voice):return ()
    def license_info(self,voice):return dict(license='Apache-2.0',source='https://huggingface.co/hexgrad/Kokoro-82M')
    def preview(self,language,voice,cancel):return self.synthesize(PREVIEW[language],language,voice,cancel)

class LocalVoicevoxBackend:
    """VOICEVOX-compatible local engine, including Aivis; never cloud requests.

    Aivis generates public API speaker IDs when models are loaded. New optional
    models therefore use style_id=-1 and are resolved against /speakers by
    speaker UUID + manifest style name. Older pinned voices keep their verified
    numeric IDs and remain fully backward compatible.
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
    def resolve_style_id(self,v,style,cancel):
        """Resolve a local manifest style to the runtime Aivis speaker ID."""
        if v.style_id>=0:return v.style_id if style is None else style
        local_id=0 if style is None else style
        if type(local_id) is not int or local_id not in {s['id'] for s in v.styles}:
            raise ValueError('Phong cách bản địa không thuộc giọng đã chọn.')
        expected=next((s for s in v.styles if s['id']==local_id),None)
        if expected is None:raise ValueError('Không tìm thấy phong cách bản địa.')
        speakers=json.loads(self.request('/speakers',cancel))
        if not isinstance(speakers,list):raise RuntimeError('Engine trả danh sách giọng không hợp lệ.')
        speaker=next((s for s in speakers if s.get('speaker_uuid')==v.speaker_uuid),None)
        if speaker is None:raise RuntimeError('Engine chưa nạp giọng đã chọn. Hãy cập nhật lại gói giọng Nhật.')
        runtime_styles=speaker.get('styles',[])
        source_name=expected.get('source_name',expected.get('name'))
        resolved=next((s.get('id') for s in runtime_styles if s.get('name')==source_name and isinstance(s.get('id'),int)),None)
        if resolved is None and 0<=local_id<len(runtime_styles):
            fallback=runtime_styles[local_id].get('id')
            if isinstance(fallback,int):resolved=fallback
        if resolved is None:raise RuntimeError('Không ánh xạ được phong cách của giọng Aivis.')
        return resolved
    def synthesize_style(self,text,language,voice,style,cancel,progress=lambda _:None):
        v=self.voices.get(voice)
        if v is None or language!=v.language:raise ValueError('Giọng không khớp ngôn ngữ hoặc chưa được cài.')
        if style is not None and (type(style) is not int or style not in {s['id'] for s in v.styles}):
            raise ValueError('Phong cách bản địa không thuộc giọng đã chọn.')
        if self.ensure_started:self.ensure_started(cancel,progress)
        style_id=self.resolve_style_id(v,style,cancel)
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
        for voice in voices:self.routes[voice.id]=engine.engine
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
