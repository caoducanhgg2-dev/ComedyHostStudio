import threading
from pathlib import Path
from dataclasses import replace
import pytest
from studio.batch import BatchQueue, DONE, FAILED, CANCELLED, WAITING
from studio.render import Settings
from studio.audio import Cancelled
from test_timeline import FakeBackend, make_srt

@pytest.mark.parametrize('count',[1,5,20])
def test_sequential_real_pcm_mixed_unicode(tmp_path,monkeypatch,count):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'data'))
    q=BatchQueue()
    for i in range(count):
        folder=tmp_path/('Tên thư mục 日本語 '+str(i))
        folder.mkdir()
        p=folder/'phụ đề 日本語.srt'
        p.write_text(make_srt(1,start=5000),encoding='utf-8-sig')
        q.add([p],Settings(language='Japanese' if i%2 else 'English US',voice='jf_alpha' if i%2 else 'af_heart'))
    output=tmp_path/'MP3'
    result=q.run(FakeBackend(.5),output)
    assert result[DONE]==count and len(list(output.glob('*.mp3')))==count
    assert len({i.output.casefold() for i in q.items})==count
    assert all(i.report['overlaps']==0 and i.report['records'][0]['start_sample']==5000*48 for i in q.items)
    assert not list(output.glob('*.wav'))

def test_failure_continues_and_can_retry(tmp_path):
    paths=[tmp_path/f'{i}.srt' for i in range(5)]
    for p in paths:p.write_text(make_srt(1),encoding='utf-8')
    paths[2].write_text('bad srt')
    q=BatchQueue();q.add(paths,Settings())
    def renderer(source,output,settings,backend,cancel,progress):
        from studio.timeline import read_srt
        read_srt(source);Path(output).write_bytes(b'test');return {}
    result=q.run(None,tmp_path/'out',renderer=renderer)
    assert result[DONE]==4 and result[FAILED]==1 and q.items[2].error
    paths[2].write_text(make_srt(1));q.retry()
    assert q.run(None,tmp_path/'out',renderer=renderer)[DONE]==5
    assert len(list((tmp_path/'out').glob('*.mp3')))==5

def test_cancel_single_continues_cancel_all_stops(tmp_path):
    q=BatchQueue()
    paths=[tmp_path/f'{i}.srt' for i in range(5)]
    for p in paths:p.write_text(make_srt(1))
    q.add(paths,Settings())
    visited=[]
    def renderer(source,output,settings,backend,cancel,progress):
        visited.append(source.name)
        if source.name=='1.srt':
            q.cancel_item(q.current_id);assert cancel.is_set();raise Cancelled()
        if source.name=='3.srt':
            q.cancel_all();assert cancel.is_set();raise Cancelled()
        Path(output).write_bytes(b'test');return {}
    result=q.run(None,tmp_path/'out',renderer=renderer)
    assert visited==['0.srt','1.srt','2.srt','3.srt']
    assert result[DONE]==2 and result[CANCELLED]==3
    q.retry();assert sum(i.state==WAITING for i in q.items)==3

def test_common_and_per_file_settings_are_snapshots(tmp_path):
    q=BatchQueue()
    for n in ('a','b'):
        p=tmp_path/(n+'.srt');p.write_text(make_srt(1));q.add([p],Settings())
    q.items[1].settings=replace(q.items[1].settings,emotion='Happy')
    seen=[]
    def renderer(source,output,settings,*args):seen.append(settings);return {}
    q.run(None,tmp_path/'out',renderer=renderer)
    assert [s.emotion for s in seen]==['Natural','Happy']
    for i in q.items:i.state=WAITING
    shared=Settings(voice='am_michael');q.run(None,tmp_path/'out',shared,renderer=renderer)
    assert all(s.voice=='am_michael' for s in seen[-2:])
