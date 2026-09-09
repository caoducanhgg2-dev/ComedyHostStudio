"""Test the installed app under a Unicode path and a PATH without Python."""
import os
from pathlib import Path
import subprocess
import json

root=Path(__file__).resolve().parents[1]
dest=Path(os.environ['LOCALAPPDATA'])/'SRTVS-Test'/'LỒNG TIẾNG'/'SRT Voice Studio'
installer=root/'installer-output'/'SRTVoiceStudio_Setup.exe'
subprocess.run([str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={dest}'],check=True,timeout=180)
env=os.environ.copy()
env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
env['PYTHONHOME']='C:\\nonexistent-python'
env['PYTHONPATH']='C:\\nonexistent-python-packages'
env['TEMP']=str(dest/'missing-system-temp')
env['TMP']=env['TEMP']
env['HF_HUB_OFFLINE']='1'
env['TRANSFORMERS_OFFLINE']='1'
exe=dest/'SRTVoiceStudio.exe'
# Network denied to this executable during the acceptance test, not just cache flags.
rule='SRTVoiceStudio CI offline test'
subprocess.run(['netsh','advfirewall','firewall','add','rule',f'name={rule}','dir=out',
                'action=block',f'program={exe}','enable=yes'],check=True)
try:
    subprocess.run([str(exe),'--self-test'],env=env,check=True,timeout=900)
    subprocess.run([str(exe),'--ui-smoke'],env=env,check=True,timeout=40)
    report=Path(os.environ['LOCALAPPDATA'])/'SRTVoiceStudio'/'self-test.json'
    data=json.loads(report.read_text('utf-8'))
    if data.get('passed') is not True:
        raise RuntimeError(data)
    (root/'installer-output'/'acceptance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    for name in ('self-test.json','logs/latest.log'):
        log=Path(os.environ['LOCALAPPDATA'])/'SRTVoiceStudio'/name
        if log.exists():
            print(log.read_text('utf-8',errors='replace')[-20000:],flush=True)
    subprocess.run(['netsh','advfirewall','firewall','delete','rule',f'name={rule}'],check=False)
    if (dest/'unins000.exe').exists():
        subprocess.run([str(dest/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=180)
if exe.exists():
    raise RuntimeError('Uninstall did not remove app executable')
