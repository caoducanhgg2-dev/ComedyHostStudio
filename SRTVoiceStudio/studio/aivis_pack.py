"""Pinned optional Japanese Aivis pack; no download until explicitly selected."""
import json
import os
from pathlib import Path
import tempfile
import hashlib
from .audio import check_cancel
from .paths import data_dir
from .voice_packs import Pack,PackManager
from .voice_backends import VoiceInfo,LocalVoicevoxBackend
from .local_engine import LocalEngine

ENGINE_SOURCE='https://github.com/Aivis-Project/AivisSpeech-Engine'
BERT_SOURCE='https://huggingface.co/tsukumijima/deberta-v2-large-japanese-char-wwm-onnx'
BERT_REVISION='d701ec67708287b20d2063270f6b535e6eed09ab'
LICENSE_URL='https://github.com/Aivis-Project/ACML/blob/master/ACML-1.0.md'
HUB='https://hub.aivis-project.com/aivm-models/'
LICENSE_NOTICE=('Gói Aivis Nhật gồm Mao, Kohaku và 4 giọng mở rộng. Các mô tả chất giọng chỉ để chọn nhanh, '
    'không phải điểm chất lượng nghe. Tất cả 6 model trong gói này dùng ACML 1.0; thương mại có điều kiện, '
    'có các giới hạn về mạo danh, lừa dối, công kích/phê phán cá nhân, tổ chức hoặc sản phẩm có thật. '
    'Đọc điều khoản đầy đủ trước khi dùng cho nội dung review/comedy. Engine LGPL-3.0; BERT CC-BY-SA-4.0. '
    'Chọn giọng cần tải bên dưới. Engine và bộ ngôn ngữ dùng chung chỉ tải một lần; model đã có được giữ nguyên.')

# Pinned AIVMX assets. Size and SHA-256 come from the AivisHub AIVMX metadata.
MODEL_PACKS=(
    ('22e8ed77-94fe-4ef2-871f-a86f94e9a579','1.1.0',255326987,'3f5c08b52bb8a64efd361268580c81510f96c927cd6905aa7dbae6851333270a'),
    ('a59cb814-0083-4369-8542-f51a29e72af7','1.2.0',258037076,'f87ccea2e8e2de0e0bfe52e803945af903b4086bf25621a015111628f00e4119'),
    ('f5017410-fbb5-49e1-97cb-e785f42e15f5','1.0.0',252769346,'e7ac9e2636f59d6f6512016d0752f9e9f89c2b3ffd2012a6a1b92791330e23bc'),
    ('47e53151-a378-46f3-abee-ce13aa07feb1','1.0.0',251137086,'6dabe29de5ec2c1715e12a430805e1bff6ec64a315cccec2d26fad029df83243'),
    ('e9339137-2ae3-4d41-9394-fb757a7e61e6','1.0.0',250837473,'eca53a500a70746f649572ec186d3b98665606b13e8e8e648f9b10fa8c0000c4'),
    ('6d11c6c2-f4a4-4435-887e-23dd60f8b8dd','1.0.0',250240153,'6ff7eaa61c24d37434e2c6ab672fc3ba189ecc9118c08918a486ed5316e5c9d3'),
)

EXTRA_VOICES=(
    dict(model='f5017410-fbb5-49e1-97cb-e785f42e15f5',speaker='d2c99ca6-73e5-486c-994e-ee0ce2d74928',
         name='Rinne El — Nữ · Trẻ, 5 phong cách bản địa',styles=(('Tự nhiên','ノーマル'),('Giận dữ','Angry'),('Lo lắng','Fear'),('Vui vẻ','Happy'),('Buồn','Sad'))),
    dict(model='47e53151-a378-46f3-abee-ce13aa07feb1',speaker='561e4e59-3bc9-4726-9028-44a3c12a6f1d',
         name='Aida Shigeru — Nam · Baritone, trung niên',styles=(('Tự nhiên','ノーマル'),('Điềm tĩnh','Calm'),('Xa mic','Far'),('Nặng / dày','Heavy'),('Trung tính','Mid'),('Hô lớn','Shout'),('Ngạc nhiên','Surprise'))),
    dict(model='e9339137-2ae3-4d41-9394-fb757a7e61e6',speaker='41b7785f-35cc-4089-a360-dd8a63da5e75',
         name='Mai — Nữ · Trẻ, một phong cách tự nhiên',styles=(('Tự nhiên','ノーマル'),)),
    dict(model='6d11c6c2-f4a4-4435-887e-23dd60f8b8dd',speaker='bf56410a-d8e6-430d-a477-f789e16206d3',
         name='Nise — Nam · Trẻ, một phong cách tự nhiên',styles=(('Tự nhiên','ノーマル'),)),
)

