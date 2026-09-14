import json
import threading
from studio.aivis_pack import MODEL_PACKS,EXTRA_VOICES,packs
from studio.voice_backends import LocalVoicevoxBackend,VoiceInfo

EXPECTED={
 'f5017410-fbb5-49e1-97cb-e785f42e15f5':(252769346,'e7ac9e2636f59d6f6512016d0752f9e9f89c2b3ffd2012a6a1b92791330e23bc'),
 '47e53151-a378-46f3-abee-ce13aa07feb1':(251137086,'6dabe29de5ec2c1715e12a430805e1bff6ec64a315cccec2d26fad029df83243'),
 'e9339137-2ae3-4d41-9394-fb757a7e61e6':(250837473,'eca53a500a70746f649572ec186d3b98665606b13e8e8e648f9b10fa8c0000c4'),
 '6d11c6c2-f4a4-4435-887e-23dd60f8b8dd':(250240153,'6ff7eaa61c24d37434e2c6ab672fc3ba189ecc9118c08918a486ed5316e5c9d3'),
}

def test_four_extra_japanese_models_are_exactly_pinned():
    manifest={uid:(size,sha) for uid,version,size,sha in MODEL_PACKS}
    assert all(manifest[uid]==value for uid,value in EXPECTED.items())
    by_id={p.filename.removesuffix('.aivmx'):p for p in packs() if p.filename.endswith('.aivmx')}
    for uid,(size,sha) in EXPECTED.items():
        p=by_id[uid]
        assert p.size==size and p.sha256==sha and p.license=='ACML-1.0'
        assert p.url.endswith(uid+'/download?model_type=AIVMX')

def test_extra_voice_metadata_has_unique_real_speakers_and_characteristics():
    assert len(EXTRA_VOICES)==4
    assert len({v['speaker'] for v in EXTRA_VOICES})==4
    assert {'Rinne El','Aida Shigeru','Mai','Nise'}=={v['name'].split(' — ',1)[0] for v in EXTRA_VOICES}
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
