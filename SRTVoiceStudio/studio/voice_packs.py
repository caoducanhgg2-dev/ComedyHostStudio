"""Version-isolated, verified optional assets. Nothing is downloaded on import."""
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import urllib.request
import zipfile
from .audio import check_cancel, Cancelled
from .paths import data_dir


@dataclass(frozen=True)
class Pack:
    id: str
    version: str
    url: str
    sha256: str
    size: int
    format: str
    filename: str
    license: str
    source: str

    def __post_init__(self):
        for value in (self.id,self.version,self.filename):
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',value):
                raise ValueError('Tên gói giọng không hợp lệ.')
        if not re.fullmatch(r'[0-9a-f]{64}',self.sha256) or self.size<=0:
            raise ValueError('Gói giọng phải có SHA-256 và kích thước xác định.')
        if self.format not in ('raw','zip','7z'):raise ValueError('Định dạng gói chưa được hỗ trợ.')
        if not self.url.startswith('https://'):raise ValueError('Gói giọng phải dùng HTTPS.')
        if not self.license or not self.source:raise ValueError('Thiếu giấy phép hoặc nguồn gói giọng.')


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def safe_member(name):
    # Archives use forward slashes; reject Windows drive/UNC and traversal too.
    if '\\' in name or ':' in name:raise ValueError('Đường dẫn không an toàn trong gói giọng.')
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:raise ValueError('Đường dẫn không an toàn trong gói giọng.')


class PackManager:
    def __init__(self,folder=None,opener=None):
        self.folder=Path(folder) if folder else data_dir()/'VoicePacks'
        self.opener=opener or urllib.request.build_opener()

    def location(self,pack):return self.folder/pack.id/pack.version

    def installed(self,pack):
        marker=self.location(pack)/'pack.json'
        try:
            metadata=json.loads(marker.read_text('utf-8'))
            return metadata['pack']==asdict(pack) and all(
                (self.location(pack)/name).is_file() and digest(self.location(pack)/name)==sha
                for name,sha in metadata['files'].items()) and bool(metadata['files'])
        except (OSError,ValueError,KeyError,TypeError):return False

    def install(self,pack,cancel,progress=lambda *_:None):
        check_cancel(cancel)
        if self.installed(pack):return self.location(pack)
        target=self.location(pack)
        # A corrupt existing version is reported rather than overwritten while
        # an engine might still have its models open. Other versions are kept.
        if target.exists():raise RuntimeError('Gói hiện có bị thiếu hoặc sai checksum; cần sửa gói trước khi dùng.')
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.install-',dir=target.parent) as temp:
            temp=Path(temp);archive=temp/'download.part';payload=temp/'payload';payload.mkdir()
            self.download(pack,archive,cancel,progress)
            check_cancel(cancel)
            if pack.format=='raw':shutil.move(str(archive),str(payload/pack.filename))
            elif pack.format=='zip':
                with zipfile.ZipFile(archive) as z:
                    if sum(i.file_size for i in z.infolist())>max(pack.size*30,1024**3):raise ValueError('Gói giải nén quá lớn.')
                    for info in z.infolist():
                        safe_member(info.orig_filename)
                        if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Không chấp nhận liên kết trong gói.')
                    for info in z.infolist():check_cancel(cancel);z.extract(info,payload)
            else:
                import py7zr
                with py7zr.SevenZipFile(archive) as z:
                    entries=z.list()
                    if sum(i.uncompressed for i in entries)>max(pack.size*30,1024**3):raise ValueError('Gói giải nén quá lớn.')
                    for info in entries:
                        safe_member(info.filename)
                        if info.is_symlink:raise ValueError('Không chấp nhận liên kết trong gói.')
                    z.extractall(payload)
            check_cancel(cancel)
            files={}
            for file in payload.rglob('*'):
                check_cancel(cancel)
                if file.is_symlink():raise ValueError('Không chấp nhận liên kết trong gói.')
                if file.is_file():files[file.relative_to(payload).as_posix()]=digest(file)
            if not files or 'pack.json' in files:raise ValueError('Nội dung gói giọng không hợp lệ.')
            (payload/'pack.json').write_text(json.dumps({'pack':asdict(pack),'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
            check_cancel(cancel)
            os.rename(payload,target)
        return target

    def download(self,pack,path,cancel,progress):
        # Retry inside this staging directory. Cancel/failure removes partial
        # files with the outer TemporaryDirectory; no half-installed pack.
        for attempt in range(3):
            check_cancel(cancel)
            offset=path.stat().st_size if path.exists() else 0
            headers={'User-Agent':'SRTVoiceStudio/1.2'}
            if offset:headers['Range']=f'bytes={offset}-'
            try:
                request=urllib.request.Request(pack.url,headers=headers)
                with self.opener.open(request,timeout=20) as response:
                    status=getattr(response,'status',200)
                    append=status==206 and offset>0
                    if status==206 and (not append or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):
                        path.unlink(missing_ok=True);raise RuntimeError('Máy chủ trả sai vị trí tải tiếp.')
                    count=offset if append else 0
                    with path.open('ab' if append else 'wb') as output:
                        while True:
                            check_cancel(cancel);chunk=response.read(256*1024)
                            if not chunk:break
                            count+=len(chunk)
                            if count>pack.size:raise RuntimeError('Kích thước gói tải về vượt manifest.')
                            output.write(chunk);progress(count,pack.size)
                        output.flush();os.fsync(output.fileno())
                if count!=pack.size:raise RuntimeError('Gói tải về chưa đầy đủ.')
                if digest(path)!=pack.sha256:
                    path.unlink(missing_ok=True);raise RuntimeError('Gói giọng sai SHA-256.')
                return
            except Cancelled:raise
            except Exception:
                if attempt==2:raise
