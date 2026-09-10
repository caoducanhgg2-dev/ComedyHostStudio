"""Local API contract tests; these do not certify real voice quality."""
import io
import json
import threading
import wave
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import pytest
from studio.audio import Cancelled
from studio.voice_backends import BackendRouter, LocalVoicevoxBackend, VoiceInfo


@pytest.fixture
def api():
    calls=[]
    pcm=(np.sin(np.arange(4800)*.1)*10000).astype('<i2')
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(pcm.tobytes())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=self.rfile.read(int(self.headers.get('Content-Length',0)))
            calls.append((self.path,body))
            result=b'{"speedScale":1.0}' if self.path.startswith('/audio_query?') else buffer.getvalue()
            self.send_response(200);self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield server.server_port,calls,pcm
    finally:server.shutdown();server.server_close();thread.join()


def test_local_japanese_api_returns_pcm_without_timeline_speed(api,monkeypatch):
    port,calls,pcm=api
    monkeypatch.setenv('http_proxy','http://127.0.0.1:1')
    voice=VoiceInfo('aivis:test','Giọng thử','Japanese','Aivis',style_id=42)
    backend=LocalVoicevoxBackend('Aivis',port,[voice])
    router=BackendRouter();router.register(backend)
    samples,rate=router.synthesize('今日は、音声のテストです。','Japanese',voice.id,threading.Event())
    assert rate==48000 and np.array_equal(samples,pcm.astype(np.float32)/32768)
    assert 'speaker=42' in calls[0][0] and '%E4' in calls[0][0]
    query=json.loads(calls[1][1])
    assert query['speedScale']==1.0 and query['outputStereo'] is False
    assert query['outputSamplingRate']==48000


def test_cancelled_request_never_contacts_engine(api):
    port,calls,_=api
    backend=LocalVoicevoxBackend('Aivis',port)
    cancel=threading.Event();cancel.set()
    with pytest.raises(Cancelled):backend.request('/speakers',cancel)
    assert not calls


def test_router_registration_failure_is_atomic_and_refresh_removes_stale():
    router=BackendRouter()
    v=VoiceInfo('aivis:first','Test','Japanese','Aivis')
    router.register(LocalVoicevoxBackend('Aivis',10101,[v]))
    before=dict(router.routes);engine=router.engines['Aivis']
    with pytest.raises(ValueError):router.register(LocalVoicevoxBackend('Aivis',10101,[replace(v,id='af_heart')]))
    assert router.routes==before and router.engines['Aivis'] is engine
    router.register(LocalVoicevoxBackend('Aivis',10101,[replace(v,id='aivis:second')]))
    assert 'aivis:first' not in router.routes and 'aivis:second' in router.routes
