import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import threading
from studio.effects import EffectProcessor
filters=EffectProcessor.validate_filters(threading.Event())
Path('filter-validation.json').write_text(json.dumps({'passed':True,'filters':filters},indent=2),encoding='utf-8')
print('Verified bundled filters:',', '.join(filters))
