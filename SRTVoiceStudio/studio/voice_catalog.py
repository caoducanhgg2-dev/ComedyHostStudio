"""Static voice catalogue metadata used by the UI.

Optional voices are visible before their models are installed. The catalogue is
metadata only: rendering still routes exclusively through registered backends,
so an uninstalled Aivis voice can never be synthesized accidentally.
"""
from .voice_backends import VoiceInfo

ACML_URL='https://github.com/Aivis-Project/ACML/blob/master/ACML-1.0.md'
HUB='https://hub.aivis-project.com/aivm-models/'

AIVIS_CATALOG=(
    VoiceInfo(
        'aivis:e756b8e4-b606-4e15-99b1-3f9c6a1b2317',
        'Mao — Nữ · Tự nhiên, mềm, hội thoại đời thường',
        'Japanese','Aivis','e756b8e4-b606-4e15-99b1-3f9c6a1b2317',888753760,
        tuple(dict(id=888753760+i,name=s) for i,s in enumerate(
            ('Tự nhiên','Đời thường','Ngọt ngào','Điềm tĩnh','Trêu đùa','Man mác buồn'))),
        'ACML-1.0 • Thương mại có điều kiện',ACML_URL),
    VoiceInfo(
        'aivis:5680ac39-43c9-487a-bc3e-018c0d29cc38',
        'Kohaku — Nữ · Nhẹ, ngọt, thư giãn',
        'Japanese','Aivis','5680ac39-43c9-487a-bc3e-018c0d29cc38',1878365376,
        tuple(dict(id=1878365376+i,name=s) for i,s in enumerate(
            ('Tự nhiên','Ngọt ngào','Man mác buồn','Buồn ngủ'))),
        'ACML-1.0 • Thương mại có điều kiện',ACML_URL),
    VoiceInfo(
        'aivis:d2c99ca6-73e5-486c-994e-ee0ce2d74928',
        'Rinne El — Nữ · Trẻ, sáng, giàu cảm xúc',
        'Japanese','Aivis','d2c99ca6-73e5-486c-994e-ee0ce2d74928',-1,
        tuple(dict(id=i,name=display,source_name=source) for i,(display,source) in enumerate((
            ('Tự nhiên','ノーマル'),('Giận dữ','Angry'),('Lo lắng','Fear'),('Vui vẻ','Happy'),('Buồn','Sad')))),
        'ACML-1.0 • Thương mại có điều kiện',HUB+'f5017410-fbb5-49e1-97cb-e785f42e15f5'),
    VoiceInfo(
        'aivis:561e4e59-3bc9-4726-9028-44a3c12a6f1d',
        'Aida Shigeru — Nam · Baritone, trung niên, kể chuyện',
        'Japanese','Aivis','561e4e59-3bc9-4726-9028-44a3c12a6f1d',-1,
        tuple(dict(id=i,name=display,source_name=source) for i,(display,source) in enumerate((
            ('Tự nhiên','ノーマル'),('Điềm tĩnh','Calm'),('Xa mic','Far'),('Nặng / dày','Heavy'),
            ('Trung tính','Mid'),('Hô lớn','Shout'),('Ngạc nhiên','Surprise')))),
        'ACML-1.0 • Thương mại có điều kiện',HUB+'47e53151-a378-46f3-abee-ce13aa07feb1'),
    VoiceInfo(
        'aivis:41b7785f-35cc-4089-a360-dd8a63da5e75',
        'Mai — Nữ · Trẻ, mềm, biểu cảm',
        'Japanese','Aivis','41b7785f-35cc-4089-a360-dd8a63da5e75',-1,
        (dict(id=0,name='Tự nhiên',source_name='ノーマル'),),
        'ACML-1.0 • Thương mại có điều kiện',HUB+'e9339137-2ae3-4d41-9394-fb757a7e61e6'),
    VoiceInfo(
        'aivis:bf56410a-d8e6-430d-a477-f789e16206d3',
        'Nise — Nam · Trẻ, tự nhiên, hội thoại',
        'Japanese','Aivis','bf56410a-d8e6-430d-a477-f789e16206d3',-1,
        (dict(id=0,name='Tự nhiên',source_name='ノーマル'),),
        'ACML-1.0 • Thương mại có điều kiện',HUB+'6d11c6c2-f4a4-4435-887e-23dd60f8b8dd'),
)


def catalog_voices():
    return AIVIS_CATALOG


def catalog_ids():
    return {v.id for v in AIVIS_CATALOG}
