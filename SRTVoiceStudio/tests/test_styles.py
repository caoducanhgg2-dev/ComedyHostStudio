from dataclasses import replace
import threading
from pathlib import Path
import numpy as np
import pytest
from studio.effects import EffectProcessor, EMOTIONS, EFFECTS, LEVELS, auto_emotion
from studio.preview import PreviewCache
from studio.render import Settings, render
from studio.fitting import fit_processed
from studio.timeline import Caption, slots_for, RATE, TimelineError
from studio.audio import run, Cancelled
from studio.paths import executable, workspace
from test_timeline import FakeBackend, make_srt

@pytest.fixture
def ctx(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'appdata'))
    return tmp_path,threading.Event()

def tone(duration=1.0):
    t=np.arange(round(duration*24000))/24000
    # Harmonics and envelope exercise EQ and dynamics beyond a single sine.
    return ((.18*np.sin(2*np.pi*190*t)+.08*np.sin(2*np.pi*1700*t)+.025*np.sin(2*np.pi*3900*t))
            *(.7+.3*np.sin(2*np.pi*2*t))).astype('float32')

def test_bundled_filters(ctx):
    assert len(EffectProcessor.validate_filters(ctx[1]))==11

@pytest.mark.parametrize('effect',list(EFFECTS))
def test_effect_strengths_real_dsp(ctx,effect):
    folder,cancel=ctx;p=EffectProcessor(folder,cancel);a=tone();original=a.copy()
    results=[]
    for level in LEVELS:
        b=p.apply_effect(a,24000,effect,level)
        assert np.isfinite(b).all() and np.max(np.abs(b)) <= .951 and np.max(np.abs(b)) > .005
        assert np.array_equal(a,original)
        results.append(b)
        if effect=='None':
            assert np.array_equal(a,b)
        else:
            assert len(a)!=len(b) or np.sqrt(np.mean((a-b)**2)) > .0001
    if effect!='None':
        assert len(results[0])!=len(results[2]) or not np.allclose(results[0],results[2],atol=1e-5)
    if effect in ('Deep Voice','Bright Voice'):
        assert all(len(b)==len(a) for b in results)

@pytest.mark.parametrize('emotion',list(EMOTIONS))
def test_emotion_dsp_and_intensity(ctx,emotion):
    folder,cancel=ctx;p=EffectProcessor(folder,cancel);a=tone();original=a.copy();results=[]
    for intensity in LEVELS:
        b,t=p.apply_emotion(a,24000,emotion,intensity)
        assert .9 <= t <= 1.2 and np.isfinite(b).all()
        assert np.array_equal(a,original)
        if emotion=='Natural':
            assert np.array_equal(a,b) and t==1
        else:
            assert len(a)!=len(b) or not np.allclose(a,b,atol=1e-5)
        results.append(b)
    if emotion!='Natural':
        assert len(results[0])!=len(results[2]) or not np.allclose(results[0],results[2],atol=1e-5)

@pytest.mark.parametrize('text,language,emotion',[
    ('What is THAT?!','English US','Surprised'),
    ('No way this actually worked.','English US','Surprised'),
    ('Everything finally went quiet.','English US','Calm'),
    ('And then everything went wrong.','English US','Dramatic'),
    ('これは本当に大丈夫なのか？','Japanese','Surprised'),
    ('ついに完成しました。','Japanese','Happy'),
    ('何をしてるんだよ！','Japanese','Surprised'),
    ('静かな夜です。','Japanese','Calm'),
    ('ふざけるな！','Japanese','Angry'),
])
def test_auto_rules(text,language,emotion):
    assert auto_emotion(text,language)[0]==emotion

class CountingBackend(FakeBackend):
    def __init__(self,duration=1):
        super().__init__(duration);self.count=0
    def synthesize(self,*args):
        self.count+=1
        return tone(self.duration),24000

