"""Portable packaging checks; actual rollback execution is a Windows CI gate."""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_delta_contains_recovery_tools_and_preserves_uninstaller(tmp_path):
    old, new, output = [tmp_path / name for name in ('old','new','out')]
    old.mkdir(); new.mkdir()
    for folder in (old,new):
        (folder/'shared-model.bin').write_bytes(b'unchanged model'*100)
    (old/'SRTVoiceStudio.exe').write_bytes(b'old exe')
    (new/'SRTVoiceStudio.exe').write_bytes(b'new exe')
    (old/'unins000.exe').write_bytes(b'original uninstaller')
    (old/'obsolete.dll').write_bytes(b'old library')
    (new/'new.dll').write_bytes(b'new library')
    result = subprocess.run([sys.executable,str(ROOT/'build_tools/build_update_zip.py'),
        '--baseline',str(old),'--current',str(new),'--output-dir',str(output),
        '--from-version','1.3.0','--to-version','1.4.0','--baseline-commit','test-fixture'],
        capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(next(output.glob('*.zip'))) as package:
        manifest=json.loads(package.read('update_manifest.json'))
        assert manifest['format']==4 and manifest['persistent_rollback']
        assert manifest['health_check']=='--update-health-check'
        assert {e['path'] for e in manifest['delete']}=={'obsolete.dll'}
        assert {e['path'] for e in manifest['files']}=={'SRTVoiceStudio.exe','new.dll'}
        assert 'payload/shared-model.bin' not in package.namelist()
        assert {'Apply_Update.cmd','Apply_Update.ps1','Restore_Previous.cmd',
                'Restore_Previous.ps1','Update_Common.ps1'} <= set(package.namelist())
        for entry in manifest['files']:
            assert hashlib.sha256(package.read('payload/'+entry['path'])).hexdigest()==entry['sha256']


def test_refuses_full_app_disguised_as_delta(tmp_path):
    old,new = tmp_path/'old',tmp_path/'new'
    old.mkdir();new.mkdir()
    (old/'SRTVoiceStudio.exe').write_bytes(b'old')
    (new/'SRTVoiceStudio.exe').write_bytes(b'new')
    result=subprocess.run([sys.executable,str(ROOT/'build_tools/build_update_zip.py'),
        '--baseline',str(old),'--current',str(new),'--output-dir',str(tmp_path/'out'),
        '--from-version','1.3.0','--to-version','1.4.0','--baseline-commit','test-fixture'],
        capture_output=True,text=True)
    assert result.returncode!=0 and 'not a delta' in result.stderr


def test_known_alternate_hash_is_kept_even_when_primary_matches_target(tmp_path):
    old,new = tmp_path/'old',tmp_path/'new'
    old.mkdir();new.mkdir()
    for folder in (old,new):
        (folder/'SRTVoiceStudio.exe').write_bytes(b'same primary executable')
        (folder/'model.bin').write_bytes(b'shared model'*100)
    (old/'notes.txt').write_text('old')
    (new/'notes.txt').write_text('new')
    alternate=tmp_path/'alternate.json'
    alternate_hash=hashlib.sha256(b'alternate released executable').hexdigest()
    alternate.write_text(json.dumps({'version':'1.3.1','name':'known-alternate',
        'file_hashes':{'SRTVoiceStudio.exe':alternate_hash}}))
    result=subprocess.run([sys.executable,str(ROOT/'build_tools/build_update_zip.py'),
        '--baseline',str(old),'--current',str(new),'--output-dir',str(tmp_path/'out'),
        '--from-version','1.3.1','--to-version','1.4.0','--baseline-commit','test-fixture',
        '--alternate-baseline-manifest',str(alternate)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    manifest=json.loads((tmp_path/'out/update_manifest.json').read_text())
    exe=next(e for e in manifest['files'] if e['path']=='SRTVoiceStudio.exe')
    assert exe['sha256']==exe['old_sha256']
    assert alternate_hash in exe['old_sha256_variants']
    assert len(manifest['baseline_variants'])==2
