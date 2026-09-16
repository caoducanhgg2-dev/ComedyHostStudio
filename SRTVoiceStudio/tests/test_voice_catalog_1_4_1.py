from studio.backend import EN_US_VOICES, EN_GB_VOICES, JA_VOICES
from studio.ui_text import voice_characteristic, voice_label
from studio.voice_catalog import catalog_voices, catalog_ids


def test_all_english_voices_have_visible_characteristics():
    voices=EN_US_VOICES+EN_GB_VOICES
    assert len(EN_US_VOICES)==20
    assert len(EN_GB_VOICES)==8
    assert all(voice_characteristic(v) for v in voices)
    assert all(' · ' in voice_label(v) for v in voices)


def test_kokoro_japanese_annotations_remain_complete():
    assert len(JA_VOICES)==5
    assert all(voice_characteristic(v) for v in JA_VOICES)


def test_optional_aivis_catalog_exposes_six_japanese_voices_before_install():
    voices=catalog_voices()
    assert len(voices)==6
    assert len(catalog_ids())==6
    assert all(v.language=='Japanese' and v.engine=='Aivis' for v in voices)
    names={v.name.split(' — ',1)[0] for v in voices}
    assert names=={'Mao','Kohaku','Rinne El','Aida Shigeru','Mai','Nise'}
    assert all(voice_characteristic(v.id) for v in voices)
    assert all(v.license.startswith('ACML-1.0') and v.source.startswith('https://') for v in voices)


def test_total_japanese_catalog_capacity_is_eleven_voices():
    assert len(JA_VOICES)+len(catalog_voices())==11
