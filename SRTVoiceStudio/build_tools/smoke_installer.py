"""Clean install and upgrade the exact verified 1.3 artifact; real offline installed acceptance."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
sys.stderr.reconfigure(encoding='utf-8',errors='replace')
from pathlib import Path
import subprocess
import json
import hashlib
import winreg

root=Path(__file__).resolve().parents[1]
installer=root/'installer-output'/'SRTVoiceStudio_Setup_1.7.2.exe'
baselines=list((root/'baseline-installer').rglob('SRTVoiceStudio_Setup_1.3.0.exe'))
assert len(baselines)==1, f'Expected one baseline installer, found: {baselines}'
baseline=baselines[0]
expected='f955633c700a48b87e8c96b4b2ad8a40d0fc522a0720a37eff3d51dae2a9a6cc'
with baseline.open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,'Baseline installer checksum mismatch'
appkey=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{68F0C1C1-17CB-4CED-8261-5C18EB92571A}_is1'
appdata=Path(os.environ['LOCALAPPDATA'])/'SRTVoiceStudio'
target_version='1.7.2'
results={'version':target_version,'baseline_sha256':expected,'scenarios':{}}

def registry():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,appkey,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
        return {name:winreg.QueryValueEx(key,name)[0] for name in ('DisplayName','DisplayVersion','InstallLocation')}

def install(file,dest=None):
    args=[str(file),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-']
    if dest is not None:args.append(f'/DIR={dest}')
    subprocess.run(args,check=True,timeout=240)

def read_report(name):
    data=json.loads((appdata/name).read_text('utf-8'))
    assert data.get('passed') is True,data
    assert data.get('version')==target_version,data
    return data

for scenario in ('upgrade','clean'):
    dest=Path(r'D:\LỒNG TIẾNG\SRT Voice Studio') if scenario=='upgrade' else Path(os.environ['LOCALAPPDATA'])/'Programs'/'SRTVoiceStudio'
    exe=dest/'SRTVoiceStudio.exe';rule='SRTVoiceStudio CI offline '+scenario;blocked=[]
    try:
        if scenario=='upgrade':
            install(baseline,dest)
            old=registry();assert old['DisplayVersion']=='1.3.0',old
            sentinel=appdata/'VoicePacks'/'keep-upgrade.txt';sentinel.parent.mkdir(parents=True,exist_ok=True);sentinel.write_text('preserve user pack')
            preferences=appdata/'preferences.json';preferences.write_text('{"favorite_voices":["am_michael","bf_emma"]}')
            install(installer)
            assert sentinel.read_text()=='preserve user pack'
            assert json.loads(preferences.read_text())['favorite_voices']==['am_michael','bf_emma']
        else:install(installer)
        state=registry()
        assert state['DisplayVersion']==target_version and state['DisplayName']=='SRT Voice Studio',state
        assert Path(state['InstallLocation']).resolve()==dest.resolve(),state
        assert exe.exists() and len(list(dest.glob('unins*.exe')))==1
        env=os.environ.copy();env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
        env['PYTHONHOME']=r'C:\nonexistent-python';env['PYTHONPATH']=r'C:\nonexistent-python-packages'
        env['TEMP']=str(dest/'missing-system-temp');env['TMP']=env['TEMP'];env['HF_HUB_OFFLINE']='1';env['TRANSFORMERS_OFFLINE']='1'
        env['SRTVS_UNICODE_TEST_DIR']=r'D:\LỒNG TIẾNG\Test App'
        programs=[exe,dest/'_internal'/'bin'/'ffmpeg.exe',dest/'_internal'/'bin'/'ffprobe.exe']
        if scenario=='upgrade':
            subprocess.run([str(exe),'--install-voice-test'],env=env,check=True,timeout=1800)
            voice_install=read_report('install-voice-test.json');assert voice_install.get('complete') is True,voice_install
            marker=appdata/'VoicePacks/aivis-runtime/1.2.0/ready.json';programs.append(Path(json.loads(marker.read_text())['engine']))
        for i,program in enumerate(programs):
            name=rule+str(i)
            subprocess.run(['netsh','advfirewall','firewall','add','rule',f'name={name}','dir=out','action=block',f'program={program}','enable=yes'],check=True)
            blocked.append(name)
        subprocess.run([str(exe),'--self-test'],env=env,check=True,timeout=1200)
        data=read_report('self-test.json');assert data.get('all_british_voices',{}).get('count')==8,data.get('all_british_voices')
        subprocess.run([str(exe),'--ui-smoke'],env=env,check=True,timeout=240);data['ui']=read_report('ui-test.json')
        if scenario=='upgrade':
            subprocess.run([str(exe),'--optional-voices-test'],env=env,check=True,timeout=1800)
            data['optional-voices']=read_report('optional-voices-test.json')
            assert len(data['optional-voices'].get('voices',{}))==11,data['optional-voices']
            subprocess.run([str(exe),'--stress-test'],env=env,check=True,timeout=2400);data['real_74_caption_stress']=read_report('stress-test.json')
            subprocess.run([str(exe),'--underfill-test'],env=env,check=True,timeout=900);data['real_30_caption_underfill']=read_report('underfill-test.json')
            for check in ('underfill-v2','batch','voice-benchmark'):
                subprocess.run([str(exe),'--'+check+'-test'],env=env,check=True,timeout=1800);data[check]=read_report(check+'-test.json')
            assert data['voice-benchmark']['voices']>=39,data['voice-benchmark']
        assert not list((appdata/'Temp').glob('job-*')),'Temporary audio remains: '+repr([str(p) for p in (appdata/'Temp').glob('job-*')])
        data['registry']=state;results['scenarios'][scenario]=data
    finally:
        for name in ('self-test.json','ui-test.json','logs/latest.log'):
            log=appdata/name
            if log.exists():print(log.read_text('utf-8',errors='replace')[-18000:],flush=True)
        for name in blocked:subprocess.run(['netsh','advfirewall','firewall','delete','rule',f'name={name}'],check=False)
        if (dest/'unins000.exe').exists():subprocess.run([str(dest/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=240)
    assert not exe.exists(),'Uninstall did not remove app executable'
    try:registry()
    except FileNotFoundError:pass
    else:raise RuntimeError('Uninstall registry entry remains')
    results['scenarios'][scenario]['uninstall']='OK'
results['passed']=True
(root/'installer-output'/'acceptance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
