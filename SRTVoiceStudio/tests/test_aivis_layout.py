import hashlib
import threading
import pytest
from studio.aivis_pack import install_shared_file
from studio.audio import Cancelled


def test_shared_model_preserves_existing_and_accepts_identical(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'verified model')
    destination=tmp_path/'roaming'/'model.aivmx'
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    cancel=threading.Event()
    install_shared_file(source,destination,checksum,cancel)
    install_shared_file(source,destination,checksum,cancel)
    assert destination.read_bytes()==source.read_bytes()
    destination.write_bytes(b'user model')
    with pytest.raises(RuntimeError,match='giữ nguyên'):
        install_shared_file(source,destination,checksum,cancel)
    assert destination.read_bytes()==b'user model'
    assert not list(tmp_path.rglob('.srtvs-*'))


def test_shared_model_cancel_never_publishes_partial(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'verified model')
    destination=tmp_path/'roaming'/'model.aivmx'
    cancel=threading.Event();cancel.set()
    with pytest.raises(Cancelled):
        install_shared_file(source,destination,hashlib.sha256(source.read_bytes()).hexdigest(),cancel)
    assert not destination.exists() and not list(tmp_path.rglob('.srtvs-*'))