def test_preview_cache_original_shared_fit(ctx):
    folder,cancel=ctx;b=CountingBackend(2);cache=PreviewCache();s=Settings(voice='am_michael')
    slot=slots_for([Caption(17,5000,5500,'sample')])[0]
    a=cache.get('A','sample',s,b,cancel,slot)
    clean=cache.get('B','sample',s,b,cancel,slot)
    assert np.array_equal(clean.samples,a.samples)
    for options in [dict(emotion='Funny / Playful'),dict(emotion='Serious'),dict(effect='Radio'),
                    dict(effect='Cave'),dict(effect='Cave',strength='Strong')]:
        styled=replace(s,**options)
        processed=cache.get('B','sample',styled,b,cancel,slot)
        final=cache.get('C','sample',styled,b,cancel,slot)
        expected,record=fit_processed(processed.samples,processed.rate,slot,styled,
                                     cache.emotion_tempo,folder,cancel)
        assert np.array_equal(final.samples,expected)
        assert final.details['speed']<=1.2 and final.details['overlaps']==0
        assert final.samples[-1]==0
        assert np.array_equal(cache.base,a.samples)
        assert b.count==1
    cache.get('A','new text',s,b,cancel)
    assert b.count==2
    cache.get('A','new text',replace(s,voice='af_heart'),b,cancel)
    assert b.count==3
    assert not list(workspace().glob('job-*'))

@pytest.mark.parametrize('language,text,voice',[
    ('English US','What is THAT?!','am_michael'),('Japanese','何をしてるんだよ！','jm_kumo')])
def test_74_auto_cave_one_mp3(ctx,language,text,voice):
    folder,cancel=ctx
    source=folder/'日本語 テスト.srt';source.write_text(make_srt(74,start=5000,text=text),encoding='utf-8-sig')
    output=folder/'日本語 テスト_Voice.mp3'
    settings=Settings(language=language,voice=voice,emotion_mode='Auto',effect='Cave',strength='Strong')
    report=render(source,output,settings,CountingBackend(2.5),cancel)
    assert report['valid']==74 and report['overlaps']==0 and report['duration_ms']==153000
    assert report['safely_trimmed']==74
    for i,r in enumerate(report['records']):
        assert r['start_sample']==(5000+i*2000)*48
        assert r['end_sample']<=r['allowed_end'] and r['speed']<=1.2
        if i<73: assert r['end_sample']+30*48<=report['records'][i+1]['start_sample']
    assert list(folder.glob('*.mp3'))==[output]
    assert not list(folder.glob('*.wav')) and not list(folder.glob('.srtvs-*'))
    assert not list(workspace().glob('job-*'))
    decode=folder/'decode.raw'
    run([executable('ffmpeg'),'-nostdin','-v','error','-y','-i',str(output),'-f','f32le',str(decode)],cancel)
    audio=np.fromfile(decode,dtype='<f4')
    assert abs(len(audio)/RATE-153)<.05
    assert np.max(np.abs(audio[:round(4.97*RATE)]))<.001

def test_echo_tail_gap_and_stop(ctx):
    folder,cancel=ctx
    source=folder/'echo.srt'
    source.write_text('1\n00:00:00,000 --> 00:00:04,000\nFirst\n\n2\n00:00:04,100 --> 00:00:08,000\nSecond',encoding='utf-8')
    output=folder/'out.mp3';s=Settings(effect='Echo',strength='Strong',emotion='Excited',intensity='Strong',speed=1.2)
    report=render(source,output,s,CountingBackend(5),cancel)
    first,second=report['records']
    assert first['processed_seconds']>4 and first['trimmed']
    assert first['speed']<=1.2 and first['end_sample']<=round(4.07*RATE)
    assert first['allowed_end']==round(4.07*RATE)
    assert second['start_sample']==round(4.1*RATE)
    old=output.read_bytes()
    with pytest.raises(TimelineError,match='CAPTION 1 TOO LONG'):
        render(source,output,replace(s,overflow='Stop and Report'),CountingBackend(5),cancel)
    assert output.read_bytes()==old
    assert not list(workspace().glob('job-*')) and not list(folder.glob('.srtvs-*'))

def test_first_silence_dramatic_cave(ctx):
    folder,cancel=ctx;srt=folder/'test.srt';srt.write_text(make_srt(1,start=5000),encoding='utf-8')
    output=folder/'test.mp3'
    report=render(srt,output,Settings(emotion='Dramatic',effect='Cave'),CountingBackend(),cancel)
    assert report['records'][0]['start_sample']==5*RATE
    raw=folder/'decoded.raw'
    run([executable('ffmpeg'),'-nostdin','-v','error','-y','-i',str(output),'-f','f32le',str(raw)],cancel)
    a=np.fromfile(raw,dtype='<f4');assert np.max(np.abs(a[:round(4.97*RATE)]))<.001

def test_cancel_effect_cleans_internal_files(ctx):
    folder,cancel=ctx;cancel.set()
    with pytest.raises(Cancelled):
        EffectProcessor(folder,cancel).apply_effect(tone(),24000,'Echo','Strong')
    assert not list(folder.glob('effect-*.raw'))
