"""Fail early with readable app logs, before spending time compressing an installer."""
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
exe=root/'dist'/'SRTVoiceStudio'/'SRTVoiceStudio.exe'
result=subprocess.run([str(exe),'--self-test'],timeout=900)
appdata=Path(os.environ['LOCALAPPDATA'])/'SRTVoiceStudio'
for name in ('self-test.json','logs/latest.log'):
    file=appdata/name
    if file.exists():
        print(f'APP REPORT {name}:',flush=True)
        print(file.read_text('utf-8',errors='replace')[-20000:],flush=True)
raise SystemExit(result.returncode)
