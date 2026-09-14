import hashlib
import io
import threading
import zipfile
from dataclasses import replace
import pytest
from studio.audio import Cancelled
from studio.voice_packs import Pack,PackManager


class Response(io.BytesIO):
    status=200
    headers={}


class Opener:
    def __init__(self,body):self.body=body;self.calls=0
    def open(self,*args,**kwargs):self.calls+=1;return Response(self.body)


def pack(body,**kwargs):
    return Pack('test','1.0','https://example.org/voice',hashlib.sha256(body).hexdigest(),len(body),
                kwargs.get('format','raw'),'voice.bin','Apache-2.0','https://example.org/license')


def test_verified_offline_reuse_and_version_isolation(tmp_path):
    body=b'test voice bytes';opener=Opener(body);manager=PackManager(tmp_path,opener);p=pack(body)
    first=manager.install(p,threading.Event())
    assert (first/'voice.bin').read_bytes()==body and manager.installed(p)
    assert manager.install(p,threading.Event())==first and opener.calls==1
    newer=manager.install(replace(p,version='2.0'),threading.Event())
    assert newer!=first and first.is_dir() and opener.calls==2
    (first/'voice.bin').write_bytes(b'corrupt')
    assert not manager.installed(p)
    with pytest.raises(RuntimeError,match='checksum'):manager.install(p,threading.Event())
    assert manager.installed(replace(p,version='2.0'))


def test_bad_hash_never_publishes_and_removes_partial(tmp_path):
    body=b'wrong bytes';manager=PackManager(tmp_path,Opener(body));p=replace(pack(body),sha256='0'*64)
    with pytest.raises(RuntimeError,match='SHA-256'):manager.install(p,threading.Event())
    assert not manager.location(p).exists()
    assert not list(tmp_path.rglob('*.part')) and not list(tmp_path.rglob('.install-*'))


def test_cancellation_during_download_removes_partial(tmp_path):
    body=b'a'*600000;manager=PackManager(tmp_path,Opener(body));p=pack(body);cancel=threading.Event()
    with pytest.raises(Cancelled):manager.install(p,cancel,lambda *_:cancel.set())
    assert not manager.location(p).exists() and not list(tmp_path.rglob('.install-*'))


@pytest.mark.parametrize('name',['../outside','/absolute','C:/outside','folder\\outside'])
def test_zip_traversal_is_rejected_before_extraction(tmp_path,name):
    buffer=io.BytesIO()
    # ZipInfo normalizes os.sep on Windows at construction. Preserve the
    # actual archive spelling so this fixture has identical bytes on both OSes.
    info=zipfile.ZipInfo('placeholder');info.filename=name
    with zipfile.ZipFile(buffer,'w') as z:z.writestr(info,b'invalid')
    body=buffer.getvalue();p=pack(body,format='zip');manager=PackManager(tmp_path,Opener(body))
    with pytest.raises(ValueError,match='an toàn'):manager.install(p,threading.Event())
    assert not manager.location(p).exists()


def test_valid_zip_is_verified_after_extract(tmp_path):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:z.writestr('models/voice.bin',b'voice')
    body=buffer.getvalue();p=pack(body,format='zip');manager=PackManager(tmp_path,Opener(body))
    folder=manager.install(p,threading.Event())
    assert (folder/'models/voice.bin').read_bytes()==b'voice' and manager.installed(p)
