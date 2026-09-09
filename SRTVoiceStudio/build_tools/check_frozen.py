"""Exercise the frozen runtime under the same hostile paths as the installed app."""
import os
import sys
import shutil
from pathlib import Path
import subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
root=Path(__file__).resolve().parents[1]
folder=Path(os.environ['LOCALAPPDATA'])/'Frozen LỒNG TIẾNG'/'SRT Voice Studio'
shutil.copytree(root/'dist'/'SRTVoiceStudio',folder,dirs_exist_ok=True)
env=os.environ.copy()
env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
env['PYTHONHOME']='C:\\nonexistent-python'
env['PYTHONPATH']='C:\\nonexistent-python-packages'
env['TEMP']=str(folder/'missing-system-temp')
env['TMP']=env['TEMP']
appdata=Path(os.environ['LOCALAPPDATA'])/'SRTVoiceStudio'
try:
    result=subprocess.run([str(folder/'SRTVoiceStudio.exe'),'--self-test'],env=env,timeout=900)
finally:
    for name in ('self-test.json','logs/latest.log'):
        file=appdata/name
        if file.exists():
            print(f'APP REPORT {name}:',flush=True)
            print(file.read_text('utf-8',errors='replace')[-20000:],flush=True)
    shutil.rmtree(folder,ignore_errors=True)
raise SystemExit(result.returncode)