MODEL_NAMES = {
    MODEL_PACKS[0][0]: 'Mao', MODEL_PACKS[1][0]: 'Kohaku',
    **{v['model']: v['name'].split(' — ', 1)[0] for v in EXTRA_VOICES},
}

def selected_packs(model_ids=None):
    selected = set(MODEL_NAMES if model_ids is None else model_ids)
    if not selected or selected - set(MODEL_NAMES):
        raise ValueError('Chọn ít nhất một giọng Nhật hợp lệ.')
    return [p for p in packs() if not p.filename.endswith('.aivmx')
            or p.filename.removesuffix('.aivmx') in selected]

def engine_data_root():
    import ctypes
    buffer=ctypes.create_unicode_buffer(32768)
    status=ctypes.windll.shell32.SHGetFolderPathW(None,26,None,0,buffer)
    if status!=0:raise RuntimeError('Không xác định được thư mục dữ liệu Aivis của Windows.')
    return Path(buffer.value)/'AivisSpeech-Engine'

def install_shared_file(source,destination,expected,cancel):
    """Publish verified bytes without replacing another Aivis user's model."""
    def matches(path):
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while chunk:=stream.read(1024*1024):check_cancel(cancel);digest.update(chunk)
        return digest.hexdigest()==expected
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        if matches(destination):return
        raise RuntimeError('Aivis đã có tệp khác phiên bản; giữ nguyên tệp hiện có: '+str(destination))
    fd,temporary=tempfile.mkstemp(prefix='.srtvs-',dir=destination.parent);temporary=Path(temporary)
    try:
        with os.fdopen(fd,'wb') as dst,Path(source).open('rb') as src:
            while chunk:=src.read(1024*1024):check_cancel(cancel);dst.write(chunk)
        if not matches(temporary):raise RuntimeError('Tệp model thay đổi trong khi cài.')
        check_cancel(cancel)
        try:os.link(temporary,destination)
        except FileExistsError:
            if not matches(destination):raise RuntimeError('Tệp model được ứng dụng khác thay đổi; không ghi đè.')
    finally:temporary.unlink(missing_ok=True)

def packs():
    result=[Pack('aivis-engine-windows','1.2.0',ENGINE_SOURCE+'/releases/download/1.2.0/AivisSpeech-Engine-Windows-x64-1.2.0.7z.001',
        'bfbceba2e14dc7f23c7f3695f9ac0381baf91b15d6544e98384574eaadd271f3',216525495,'7z','engine.7z','LGPL-3.0',ENGINE_SOURCE)]
    for uid,version,size,sha in MODEL_PACKS:
        result.append(Pack('aivis-'+uid,version,'https://api.aivis-project.com/v1/aivm-models/'+uid+'/download?model_type=AIVMX',sha,size,'raw',uid+'.aivmx','ACML-1.0',HUB+uid))
    for name,size,sha in [
        ('model_fp16.onnx',653075699,'23f633ae7c5900ff82b35a428b67a54e7e7911d5d6a6dcfc77967be8f1c94dc6'),
        ('tokenizer_config.json',520,'1cc5203f09ecac12bb7a98a05cb9c2e39a9e37a113a7d85d12542ef29190583b'),
        ('vocab.txt',88151,'902cbd7e218aaf23a72955533293ceac12fcc4e010ad98c0c14757b94ce7abb6'),
        ('special_tokens_map.json',125,'b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3'),
        ('tokenizer.json',430981,'21a17e4d0032739e82dc60f155b4ae37e94519103e0d399657fdd249ec3e7905')]:
        result.append(Pack('aivis-bert-'+name,BERT_REVISION,BERT_SOURCE+'/resolve/'+BERT_REVISION+'/'+name,sha,size,'raw',name,'CC-BY-SA-4.0',BERT_SOURCE))
    return result

