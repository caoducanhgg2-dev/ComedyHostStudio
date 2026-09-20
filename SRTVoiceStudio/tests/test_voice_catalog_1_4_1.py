from studio.backend import EN_US_VOICES, EN_GB_VOICES, JA_VOICES
from studio.ui_text import voice_characteristic, voice_label
from studio.voice_catalog import aivis_catalog, korva_catalog, catalog_ids


def test_all_english_voices_have_visible_characteristics():
    voices=EN_US_VOICES+EN_GB_VOICES
    assert len(EN_US_VOICES)==20
    assert len(EN_GB_VOICES)==8
    assert all(voice_characteristic(v) for v in voices)
    assert all(' · ' in voice_label(v) for v in voices)


def test_kokoro_japanese_annotations_remain_complete():
    assert len(JA_VOICES)==5
    assert all(voice_characteristic(v) for v in JA_VOICES)


def test_optional_aivis_catalog_exposes_eleven_japanese_voices_before_install():
    voices=aivis_catalog()
    assert len(voices)==11
    assert all(v.language=='Japanese' and v.engine=='Aivis' for v in voices)
    names={v.name.split(' — ',1)[0] for v in voices}
    assert {'Mao','Kohaku','Rinne El','Aida Shigeru','Mai','Nise',
            'Sukiyaki Umataro','Satsuki','Wakana','Rena','Moe'}==names
    assert all(voice_characteristic(v.id) for v in voices)
    assert all(v.license and v.source.startswith('https://') for v in voices)


def test_vietnamese_catalog_exposes_ten_korva_voices():
    voices=korva_catalog()
    assert len(voices)==10
    assert all(v.language=='Vietnamese' and v.engine=='Korva' for v in voices)
    assert all(v.license=='Apache-2.0' and v.source.startswith('https://') for v in voices)
    assert all(voice_characteristic(v.id) for v in voices)
    assert len(catalog_ids())==21


def test_total_japanese_catalog_capacity_is_sixteen_voices():
    assert len(JA_VOICES)+len(aivis_catalog())==16
