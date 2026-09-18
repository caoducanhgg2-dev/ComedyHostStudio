import threading
from pathlib import Path
import numpy as np
import pytest
from studio.timeline import parse, slots_for, validate, TimelineError, AUTO_GAP_MS
from studio.render import render, Settings
from studio.audio import Cancelled, run
from studio.paths import executable

def ts(ms):
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def make_srt(n=10, start=0, spacing=2000, text="That's a test."):
    return '\n\n'.join(f'{i+1}\n{ts(start+i*spacing)} --> {ts(start+(i+1)*spacing)}\n{text}' for i in range(n))

class FakeBackend:
    def __init__(self, duration=1.0):
        self.duration = duration
    def synthesize(self, *args):
        t = np.arange(round(self.duration*24000))/24000
        return (0.2*np.sin(2*np.pi*440*t)).astype(np.float32),24000

@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'appdata'))
    return tmp_path/'LỒNG TIẾNG'/'Test App'

def test_bom_japanese_multiline():
    c = parse('\ufeff1\r\n00:00:00,000 --> 00:00:02,100\r\nこれは\r\nテストです。\r\n')[0]
    assert c.text == 'これは テストです。' and c.end == 2100

@pytest.mark.parametrize('text', [
    '', '1\n00:00:01,000 --> 00:00:00,000\nHello',
    '1\n00:60:00,000 --> 00:00:01,000\nHello',
    '1\n00:00:00,000 --> 00:00:01,000\nHello\n2\n00:00:01,000 --> 00:00:02,000\nWorld',
    'x\n00:00:00,000 --> 00:00:01,000\nHello',
    make_srt(2).replace('2\n','1\n'),
    make_srt(2).replace('00:00:02,000 -->','00:00:00,000 -->'),
])
def test_bad_srt(text):
    with pytest.raises(TimelineError,match='CAPTION'):
        parse(text)

def test_impossible_gap():
    with pytest.raises(TimelineError,match='CAPTION 1'):
        slots_for(parse(make_srt(2,spacing=50)),100)

def test_overlapping_srt_shrinks_slot():
    c = parse('1\n00:00:00,000 --> 00:00:05,000\nA\n\n2\n00:00:02,000 --> 00:00:04,000\nB')
    slots = slots_for(c,100)
    assert slots[0].end == 1900*48
    validate(slots,[1900*48,2000*48],100)

def test_adaptive_timeline_reuses_existing_100ms_gap_without_overlap():
    c = parse('1\n00:00:00,000 --> 00:00:01,000\nA\n\n2\n00:00:01,100 --> 00:00:02,500\nB')
    slots = slots_for(c)
    assert slots[0].end == 1070*48
    report = validate(slots,[1050*48,1000*48],AUTO_GAP_MS)
    assert report['overlaps'] == 0 and report['adaptive_timeline']


def test_adaptive_timeline_extends_past_original_end_but_never_next_start():
    c = parse('1\n00:00:00,000 --> 00:00:02,000\nA\n\n2\n00:00:02,100 --> 00:00:04,000\nB')
    auto = slots_for(c)
    fixed = slots_for(c,100)
    assert fixed[0].end == 2000*48
    assert auto[0].end == 2070*48
    assert auto[0].end < auto[1].start


def test_adaptive_guard_shrinks_on_tight_start_spacing():
    c = [Caption(1,0,40,'A'), Caption(2,50,100,'B')]
    slots = slots_for(c)
    # 10% of the 50 ms start spacing = 5 ms safety.
    assert slots[0].end == 45*48
    assert slots[0].end < slots[1].start


def test_validator_rejects_boundary_violation():
    slots = slots_for(parse(make_srt(2)))
    with pytest.raises(TimelineError):
        validate(slots,[2*48000,48000],100)

@pytest.mark.parametrize('count', [10,74])
def test_full_render_unicode_first_silence(home,count):
    home.mkdir(parents=True)
    source = home/'字幕 日本語.srt'
    source.write_text(make_srt(count,start=5000),encoding='utf-8-sig')
    output = home/'字幕 日本語_Voice.mp3'
    report = render(source,output,Settings(),FakeBackend(),threading.Event())
    assert report['overlaps']==0 and report['valid']==count
    decoded=home/'check.raw'
    run([executable('ffmpeg'),'-nostdin','-v','error','-y','-i',str(output),'-f','f32le',
         '-ar','48000','-ac','1',str(decoded)],threading.Event())
    a=np.fromfile(decoded,dtype='<f4')
    assert abs(len(a)/48000-(5+count*2))<0.05
    assert np.max(np.abs(a[:int(4.97*48000)]))<0.001
    for record in report['records']:
        assert record['end_sample'] <= record['allowed_end']
    from studio.paths import workspace
    assert not list(workspace().glob('job-*'))
    assert not list(home.glob('.srtvs-*'))
    assert source.exists()

@pytest.mark.parametrize('duration,trimmed', [(2.10,False),(3.5,True)])
def test_overflow_and_speed(home,duration,trimmed):
    home.mkdir(parents=True)
    srt=home/'test.srt';srt.write_text(make_srt(1),encoding='utf-8')
    r=render(srt,home/'out.mp3',Settings(),FakeBackend(duration),threading.Event())
    assert r['overlaps']==0 and r['records'][0]['speed']<=1.2
    assert r['speed_adjusted']==1
    assert bool(r['safely_trimmed']) is trimmed

def test_stop_preserves_existing_file(home):
    home.mkdir(parents=True)
    srt=home/'test.srt';srt.write_text(make_srt(1),encoding='utf-8')
    output=home/'out.mp3';output.write_bytes(b'old output')
    with pytest.raises(TimelineError,match='CAPTION 1 TOO LONG'):
        render(srt,output,Settings(overflow='Stop and Report'),FakeBackend(5),threading.Event())
    assert output.read_bytes()==b'old output'

def test_cancel_no_output(home):
    home.mkdir(parents=True)
    srt=home/'test.srt';srt.write_text(make_srt(1),encoding='utf-8')
    event=threading.Event();event.set()
    with pytest.raises(Cancelled):
        render(srt,home/'out.mp3',Settings(),FakeBackend(),event)
    assert not (home/'out.mp3').exists()

def test_japanese_phonemes():
    from misaki.cutlet import Cutlet
    phonemes,_=Cutlet()('これは日本語の音声です。')
    assert any(c in phonemes for c in 'ɯɨɾɲʔ') and not any('\u3040'<=c<='\u9fff' for c in phonemes)
