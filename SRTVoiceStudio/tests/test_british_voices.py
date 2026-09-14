import threading
import numpy as np
import pytest
from studio.backend import Backend, EN_GB_VOICES, EN_US_VOICES, JA_VOICES, PREVIEW
from studio.voice_backends import KokoroBackend
from studio.ui_text import LANGUAGES, voice_label


class DummyModel:
    def __init__(self):
        self.calls=[]
    def create(self,text,**kwargs):
        self.calls.append((text,kwargs))
        return np.ones(2400,dtype=np.float32),24000


def configured_backend():
    backend=Backend();backend.model=DummyModel()
    return backend


def test_british_voice_catalogue_is_eight_distinct_offline_kokoro_voices():
    assert EN_GB_VOICES==['bf_alice','bf_emma','bf_isabella','bf_lily','bm_daniel','bm_fable','bm_george','bm_lewis']
    assert len(EN_GB_VOICES)==8 and not (set(EN_GB_VOICES)&set(EN_US_VOICES))
    assert not (set(EN_GB_VOICES)&set(JA_VOICES))
    voices=[v for v in KokoroBackend().list_voices() if v.language=='English UK']
    assert [v.id for v in voices]==EN_GB_VOICES
    assert all(v.engine=='Kokoro' and v.license=='Apache-2.0' for v in voices)
    assert LANGUAGES['English UK']=='Tiếng Anh (Anh)'
    assert 'Anh' in voice_label('bf_emma') and 'Anh' in voice_label('bm_george')


def test_british_synthesis_uses_en_gb_and_rejects_cross_region_voice():
    backend=configured_backend();cancel=threading.Event()
    samples,rate=backend.synthesize(PREVIEW['English UK'],'English UK','bf_emma',cancel)
    assert len(samples)==2400 and rate==24000
    assert backend.model.calls[-1][1]['lang']=='en-gb'
    assert backend.model.calls[-1][1]['voice']=='bf_emma'
    with pytest.raises(ValueError):
        backend.synthesize('Wrong region','English UK','af_heart',cancel)
    with pytest.raises(ValueError):
        backend.synthesize('Wrong region','English US','bf_emma',cancel)


def test_existing_us_and_japanese_voice_counts_are_preserved():
    assert len(EN_US_VOICES)==20
    assert len(JA_VOICES)==5
    assert len(KokoroBackend().list_voices())==33
