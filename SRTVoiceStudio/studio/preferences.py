"""Version-tolerant user preferences outside the installation directory."""
import json
import os
import tempfile
from dataclasses import asdict, fields
from .paths import data_dir
from .render import Settings

def read():
    try:
        value=json.loads((data_dir()/'preferences.json').read_text('utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}

def write(value):
    folder=data_dir()
    fd,name=tempfile.mkstemp(prefix='preferences-',suffix='.tmp',dir=folder)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(name,folder/'preferences.json')
    finally:
        if os.path.exists(name):os.unlink(name)

def save_settings(settings):
    value=read();value['settings']=asdict(settings);write(value)

def load_settings():
    source=read().get('settings',{})
    if not isinstance(source,dict):return Settings()
    allowed={f.name for f in fields(Settings)}
    try:return Settings(**{k:v for k,v in source.items() if k in allowed})
    except (TypeError,ValueError):return Settings()
