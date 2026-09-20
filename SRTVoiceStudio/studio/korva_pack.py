"""Pinned optional Vietnamese KorvaTTS assets; no download until user clicks install."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import tempfile

from .audio import check_cancel
from .paths import data_dir
from .voice_packs import Pack, PackManager, digest
from .korva_backend import KorvaBackend

REVISION='e5c8c218e93c1d8daa53bfe0e62b8fbc5a5e991d'
SOURCE='https://huggingface.co/dogenthq/KorvaTTS'
LICENSE_URL='https://huggingface.co/dogenthq/KorvaTTS/blob/'+REVISION+'/MODEL_LICENSE.md'
LICENSE_NOTICE=(
    'KorvaTTS: 10 giọng Việt (5 nữ, 5 nam), chạy local bằng ONNX Runtime. '
    'Code, model weights và voice styles được công bố Apache-2.0. '
    'Gói model được tải riêng, ghim theo revision và kiểm tra SHA-256 trước khi kích hoạt.'
)

# path, exact bytes, SHA-256. Large-file ETags were resolved from the pinned
# Hugging Face Xet revision; JSON/style SHA-256 values were computed in CI.
FILES=(
 ('onnx/duration_predictor.onnx',3573391,'26d385840e93bda0395013b719464894d86fb5fb705099de38a759529d27a882'),
 ('onnx/text_encoder.onnx',35678255,'e130d8960cd4c0008ef021a62bfceebb30bec3106d660df1e9d3a0f589853507'),
 ('onnx/vector_estimator.onnx',256700640,'f78d2893feaca9ee7eb54e892d7c65deb4793e5b5e68f6a47a5c594d4696970a'),
 ('onnx/vocoder.onnx',101426104,'91795b4dd3ad3b05e5095332aeaf3999f889fd8496e016682da60092c5ed9295'),
 ('onnx/tts.json',8493,'d9b6bd2844a45ecccfd521b2defeaf74d45ea23e8cc099b980c1e0198c7f2365'),
 ('onnx/unicode_indexer.json',277676,'9bf7346e43883a81f8645c81224f786d43c5b57f3641f6e7671a7d6c493cb24f'),
 ('voice_styles/bao_kim.json',271241,'89cd8c7d9c834118b523d04ba8d556e7664fc9c3fc7fd5247194355d2561234b'),
 ('voice_styles/khanh_vy.json',270909,'8fae3454ffb773fc0cbcdbe75625c4f2779b9a657d485416835287a95b673e8e'),
 ('voice_styles/ngoc_huyen.json',273504,'9acca9036984db64c5dc72d79e5ec685354bd6f9676827c9e5839c72e2c1adeb'),
 ('voice_styles/phuong_linh.json',271332,'a79ea59ad370023e34f24da9e4feafb748262e0800d070f8d84f7776beef7dbb'),
 ('voice_styles/quynh_nhu.json',271427,'3f41b6c46dd0f480989fce0a1060143310ebbc0c19e56e1dc2ccbafbf8ff973e'),
 ('voice_styles/gia_bao.json',271907,'c6e04d3219695fd0f76ad7602c572c0a10d2d4750237e46ec68b57befc3d1e74'),
 ('voice_styles/hoang_nam.json',271277,'e18fbef2e3b85ca3a883c019031dcb135f3d52f75a75678d95d677b05e61c77a'),
 ('voice_styles/huu_dat.json',271469,'508256f14e4bd71971ba2dcde1f0c828b12ad50b1852f43f6f758728a643c112'),
 ('voice_styles/quang_huy.json',271867,'f58c5ad23292b04f5d3dc4588babcd45d5e4e095e5f02fc10891764618c3f163'),
 ('voice_styles/thanh_phong.json',270538,'a41e410887d029480f36c154a11e0df951f621e0d6bc7efaffe923aecc105ec9'),
)

def packs():
    result=[]
    for index,(path,size,sha) in enumerate(FILES):
        safe=path.replace('/','-')
        result.append(Pack(
            'korva-'+safe,REVISION[:12],
            f'https://huggingface.co/dogenthq/KorvaTTS/resolve/{REVISION}/{path}?download=true',
            sha,size,'raw',Path(path).name,'Apache-2.0',SOURCE))
    return tuple(result)

class KorvaPack:
    def __init__(self):
        self.manager=PackManager()
        self.runtime=data_dir()/'VoicePacks'/'korva-runtime'/REVISION[:12]

    @property
    def assets(self):return self.runtime/'assets'

    def marker(self):
        try:return json.loads((self.runtime/'ready.json').read_text('utf-8'))
        except (OSError,ValueError,TypeError):return {}

    def available(self):
        marker=self.marker()
        if marker.get('revision')!=REVISION:return False
        try:
            for path,size,sha in FILES:
                file=self.assets/path
                if not file.is_file() or file.stat().st_size!=size or digest(file)!=sha:return False
            return True
        except OSError:return False

    def complete(self):return self.available()

    def install(self,cancel,progress=lambda *_:None):
        if self.available():return self.assets
        if self.runtime.exists():
            raise RuntimeError('Gói Korva hiện có bị thiếu hoặc sai checksum; giữ nguyên để không ghi đè dữ liệu bất thường.')
        files=packs();total=sum(p.size for p in files);done=0;locations=[]
        for p in files:
            location=self.manager.install(
                p,cancel,lambda n,_,base=done:progress(base+n,total,'Đang tải gói giọng Việt Korva và kiểm tra SHA-256'))
            locations.append(location);done+=p.size
        check_cancel(cancel)
        self.runtime.parent.mkdir(parents=True,exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix='.korva-',dir=self.runtime.parent))
        try:
            assets=staging/'assets'
            for (path,size,sha),pack,location in zip(FILES,files,locations):
                check_cancel(cancel)
                source=location/pack.filename;destination=assets/path
                if source.stat().st_size!=size or digest(source)!=sha:raise RuntimeError('Korva asset sai checksum trước khi kích hoạt.')
                destination.parent.mkdir(parents=True,exist_ok=True)
                try:os.link(source,destination)
                except OSError:shutil.copy2(source,destination)
                if digest(destination)!=sha:raise RuntimeError('Korva asset thay đổi khi kích hoạt.')
            (staging/'ready.json').write_text(json.dumps({
                'revision':REVISION,'files':len(FILES),'voices':10,'license':'Apache-2.0'
            },indent=2),encoding='utf-8')
            check_cancel(cancel);os.rename(staging,self.runtime);staging=None
        finally:
            if staging is not None:shutil.rmtree(staging,ignore_errors=True)
        return self.assets

    def backend(self):
        if not self.available():return None
        return KorvaBackend(self.assets)
