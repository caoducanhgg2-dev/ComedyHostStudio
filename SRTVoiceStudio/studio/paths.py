from pathlib import Path
import os
import shutil
import sys

def root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))

def data_dir():
    base = os.environ.get('LOCALAPPDATA')
    result = (Path(base) if base else Path.home() / 'AppData' / 'Local') / 'SRTVoiceStudio'
    result.mkdir(parents=True, exist_ok=True)
    return result

def workspace():
    path = data_dir() / 'Temp'
    path.mkdir(parents=True, exist_ok=True)
    return path

def clean_stale():
    # Called only after the process-wide single-instance lock is acquired.
    for p in workspace().glob('job-*'):
        if p.is_dir() and not p.is_symlink():
            marker = p/'staged-output.txt'
            if marker.is_file():
                try:
                    staged = Path(marker.read_text(encoding='utf-8'))
                    if staged.name.startswith('.srtvs-') and staged.suffix == '.mp3':
                        staged.unlink(missing_ok=True)
                except (OSError, UnicodeError):
                    pass
            shutil.rmtree(p, ignore_errors=True)

def executable(name):
    bundled = root() / 'bin' / (name + ('.exe' if sys.platform == 'win32' else ''))
    if bundled.is_file():
        return str(bundled)
    if not getattr(sys, 'frozen', False):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(f'Thiếu {name} trong bộ cài. Hãy cài lại ứng dụng.')
