"""Real bundled DSP and shared preview acceptance, also used by Help diagnostics."""
from dataclasses import replace
import tempfile
from pathlib import Path
import numpy as np
from .effects import EffectProcessor, EMOTIONS, EFFECTS, LEVELS
from .preview import PreviewCache
from .render import Settings
from .timeline import Caption, slots_for, RATE
from .paths import workspace
from .fitting import fit_processed

def style_checks(backend,cancel,progress):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as folder:
        folder=Path(folder);processor=EffectProcessor(folder,cancel)
        filters=processor.validate_filters(cancel)
        checks.append('FFmpeg filters: OK ('+', '.join(filters)+')')
        cache=PreviewCache();settings=Settings();text='What is that? This is a voice test.'
        slot=slots_for([Caption(1,5000,5700,text)])[0]
        original=cache.get('A',text,settings,backend,cancel,slot,progress)
        checks.append('Preview A: OK')
        clean=cache.get('B',text,settings,backend,cancel,slot,progress)
        assert np.array_equal(original.samples,clean.samples)
        checks.append('Natural / None reference: OK')
        for emotion in EMOTIONS:
            for intensity in LEVELS:
                b,tempo=processor.apply_emotion(original.samples,original.rate,emotion,intensity)
                assert len(b)>0 and np.isfinite(b).all() and .9<=tempo<=1.2
                if emotion!='Natural':
                    assert len(b)!=len(original.samples) or not np.allclose(b,original.samples,atol=1e-5)
        checks.append('Emotion Processor: OK (12 presets x 3 intensities)')
        for effect in EFFECTS:
            for strength in LEVELS:
                b=processor.apply_effect(original.samples,original.rate,effect,strength)
                assert len(b)>0 and np.isfinite(b).all() and np.max(np.abs(b))<=1
                if effect!='None':
                    assert len(b)!=len(original.samples) or not np.allclose(b,original.samples,atol=1e-5)
        checks.append('Voice FX Processor: OK (16 choices x 3 strengths)')
        styled=replace(settings,emotion='Happy',effect='Radio')
        b=cache.get('B',text,styled,backend,cancel,slot,progress)
        c=cache.get('C',text,styled,backend,cancel,slot,progress)
        expected,record=fit_processed(b.samples,b.rate,slot,styled,cache.emotion_tempo,folder,cancel)
        assert np.array_equal(c.samples,expected)
        assert np.array_equal(cache.base,original.samples)
        assert c.details['overlaps']==0 and c.details['speed']<=1.2
        checks.extend(['Preview B: OK (same immutable A)','Timeline Preview C: OK (production fit)'])
        # The deliberately short slot exercises tail truncation after DSP.
        for effect in ('Reverb','Echo','Cave'):
            s=replace(settings,effect=effect,strength='Strong')
            b=cache.get('B',text,s,backend,cancel,slot,progress)
            c=cache.get('C',text,s,backend,cancel,slot,progress)
            assert len(b.samples)>len(original.samples)
            assert c.details['trimmed'] and c.details['end_sample']<=slot.end
            assert c.samples[-1]==0 and c.details['overlaps']==0
            checks.append(effect+' Tail Guard: OK')
        underfill_slot=slots_for([Caption(1,5000,15000,text)])[0]
        c=cache.get('C',text,settings,backend,cancel,underfill_slot,progress)
        assert c.details['speed']==.88 and c.details['underfilled'] and c.details['overlaps']==0
        checks.append('Underfill Fit: OK')
        cache.clear()
    return checks
