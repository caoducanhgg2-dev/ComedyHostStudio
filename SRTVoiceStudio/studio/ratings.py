"""Import explicit listening scores; technical checks never manufacture ratings."""
import csv
import math
from datetime import datetime, timezone

WEIGHTS = dict(naturalness=35, pronunciation=25, expression=15,
               speed_fit=10, audio_quality=10, popularity=5)


def score(record):
    try:
        if not record.get('reviewer') or record.get('method') != 'user_listening':
            return None
        values = {key: float(record['scores'][key]) for key in WEIGHTS}
        if not all(math.isfinite(value) and 0 <= value <= 10 for value in values.values()):
            return None
        return sum(values[key] * weight for key, weight in WEIGHTS.items()) / 100
    except (TypeError, KeyError, ValueError, AttributeError):
        return None


def read_csv(path, known_voices):
    result = {}; seen = set()
    with open(path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'voice', 'reviewer', *WEIGHTS}.issubset(reader.fieldnames or []):
            raise ValueError('Thiếu cột điểm nghe trong CSV.')
        for row in reader:
            voice = str(row.get('voice') or '').strip()
            if voice not in known_voices:
                raise ValueError('CSV có mã giọng chưa được cài: ' + voice)
            if voice in seen:
                raise ValueError('CSV có mã giọng trùng: ' + voice)
            seen.add(voice)
            if all(not str(row.get(key) or '').strip() for key in WEIGHTS):
                continue
            record = dict(scores={key: row.get(key) for key in WEIGHTS},
                          reviewer=str(row.get('reviewer') or '').strip(),
                          notes=str(row.get('notes') or ''), method='user_listening',
                          date=datetime.now(timezone.utc).isoformat())
            if score(record) is None:
                raise ValueError('Điền đủ sáu điểm từ 0 đến 10 và người chấm cho ' + voice)
            record['scores'] = {key: float(record['scores'][key]) for key in WEIGHTS}
            result[voice] = record
    return result
