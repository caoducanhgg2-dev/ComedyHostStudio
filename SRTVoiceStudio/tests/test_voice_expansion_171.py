import threading
from pathlib import Path
import numpy as np

from studio.backend import PREVIEW
from studio.ui_text import LANGUAGES
from studio.voice_backends import BackendRouter
from studio.voice_catalog import aivis_catalog, korva_catalog
from studio.korva_backend import KorvaBackend
from studio.korva_runtime import normalize_text, chunk_text


def test_171_language_and_catalog_capacity():
    assert LANGUAGES["Vietnamese"]=="Tiếng Việt"
    assert "Vietnamese" in PREVIEW and "tiếng Việt" in PREVIEW["Vietnamese"]
    assert len(aivis_catalog())==11
    assert len(korva_catalog())==10
    assert len({v.id for v in aivis_catalog()+korva_catalog()})==21


def test_korva_text_normalization_keeps_vietnamese_and_code_switching():
    value=normalize_text("Hôm nay team mình review iPhone 17")
    assert value.startswith("<vi>") and value.endswith("</vi>")
    assert "iPhone 17" in value
    chunks=chunk_text("Xin chào. Đây là câu thứ hai!")
    assert chunks==["Xin chào. Đây là câu thứ hai!"]


def test_korva_backend_registers_ten_voices_and_returns_pcm(tmp_path):
    class FakeRuntime:
        def __init__(self,root):self.root=Path(root);self.calls=[]
        def synthesize(self,text,voice,total_steps=16,speed=1.0):
            self.calls.append((text,voice,total_steps,speed))
            return np.linspace(-.05,.05,4410,dtype=np.float32),44100

    backend=KorvaBackend(tmp_path,runtime_factory=FakeRuntime)
    assert len(backend.list_voices())==10
    router=BackendRouter();router.register(backend)
    voice=korva_catalog()[0]
    audio,rate=router.synthesize(
        "Xin chào, đây là giọng thử.","Vietnamese",voice.id,threading.Event())
    assert rate==44100 and len(audio)==4410 and np.isfinite(audio).all()
    assert router.routes[voice.id]=="Korva"


def test_korva_backend_rejects_wrong_language(tmp_path):
    backend=KorvaBackend(tmp_path,runtime_factory=lambda root:None)
    voice=korva_catalog()[0]
    try:
        backend.synthesize("hello","English US",voice.id,threading.Event())
    except ValueError as exc:
        assert "không khớp" in str(exc)
    else:
        raise AssertionError("Expected wrong-language rejection")


def test_new_aivis_catalog_excludes_noncommercial_only_entries():
    names={v.name.split(" — ",1)[0] for v in aivis_catalog()}
    assert {"Sukiyaki Umataro","Satsuki","Wakana","Rena","Moe"} <= names
    assert all("NC" not in v.license.upper() for v in aivis_catalog())