class AivisPack:
    def __init__(self):
        self.manager=PackManager();self.runtime=data_dir()/'VoicePacks/aivis-runtime/1.2.0';self.engine=None
    def marker(self):
        try:return json.loads((self.runtime/'ready.json').read_text('utf-8'))
        except (OSError,ValueError,TypeError):return {}
    def available(self):
        try:
            marker=self.marker()
            return marker.get('layout',0)>=2 and Path(marker['engine']).is_file() and all(Path(p).is_file() for p in marker['model_files'])
        except (KeyError,TypeError):return False
    def complete(self,model_ids=None):
        if not self.available():return False
        try:
            models=engine_data_root()/'Models'
            return all((models/p.filename).is_file() for p in selected_packs(model_ids)
                       if p.filename.endswith('.aivmx'))
        except Exception:return False
    def download_size(self,model_ids=None):
        return sum(p.size for p in selected_packs(model_ids) if not self.manager.installed(p))
    def install(self,cancel,progress=lambda *_:None,model_ids=None):
        if os.name!='nt':raise RuntimeError('Gói cài tự động này dành cho Windows x64.')
        if self.complete(model_ids):return self.runtime
        files=selected_packs(model_ids);total=sum(p.size for p in files);done=0;locations=[]
        for p in files:
            locations.append(self.manager.install(p,cancel,lambda n,_,base=done:progress(base+n,total,'Đang tải gói giọng Nhật và kiểm tra SHA-256')))
            done+=p.size
        check_cancel(cancel)
        executable=locations[0]/'Windows-x64/run.exe'
        if not executable.is_file():raise RuntimeError('Cấu trúc engine không khớp bản đã kiểm tra.')
        if self.engine:self.engine.close()
        data=engine_data_root();models=data/'Models'
        bert=data/'BertModelCaches/models--tsukumijima--deberta-v2-large-japanese-char-wwm-onnx/snapshots'/BERT_REVISION
        installed=[p for p in self.marker().get('model_files',[]) if Path(p).is_file()]
        for p,location in zip(files[1:],locations[1:]):
            destination=(models if p.filename.endswith('.aivmx') else bert)/p.filename
            install_shared_file(location/p.filename,destination,p.sha256,cancel);installed.append(str(destination))
        self.runtime.mkdir(parents=True,exist_ok=True)
        marker=self.runtime/'ready.tmp'
        marker.write_text(json.dumps({'engine':str(executable),'version':'1.2.0','layout':3,'model_data':str(data),'model_files':list(dict.fromkeys(installed))}),encoding='utf-8')
        check_cancel(cancel);os.replace(marker,self.runtime/'ready.json')
        return self.runtime
    def backend(self):
        if not self.available():return None
        metadata=self.marker();self.engine=LocalEngine(metadata['engine'],self.runtime/'data')
        voices=[]
        models=engine_data_root()/'Models'
        for uid,name,base,styles in [
            ('e756b8e4-b606-4e15-99b1-3f9c6a1b2317','Mao — Nữ · Tự nhiên, mềm, hội thoại đời thường',888753760,['Tự nhiên','Đời thường','Ngọt ngào','Điềm tĩnh','Trêu đùa','Man mác buồn']),
            ('5680ac39-43c9-487a-bc3e-018c0d29cc38','Kohaku — Nữ · Nhẹ, ngọt, thư giãn',1878365376,['Tự nhiên','Ngọt ngào','Man mác buồn','Buồn ngủ'])]:
            model_uid=MODEL_PACKS[0 if uid=='e756b8e4-b606-4e15-99b1-3f9c6a1b2317' else 1][0]
            if not (models/(model_uid+'.aivmx')).is_file():continue
            voices.append(VoiceInfo('aivis:'+uid,name,'Japanese','Aivis',uid,base,tuple(dict(id=base+i,name=s) for i,s in enumerate(styles)),'ACML-1.0 • Thương mại có điều kiện',LICENSE_URL))
        try:models=engine_data_root()/'Models'
        except Exception:models=None
        for meta in EXTRA_VOICES:
            if models is None or not (models/(meta['model']+'.aivmx')).is_file():continue
            styles=tuple(dict(id=i,name=display,source_name=source) for i,(display,source) in enumerate(meta['styles']))
            voices.append(VoiceInfo('aivis:'+meta['speaker'],meta['name'],'Japanese','Aivis',meta['speaker'],-1,styles,'ACML-1.0 • Thương mại có điều kiện',HUB+meta['model']))
        return LocalVoicevoxBackend('Aivis',10103,voices,self.engine.start)
    def close(self):
        if self.engine:self.engine.close()

