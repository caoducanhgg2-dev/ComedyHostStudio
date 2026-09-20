import json
import threading
from studio.aivis_pack import MODEL_PACKS,EXTRA_VOICES,packs
from studio.voice_backends import LocalVoicevoxBackend,VoiceInfo

EXPECTED={
 'f5017410-fbb5-49e1-97cb-e785f42e15f5':(252769346,'e7ac9e2636f59d6f6512016d0752f9e9f89c2b3ffd2012a6a1b92791330e23bc'),
 '47e53151-a378-46f3-abee-ce13aa07feb1':(251137086,'6dabe29de5ec2c1715e12a430805e1bff6ec64a315cccec2d26fad029df83243'),
 'e9339137-2ae3-4d41-9394-fb757a7e61e6':(250837473,'eca53a500a70746f649572ec186d3b98665606b13e8e8e648f9b10fa8c0000c4'),
 '6d11c6c2-f4a4-4435-887e-23dd60f8b8dd':(250240153,'6ff7eaa61c24d37434e2c6ab672fc3ba189ecc9118c08918a486ed5316e5c9d3'),
 'f493ab6c-1ffa-4534-9bbd-2ba398f17cd5':(250036347,'4e90b846f50d4a414993a3b1b90bcf16f2a2ced9cbba9036853191a6196d3ddc'),
 '21d8d535-f206-462d-a3bb-05f8252dede7':(251278485,'d2708663b114c03c4b124d606660f155411413822a3768c5cbb257d70d850699'),
 'f83c385c-829b-40c4-8c11-639027e61636':(251173709,'859078ca2e287b7084aceec4190a54887d2ddba416bab0523d54d7aa20cfc0c6'),
 'b1b8072f-809f-4c6d-9ba1-2ca94d9c3663':(251261356,'2dc764e49667406d97c541475015176052fc618254e35d51c0ce5a5ed69f4b8e'),
 '9a7feb22-b6f3-4f79-92d9-26849e063fa1':(251224802,'0798eb70b4fa04bf5e1a92adb8bf17253f3b8094bff3356f7fbaf67daff9fe00'),
}

def test_nine_extra_japanese_models_are_exactly_pinned():
    manifest={uid:(size,sha) for uid,version,size,sha in MODEL_PACKS}
    assert all(manifest[uid]==value for uid,value in EXPECTED.items())
    by_id={p.filename.removesuffix('.aivmx'):p for p in packs() if p.filename.endswith('.aivmx')}
    expected_license={
        'f493ab6c-1ffa-4534-9bbd-2ba398f17cd5':'CC0',
    }
    for uid,(size,sha) in EXPECTED.items():
        p=by_id[uid]
        assert p.size==size and p.sha256==sha
        assert p.license==expected_license.get(uid,'ACML-1.0')
        assert p.url.endswith(uid+'/download?model_type=AIVMX')

def test_extra_voice_metadata_has_unique_real_speakers_and_characteristics():
    assert len(EXTRA_VOICES)==9
    assert len({v['speaker'] for v in EXTRA_VOICES})==9
    assert {'Rinne El','Aida Shigeru','Mai','Nise','Sukiyaki Umataro',
            'Satsuki','Wakana','Rena','Moe'}=={v['name'].split(' — ',1)[0] for v in EXTRA_VOICES}
    assert all(' · ' in v['name'] and v['styles'] for v in EXTRA_VOICES)

def test_dynamic_aivis_style_resolves_by_speaker_uuid_and_manifest_name():
    styles=({'id':0,'name':'Tự nhiên','source_name':'ノーマル'},
            {'id':1,'name':'Vui vẻ','source_name':'Happy'})
    v=VoiceInfo('aivis:uuid','Giọng thử','Japanese','Aivis','speaker-uuid',-1,styles)
    backend=LocalVoicevoxBackend('Aivis',10103,[v])
    response=[{'speaker_uuid':'someone-else','styles':[{'name':'ノーマル','id':1}]},
              {'speaker_uuid':'speaker-uuid','styles':[{'name':'ノーマル','id':780001},{'name':'Happy','id':780004}]}]
    backend.request=lambda path,cancel,body=None,params=None: json.dumps(response).encode()
    cancel=threading.Event()
    assert backend.resolve_style_id(v,None,cancel)==780001
    assert backend.resolve_style_id(v,1,cancel)==780004
