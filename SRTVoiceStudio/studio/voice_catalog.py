"""Static optional-voice catalogue used by the UI.

Catalogue entries are metadata only. Synthesis is still routed exclusively through
registered local backends, so a visible but uninstalled voice can never render.
"""
from .voice_backends import VoiceInfo

ACML_URL='https://github.com/Aivis-Project/ACML/blob/master/ACML-1.0.md'
HUB='https://hub.aivis-project.com/aivm-models/'
KORVA_SOURCE='https://huggingface.co/dogenthq/KorvaTTS'
KORVA_LICENSE='Apache-2.0'

def _aivis_dynamic(voice_id,name,speaker,model,styles,license_text='ACML-1.0 • Thương mại có điều kiện'):
    return VoiceInfo(
        'aivis:'+speaker,name,'Japanese','Aivis',speaker,-1,
        tuple(dict(id=i,name=display,source_name=source)
              for i,(display,source) in enumerate(styles)),
        license_text,HUB+model)

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
    _aivis_dynamic(
        'rinne','Rinne El — Nữ · Trẻ, sáng, giàu cảm xúc',
        'd2c99ca6-73e5-486c-994e-ee0ce2d74928','f5017410-fbb5-49e1-97cb-e785f42e15f5',
        (('Tự nhiên','ノーマル'),('Giận dữ','Angry'),('Lo lắng','Fear'),
         ('Vui vẻ','Happy'),('Buồn','Sad'))),
    _aivis_dynamic(
        'aida','Aida Shigeru — Nam · Baritone, trung niên, kể chuyện',
        '561e4e59-3bc9-4726-9028-44a3c12a6f1d','47e53151-a378-46f3-abee-ce13aa07feb1',
        (('Tự nhiên','ノーマル'),('Điềm tĩnh','Calm'),('Xa mic','Far'),('Nặng / dày','Heavy'),
         ('Trung tính','Mid'),('Hô lớn','Shout'),('Ngạc nhiên','Surprise'))),
    _aivis_dynamic(
        'mai','Mai — Nữ · Trẻ, mềm, biểu cảm',
        '41b7785f-35cc-4089-a360-dd8a63da5e75','e9339137-2ae3-4d41-9394-fb757a7e61e6',
        (('Tự nhiên','ノーマル'),)),
    _aivis_dynamic(
        'nise','Nise — Nam · Trẻ, tự nhiên, hội thoại',
        'bf56410a-d8e6-430d-a477-f789e16206d3','6d11c6c2-f4a4-4435-887e-23dd60f8b8dd',
        (('Tự nhiên','ノーマル'),)),

    # 1.7.1 expansion. Only models with commercial-compatible catalogue licenses
    # are shown here; ACML-NC and custom-license models are intentionally excluded.
    _aivis_dynamic(
        'umataro','Sukiyaki Umataro — Nam · Trẻ, thấp, điềm tĩnh',
        'c99b650e-4d24-4528-a7a3-6d0f9692f839','f493ab6c-1ffa-4534-9bbd-2ba398f17cd5',
        (('Tự nhiên','ノーマル'),),'CC0'),
    _aivis_dynamic(
        'satsuki','Satsuki — Nữ · Trẻ, tự nhiên, nhiều sắc thái',
        '161ab385-07a5-4dd6-a045-5b0f21dfd9ec','21d8d535-f206-462d-a3bb-05f8252dede7',
        (('Tự nhiên','ノーマル'),('Buồn','kanasimi_kanasimi'),('Vui','uresii_uresii'),
         ('Bình thường','hutuu_hutuu'),('Ngạc nhiên','odoroki_odoroki'))),
    _aivis_dynamic(
        'wakana','Wakana — Nữ · Trẻ, sáng, biểu cảm',
        'ef92118d-eda3-49d9-858d-1e9ae4dae714','f83c385c-829b-40c4-8c11-639027e61636',
        (('Tự nhiên','ノーマル'),('Buồn','悲しい'),('Vui','嬉しい'),
         ('Bình thường','普通'),('Ngạc nhiên','驚き'))),
    _aivis_dynamic(
        'rena','Rena — Nữ · Trẻ, tự nhiên, hội thoại',
        '4a43610f-8ace-4fe2-9541-eb26255f1927','b1b8072f-809f-4c6d-9ba1-2ca94d9c3663',
        (('Tự nhiên','ノーマル'),('Buồn','kanasimi_kanasimi'),('Vui','uresii_uresii'),
         ('Bình thường','hutuu_hutuu'),('Ngạc nhiên','odoroki_odoroki'))),
    _aivis_dynamic(
        'moe','Moe — Nữ · Trẻ, mềm, nhiều sắc thái',
        '47ddff3b-10b4-48e8-8d5d-692461fa7f96','9a7feb22-b6f3-4f79-92d9-26849e063fa1',
        (('Tự nhiên','ノーマル'),('Buồn','kanasimi_kanasimi'),('Vui','uresii_uresii'),
         ('Bình thường','hutuu_hutuu'),('Ngạc nhiên','odoroki_odoroki'))),
)

_KORVA=(
    ('bao_kim','Bảo Kim','Nữ'),
    ('khanh_vy','Khánh Vy','Nữ'),
    ('ngoc_huyen','Ngọc Huyền','Nữ'),
    ('phuong_linh','Phương Linh','Nữ'),
    ('quynh_nhu','Quỳnh Như','Nữ'),
    ('gia_bao','Gia Bảo','Nam'),
    ('hoang_nam','Hoàng Nam','Nam'),
    ('huu_dat','Hữu Đạt','Nam'),
    ('quang_huy','Quang Huy','Nam'),
    ('thanh_phong','Thanh Phong','Nam'),
)
KORVA_CATALOG=tuple(
    VoiceInfo('korva:'+key,f'{display} — {gender} · KorvaTTS Việt',
              'Vietnamese','Korva',key,0,(),KORVA_LICENSE,KORVA_SOURCE)
    for key,display,gender in _KORVA
)

OPTIONAL_CATALOG=AIVIS_CATALOG+KORVA_CATALOG

def catalog_voices(language=None):
    if language is None:
        return OPTIONAL_CATALOG
    return tuple(v for v in OPTIONAL_CATALOG if v.language==language)

def aivis_catalog():
    return AIVIS_CATALOG

def korva_catalog():
    return KORVA_CATALOG

def catalog_ids():
    return {v.id for v in OPTIONAL_CATALOG}
