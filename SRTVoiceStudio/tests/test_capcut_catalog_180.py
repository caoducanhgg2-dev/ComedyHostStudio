from studio.voice_catalog import (
    capcut_reference_voices,capcut_reference_ids,is_capcut_reference,
    capcut_reference_meta,catalog_ids,CAPCUT_SOURCE
)

def test_capcut_reference_catalog_is_grouped_by_market():
    voices=capcut_reference_voices()
    assert len(voices)==31
    assert len(capcut_reference_ids())==31
    assert all(v.engine=='CapCut' and is_capcut_reference(v) for v in voices)
    assert all(v.source==CAPCUT_SOURCE and v.source.startswith('https://') for v in voices)
    counts={}
    for voice in voices:
        counts[voice.language]=counts.get(voice.language,0)+1
    assert counts=={
        'English US':12,
        'English UK':6,
        'Japanese':6,
        'Vietnamese':7,
    }

def test_capcut_profiles_do_not_change_local_optional_catalog():
    assert len(catalog_ids())==21
    assert catalog_ids().isdisjoint(capcut_reference_ids())

def test_market_filters_return_only_the_requested_language():
    cases={
        'English US':12,
        'English UK':6,
        'Japanese':6,
        'Vietnamese':7,
    }
    for language,count in cases.items():
        voices=capcut_reference_voices(language)
        assert len(voices)==count
        assert all(v.language==language for v in voices)

def test_required_capcut_profiles_are_present():
    names={v.id for v in capcut_reference_voices()}
    required={
        'capcut:us:male_storyteller','capcut:us:female_storyteller',
        'capcut:us:jessie','capcut:us:bestie','capcut:us:chill_girl',
        'capcut:us:energetic_female','capcut:us:energetic_male',
        'capcut:us:confident_male','capcut:us:witty','capcut:us:trickster',
        'capcut:jp:kawaii_vocalist','capcut:jp:anime_girl','capcut:jp:kiddo',
        'capcut:vn:male_storyteller','capcut:vn:female_storyteller',
        'capcut:vn:serious_female','capcut:vn:confident_male',
    }
    assert required <= names


def test_capcut_reference_metadata_exposes_market_and_use_case():
    jp=next(v for v in capcut_reference_voices('Japanese') if v.id=='capcut:jp:witty')
    meta=capcut_reference_meta(jp)
    assert meta['market']=='JP'
    assert meta['gender']=='Trung tính'
    assert 'review' in meta['use_case'] and 'comedy' in meta['use_case']
    vn=next(v for v in capcut_reference_voices('Vietnamese') if v.id=='capcut:vn:confident_male')
    assert capcut_reference_meta(vn)['market']=='VN'
    assert 'thuyết minh' in capcut_reference_meta(vn)['use_case']
