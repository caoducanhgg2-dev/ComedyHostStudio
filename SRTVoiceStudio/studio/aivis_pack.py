"""Pinned optional Japanese pack; no download until explicitly selected."""
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
LICENSE_NOTICE=('Mao và Kohaku: chưa có điểm nghe xác nhận. ACML 1.0 cho phép thương mại có điều kiện; '
    'cấm mạo danh, lừa dối, công kích hoặc phê phán cá nhân, tổ chức hay sản phẩm có thật, cùng các giới hạn khác. '
    'Đọc điều khoản đầy đủ trước khi dùng cho nội dung review/comedy. Ghi nguồn gợi ý: AivisSpeech: まお / コハク. '
    'Engine LGPL-3.0; BERT của tsukumijima/ku-nlp: CC-BY-SA-4.0. Tải khoảng 1,4 GB một lần; cần thêm dung lượng giải nén.')

def engine_data_root():
    # Aivis 1.2 uses platformdirs(..., roaming=True). On Windows its shell
    # lookup ignores APPDATA overrides: resolve the same known folder.
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
    fd,temporary=tempfile.mkstemp(prefix='.srtvs-',dir=destination.parent)
    temporary=Path(temporary)
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
    for uid,version,size,sha in [
        ('22e8ed77-94fe-4ef2-871f-a86f94e9a579','1.1.0',255326987,'3f5c08b52bb8a64efd361268580c81510f96c927cd6905aa7dbae6851333270a'),
        ('a59cb814-0083-4369-8542-f51a29e72af7','1.2.0',258037076,'f87ccea2e8e2de0e0bfe52e803945af903b4086bf25621a015111628f00e4119')]:
        result.append(Pack('aivis-'+uid,version,'https://api.aivis-project.com/v1/aivm-models/'+uid+'/download?model_type=AIVMX',sha,size,'raw',uid+'.aivmx','ACML-1.0',LICENSE_URL))
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
    def available(self):
        try:
            marker=json.loads((self.runtime/'ready.json').read_text('utf-8'))
            return marker.get('layout')==2 and Path(marker['engine']).is_file() and all(Path(p).is_file() for p in marker['model_files'])
        except (OSError,ValueError,KeyError,TypeError):return False
    def install(self,cancel,progress=lambda *_:None):
        if os.name!='nt':raise RuntimeError('Gói cài tự động này dành cho Windows x64.')
        files=packs();total=sum(p.size for p in files);done=0;locations=[]
        for p in files:
            locations.append(self.manager.install(p,cancel,lambda n,_,base=done:progress(base+n,total,'Đang tải gói giọng và kiểm tra SHA-256')))
            done+=p.size
        check_cancel(cancel)
        if self.available():return self.runtime
        executable=locations[0]/'Windows-x64/run.exe'
        if not executable.is_file():raise RuntimeError('Cấu trúc engine không khớp bản đã kiểm tra.')
        data=engine_data_root();models=data/'Models'
        bert=data/'BertModelCaches/models--tsukumijima--deberta-v2-large-japanese-char-wwm-onnx/snapshots'/BERT_REVISION
        installed=[]
        for p,location in zip(files[1:],locations[1:]):
            destination=(models if p.filename.endswith('.aivmx') else bert)/p.filename
            install_shared_file(location/p.filename,destination,p.sha256,cancel)
            installed.append(str(destination))
        self.runtime.mkdir(parents=True,exist_ok=True)
        marker=self.runtime/'ready.tmp'
        marker.write_text(json.dumps({'engine':str(executable),'version':'1.2.0','layout':2,
                                     'model_data':str(data),'model_files':installed}),encoding='utf-8')
        check_cancel(cancel);os.replace(marker,self.runtime/'ready.json')
        return self.runtime
    def backend(self):
        if not self.available():return None
        metadata=json.loads((self.runtime/'ready.json').read_text('utf-8'))
        self.engine=LocalEngine(metadata['engine'],self.runtime/'data')
        voices=[]
        for uid,name,base,styles in [
            ('e756b8e4-b606-4e15-99b1-3f9c6a1b2317','Mao — Nữ · Tự nhiên, mềm, hội thoại đời thường',888753760,['Tự nhiên','Đời thường','Ngọt ngào','Điềm tĩnh','Trêu đùa','Man mác buồn']),
            ('5680ac39-43c9-487a-bc3e-018c0d29cc38','Kohaku — Nữ · Nhẹ, ngọt, thư giãn',1878365376,['Tự nhiên','Ngọt ngào','Man mác buồn','Buồn ngủ'])]:
            voices.append(VoiceInfo('aivis:'+uid,name,'Japanese','Aivis',uid,base,tuple(dict(id=base+i,name=s) for i,s in enumerate(styles)),
                'ACML-1.0 • Thương mại có điều kiện',LICENSE_URL))
        return LocalVoicevoxBackend('Aivis',10103,voices,self.engine.start)
    def close(self):
        if self.engine:self.engine.close()
