import subprocess
import sys
import tempfile
import wave
from pathlib import Path
import numpy as np
from .paths import executable, workspace
from .timeline import RATE

class Cancelled(Exception):
    pass

def check_cancel(cancel):
    if cancel.is_set():
        raise Cancelled('Đã hủy. Không xuất MP3 mới.')

def run(args, cancel, cwd=None):
    with tempfile.TemporaryFile(dir=workspace()) as log:
        proc = subprocess.Popen(args, stdout=log, stderr=log, cwd=cwd,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        try:
            while True:
                check_cancel(cancel)
                try:
                    code = proc.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if code:
                log.seek(0)
                raise RuntimeError(log.read().decode('utf-8', 'replace')[-6000:])
            log.seek(0)
            return log.read().decode('utf-8', 'replace')
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

def write_wav(path, samples, rate=RATE):
    pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())

def convert(samples, rate, tempo, folder, cancel):
    source, target = Path(folder)/'source.wav', Path(folder)/'fit.raw'
    write_wav(source, samples, rate)
    run([executable('ffmpeg'), '-nostdin', '-v', 'error', '-y', '-i', str(source),
         '-af', f'atempo={tempo:.9f}', '-ar', str(RATE), '-ac', '1',
         '-f', 'f32le', str(target)], cancel)
    result = np.fromfile(target, dtype='<f4').copy()
    source.unlink(missing_ok=True)
    target.unlink(missing_ok=True)
    return result

def normalize(samples):
    active = samples[np.abs(samples) > 0.001]
    if not len(active):
        return samples
    rms = float(np.sqrt(np.mean(active.astype(np.float64)**2)))
    peak = float(np.max(np.abs(samples)))
    gain = min(10**(-20/20) / max(rms, 1e-9), 0.84 / max(peak, 1e-9), 4.0)
    return samples * gain

def encode(master, destination, cancel):
    # Only one lossy encoding, no MP3 caption concatenation.
    run([executable('ffmpeg'), '-nostdin', '-v', 'error', '-y', '-f', 'f32le',
         '-ar', str(RATE), '-ac', '1', '-i', str(master), '-c:a', 'libmp3lame',
         '-b:a', '192k', '-write_xing', '1', str(destination)], cancel)
