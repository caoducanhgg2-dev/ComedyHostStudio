"""Integer sample timeline. No floating point timestamp accumulation."""
from dataclasses import dataclass
import re
from pathlib import Path

RATE = 48000

class TimelineError(ValueError):
    pass

@dataclass(frozen=True)
class Caption:
    index: int
    start: int
    end: int
    text: str

@dataclass(frozen=True)
class Slot:
    caption: Caption
    start: int
    end: int

def stamp(value):
    match = re.fullmatch(r'(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})', value)
    if not match:
        raise TimelineError(f'Timestamp không hợp lệ: {value}')
    h, m, s, ms = map(int, match.groups())
    return ((h * 60 + m) * 60 + s) * 1000 + ms

def parse(text):
    blocks = re.split(r'\n[ \t]*\n', text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip())
    captions, seen = [], set()
    for pos, block in enumerate(blocks, 1):
        lines = block.strip().splitlines()
        label = lines[0] if lines else str(pos)
        try:
            if len(lines) < 3 or not lines[0].strip().isdigit():
                raise TimelineError('Cần số thứ tự, timestamp và nội dung.')
            index = int(lines[0])
            if index < 1 or index in seen:
                raise TimelineError('Số thứ tự trùng hoặc không hợp lệ.')
            parts = re.split(r'\s*-->\s*', lines[1].strip())
            if len(parts) != 2:
                raise TimelineError('Thiếu dấu --> hoặc sai timestamp.')
            start, end = map(stamp, parts)
            body = ' '.join(x.strip() for x in lines[2:]).strip()
            if not body or end <= start:
                raise TimelineError('Nội dung rỗng hoặc END không lớn hơn START.')
            if '-->' in body:
                raise TimelineError('Thiếu dòng trống giữa các caption.')
            if captions and start <= captions[-1].start:
                raise TimelineError('START phải tăng nghiêm ngặt; không tự sắp xếp SRT.')
            captions.append(Caption(index, start, end, body))
            seen.add(index)
        except ValueError as exc:
            raise TimelineError(f'CAPTION {label} (khối {pos}): {exc}') from exc
    return captions

def read_srt(path):
    try:
        return parse(Path(path).read_text(encoding='utf-8-sig'))
    except UnicodeError as exc:
        raise TimelineError('SRT phải lưu bằng UTF-8 hoặc UTF-8 BOM.') from exc

def slots_for(captions, gap_ms=100):
    if gap_ms not in (0, 50, 100, 150, 200):
        raise TimelineError('Minimum Gap không hợp lệ.')
    if not captions:
        raise TimelineError('SRT rỗng.')
    slots = []
    for i, c in enumerate(captions):
        end = min(c.end, captions[i+1].start - gap_ms) if i+1 < len(captions) else c.end
        if end <= c.start:
            raise TimelineError(f'CAPTION {c.index}: không còn slot sau khi trừ gap {gap_ms} ms. Hãy sửa SRT hoặc giảm gap.')
        slots.append(Slot(c, c.start * 48, end * 48))
    return slots

def validate(slots, lengths, gap_ms):
    if len(slots) != len(lengths):
        raise TimelineError('Thiếu caption audio.')
    overlaps = 0
    for i, (slot, n) in enumerate(zip(slots, lengths)):
        if n <= 0 or slot.start + n > slot.end:
            raise TimelineError(f'CAPTION {slot.caption.index}: audio ngoài slot.')
        if i+1 < len(slots) and slot.start + n + gap_ms * 48 > slots[i+1].start:
            overlaps += 1
    if overlaps:
        raise TimelineError(f'Không export: {overlaps} overlaps.')
    return {'total': len(slots), 'valid': len(slots), 'overlaps': overlaps}

def display_time(ms):
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
