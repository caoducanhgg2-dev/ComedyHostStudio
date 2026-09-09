"""Build machine only. No downloads or dependency installation on the user's PC."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix+'.part')
    for attempt in range(4):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {'User-Agent':'SRTVoiceStudio-Build/1.0'}
            if offset:
                headers['Range'] = f'bytes={offset}-'
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
                append = response.status == 206 and offset > 0
                if append and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                    partial.unlink(missing_ok=True)
                    raise RuntimeError('Invalid resume range')
                expected = int(response.headers.get('Content-Length','0'))
                written = 0
                with partial.open('ab' if append else 'wb') as out:
                    while chunk := response.read(1024*1024):
                        out.write(chunk)
                        written += len(chunk)
                if expected and written != expected:
                    raise RuntimeError('Incomplete download')
            partial.replace(destination)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    models=ROOT/'models'
    manifest={}
    for name in ('kokoro-v1.0.onnx','voices-v1.0.bin'):
        dest=models/name
        if not dest.exists():
            download('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'+name,dest)
        if dest.stat().st_size < 1_000_000:
            raise RuntimeError(f'Invalid model size: {name}')
        manifest[name]=digest(dest)
    (models/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    binary=ROOT/'bin'
    binary.mkdir(exist_ok=True)
    archives=ROOT/'build-assets'
    archive=archives/'ffmpeg-7.1.1.zip'
    if not archive.exists():
        download('https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip',archive)
    with zipfile.ZipFile(archive) as z:
        for name in ('ffmpeg.exe','ffprobe.exe'):
            members=[n for n in z.namelist() if n.endswith('/bin/'+name)]
            if len(members)!=1:
                raise RuntimeError('FFmpeg archive layout changed')
            with z.open(members[0]) as src, (binary/name).open('wb') as dst:
                shutil.copyfileobj(src,dst)
        notices=ROOT/'third_party'
        notices.mkdir(exist_ok=True)
        for name in z.namelist():
            if name.endswith(('LICENSE','LICENSE.txt','README.txt')):
                (notices/('ffmpeg-'+Path(name).name)).write_bytes(z.read(name))
    (ROOT/'build-assets'/'sha256.json').write_text(json.dumps({
        **manifest, 'ffmpeg-7.1.1.zip':digest(archive)},indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
