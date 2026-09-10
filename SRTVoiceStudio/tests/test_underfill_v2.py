from pathlib import Path
import threading
from studio.underfill_v2_checks import run_comparison
from test_styles import CountingBackend


def test_real_46_caption_srt_structure_with_controlled_pcm(tmp_path,monkeypatch):
    # Actual user SRT + synthetic PCM tests timing only, not Kokoro quality.
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'data'))
    source=Path(__file__).parents[1]/'samples/EN7_American_Comedy_Review.srt'
    result=run_comparison(CountingBackend(3.6),threading.Event(),source,tmp_path/'result')
    assert result['captions']==46 and result['start_times_unchanged'] and result['overlaps']==0
    assert result['same_cached_tts'] and result['target_reached']
    assert result['average_reduction_seconds']>.025
    assert result['final']['transitions_over_08']==0
    assert len(list((tmp_path/'result').glob('*.mp3')))==1
