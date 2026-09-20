"""Vietnamese-first optional local backend powered by verified KorvaTTS assets."""
from __future__ import annotations
import os
from .audio import check_cancel
from .backend import PREVIEW
from .voice_catalog import korva_catalog

class KorvaBackend:
    engine="Korva"
    def __init__(self,assets_dir,runtime_factory=None):
        self.assets_dir=assets_dir;self.runtime_factory=runtime_factory;self.runtime=None
        self.voices={v.id:v for v in korva_catalog()}
    def list_voices(self):return list(self.voices.values())
    def capabilities(self):return dict(offline=True,cpu=True,native_styles=False)
    def styles(self,voice):return ()
    def license_info(self,voice):
        v=self.voices[voice];return dict(license=v.license,source=v.source)
    def _runtime(self):
        if self.runtime is None:
            if self.runtime_factory:self.runtime=self.runtime_factory(self.assets_dir)
            else:
                from .korva_runtime import KorvaRuntime
                self.runtime=KorvaRuntime(self.assets_dir,num_threads=min(6,max(1,(os.cpu_count() or 2)//2)))
        return self.runtime
    def synthesize(self,text,language,voice,cancel,progress=lambda _:None):
        if language!="Vietnamese" or voice not in self.voices:
            raise ValueError("Giọng Korva không khớp ngôn ngữ hoặc chưa được cài.")
        check_cancel(cancel);progress("Đang tạo giọng Việt Korva • CPU")
        samples,rate=self._runtime().synthesize(text,self.voices[voice].speaker_uuid,total_steps=16,speed=1.0)
        check_cancel(cancel)
        return samples,rate
    def preview(self,language,voice,cancel):
        return self.synthesize(PREVIEW["Vietnamese"],language,voice,cancel)
