"""Single-entry A/B/C cache; original samples are immutable and never resynthesized for style."""
from dataclasses import dataclass
import logging
import tempfile
from pathlib import Path
import numpy as np
from .audio import check_cancel
from .paths import workspace
from .effects import EffectProcessor, selected_emotion
from .fitting import fit_processed
from .continuity import trim_edge_silence
from .timeline import RATE
from .voice_backends import synthesize_selected

@dataclass
class PreviewResult:
    stage: str
    samples: np.ndarray
    rate: int
    details: dict

class PreviewCache:
    def __init__(self):
        self.clear()

    def clear(self):
        self.key = None
        self.base = self.processed = self.final = None
        self.style_key = self.fit_key = None
        self.rate = None
        self.details = {}
        self.continuity_trim = (0.0, 0.0)

    def get(self, stage, text, settings, backend, cancel, slot=None, progress=lambda _: None):
        if stage not in ('A','B','C') or not text.strip():
            raise ValueError('Preview không hợp lệ.')
        if stage == 'C' and (slot is None or text != slot.caption.text):
            raise ValueError('Chọn caption SRT để nghe Final Timeline.')
        check_cancel(cancel)
        key = (settings.language,settings.voice,settings.native_style,text,
               bool(getattr(settings,'continuous',False)))
        if key != self.key:
            self.clear()
            samples,rate = synthesize_selected(backend,text,settings,cancel,progress)
            original = np.asarray(samples,dtype=np.float32).reshape(-1).copy()
            if not len(original) or not np.isfinite(original).all() or not np.any(np.abs(original)>1e-7):
                raise RuntimeError('TTS trả về audio rỗng hoặc không hợp lệ.')
            original,lead,tail = trim_edge_silence(original,rate,bool(getattr(settings,'continuous',False)))
            if not len(original) or not np.isfinite(original).all() or not np.any(np.abs(original)>1e-7):
                raise RuntimeError('Continuous Voice tạo preview không hợp lệ.')
            original.setflags(write=False)
            self.base,self.rate,self.key = original,rate,key
            self.continuity_trim=(lead,tail)
        emotion,intensity = selected_emotion(settings,text)
        style_key = (emotion,intensity,settings.effect,settings.strength)
        if style_key != self.style_key:
            self.processed=self.final=None
            self.fit_key=None
            self.details={}
        with tempfile.TemporaryDirectory(prefix='job-',dir=workspace()) as folder:
            if stage != 'A' and self.processed is None:
                processor=EffectProcessor(Path(folder),cancel)
                b,tempo,emotion,intensity=processor.process(self.base.copy(),self.rate,settings,text)
                b.setflags(write=False)
                self.processed,self.emotion_tempo,self.style_key=b,tempo,style_key
            fit_key = (slot,settings.speed,settings.gap_ms,settings.adaptive,settings.loudness,settings.overflow,
                       bool(getattr(settings,'continuous',False)),int(getattr(settings,'continuous_target_ms',100)))
            if fit_key != self.fit_key:
                self.final=None
                self.details={}
            if stage == 'C' and self.final is None:
                final,details=fit_processed(self.processed.copy(),self.rate,slot,settings,
                                          self.emotion_tempo,Path(folder),cancel)
                final.setflags(write=False)
                self.final,self.details,self.fit_key=final,details,fit_key
        details=dict(self.details,original_seconds=len(self.base)/self.rate,
            processed_seconds=len(self.processed)/self.rate if self.processed is not None else None,
            emotion=emotion,intensity=intensity,effect=settings.effect,strength=settings.strength,
            continuous_mode=bool(getattr(settings,'continuous',False)),
            continuity_trimmed_start=self.continuity_trim[0],
            continuity_trimmed_end=self.continuity_trim[1],
            continuity_trimmed_seconds=sum(self.continuity_trim))
        if slot is not None:
            details.update(caption=slot.caption.index,start_sample=slot.start,allowed_end=slot.end,
                           available_seconds=(slot.end-slot.start)/RATE)
        logging.info('Preview %s: %s',stage,details)
        samples={'A':self.base,'B':self.processed,'C':self.final}[stage]
        return PreviewResult(stage,samples.copy(),RATE if stage=='C' else self.rate,details)
