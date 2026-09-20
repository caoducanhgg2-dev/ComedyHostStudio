"""Minimal sealed KorvaTTS ONNX runtime for SRT Voice Studio.

Adapted from dogenthq/KorvaTTS v0.1.3 (Apache-2.0). Network access and
Hugging Face auto-download are deliberately removed: this runtime accepts only
an explicitly verified local assets directory managed by korva_pack.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unicodedata import normalize
import numpy as np

REQUIRED_ONNX = (
    "duration_predictor.onnx","text_encoder.onnx","vector_estimator.onnx",
    "vocoder.onnx","tts.json","unicode_indexer.json",
)
MAX_TOTAL_STEPS=32
_REPLACEMENTS={"–":"-","‑":"-","—":"-","_":" ","“":'"',"”":'"',"‘":"'","’":"'","´":"'","[":" ","]":" ","|":" ","/":" ","#":" "}
_TRAILING=re.compile(r"[.!?;:,'\"')\]}…。」』】〉》›»]$")

def validate_assets(root):
    root=Path(root);onnx=root/"onnx";styles=root/"voice_styles"
    if not all((onnx/name).is_file() for name in REQUIRED_ONNX):
        raise FileNotFoundError("Gói Korva thiếu model ONNX bắt buộc.")
    if not styles.is_dir():raise FileNotFoundError("Gói Korva thiếu thư mục voice_styles.")
    return root

def normalize_text(text,lang="vi"):
    if lang!="vi":raise ValueError("Korva backend chỉ bật tiếng Việt.")
    text=normalize("NFKD",str(text))
    for src,dst in _REPLACEMENTS.items():text=text.replace(src,dst)
    text=re.sub(r"\s+"," ",text).strip()
    if text and not _TRAILING.search(text):text+="."
    return f"<vi>{text}</vi>"

def chunk_text(text,max_len=300):
    text=str(text).strip()
    if not text:return []
    chunks=[];current=""
    for sentence in re.split(r"(?<=[.!?])\s+",text):
        pieces=[]
        if len(sentence)<=max_len:pieces=[sentence]
        else:
            piece=""
            for word in sentence.split():
                if piece and len(piece)+len(word)+1>max_len:
                    pieces.append(piece);piece=word
                else:piece+=(" " if piece else "")+word
            if piece:pieces.append(piece)
        for part in pieces:
            if current and len(current)+len(part)+1>max_len:
                chunks.append(current.strip());current=part
            else:current+=(" " if current else "")+part
    if current:chunks.append(current.strip())
    return chunks

def length_to_mask(lengths,max_len=None):
    max_len=max_len or int(lengths.max());ids=np.arange(max_len)
    return (ids<np.expand_dims(lengths,1)).astype(np.float32).reshape(-1,1,max_len)

class TextProcessor:
    def __init__(self,path):self.indexer=json.loads(Path(path).read_text("utf-8"))
    def encode(self,text):
        ids=[]
        for ch in normalize_text(text):
            code=ord(ch)
            if code<len(self.indexer) and self.indexer[code]>=0:ids.append(int(self.indexer[code]))
        if not ids:raise RuntimeError("Không mã hóa được nội dung tiếng Việt.")
        arr=np.asarray([ids],dtype=np.int64)
        return arr,length_to_mask(np.asarray([len(ids)],dtype=np.int64))

class VoiceStyle:
    def __init__(self,path):
        data=json.loads(Path(path).read_text("utf-8"))
        self.ttl=np.asarray(data["style_ttl"]["data"],dtype=np.float32).reshape([int(x) for x in data["style_ttl"]["dims"]])
        self.dp=np.asarray(data["style_dp"]["data"],dtype=np.float32).reshape([int(x) for x in data["style_dp"]["dims"]])
        if self.ttl.shape[0]!=1 or self.dp.shape[0]!=1:raise ValueError("Voice style Korva không hợp lệ.")

def _clean_tail(wav,rate):
    """Remove detached vocoder burst/silence then fade to zero (Korva v0.1.3 logic)."""
    wav=np.asarray(wav,dtype=np.float32).reshape(-1).copy()
    frame=max(1,int(.02*rate));start=max(0,len(wav)-int(.6*rate))
    gap_start=None;run=0;best=None
    for i in range(start,max(start,len(wav)-frame),frame):
        block=wav[i:i+frame]
        rms=float(np.sqrt(np.mean(block*block))) if len(block) else 0.0
        if rms<.01:
            if run==0:gap_start=i
            run+=frame
        else:
            if run>=.05*rate:best=gap_start
            run=0
    if run>=.05*rate:best=gap_start
    if best is not None:
        after=wav[best+int(.05*rate):]
        peak=float(np.max(np.abs(after))) if len(after) else 0.0
        if peak<.05 or (len(after)<=int(.35*rate) and peak>=.4):
            wav=wav[:best+int(.05*rate)]
    n=min(len(wav),int(.03*rate))
    if n:wav[-n:]*=np.linspace(1.0,0.0,n,dtype=np.float32)
    return wav

class KorvaRuntime:
    def __init__(self,assets_dir,num_threads=None):
        import onnxruntime as ort
        self.assets=validate_assets(assets_dir);onnx=self.assets/"onnx"
        cfg=json.loads((onnx/"tts.json").read_text("utf-8"))
        self.rate=int(cfg["ae"]["sample_rate"]);self.base_chunk=int(cfg["ae"]["base_chunk_size"])
        self.compress=int(cfg["ttl"]["chunk_compress_factor"]);self.latent_dim=int(cfg["ttl"]["latent_dim"])
        opts=ort.SessionOptions()
        if num_threads:opts.intra_op_num_threads=int(num_threads)
        opts.inter_op_num_threads=1
        providers=["CPUExecutionProvider"]
        def open_model(name):return ort.InferenceSession(str(onnx/name),sess_options=opts,providers=providers)
        self.duration=open_model("duration_predictor.onnx");self.encoder=open_model("text_encoder.onnx")
        self.vector=open_model("vector_estimator.onnx");self.vocoder=open_model("vocoder.onnx")
        self.processor=TextProcessor(onnx/"unicode_indexer.json");self.styles={}

    def voice_names(self):return sorted(p.stem for p in (self.assets/"voice_styles").glob("*.json"))
    def style(self,name):
        if name not in self.voice_names():raise ValueError("Giọng Korva chưa được cài.")
        if name not in self.styles:self.styles[name]=VoiceStyle(self.assets/"voice_styles"/f"{name}.json")
        return self.styles[name]

    def _infer(self,text,style,total_steps,speed,rng):
        text_ids,text_mask=self.processor.encode(text)
        duration=self.duration.run(None,{"text_ids":text_ids,"style_dp":style.dp,"text_mask":text_mask})[0]/speed
        text_emb=self.encoder.run(None,{"text_ids":text_ids,"style_ttl":style.ttl,"text_mask":text_mask})[0]
        wav_lengths=(duration*self.rate).astype(np.int64);chunk=self.base_chunk*self.compress
        latent_lengths=(wav_lengths+chunk-1)//chunk;latent_len=int(latent_lengths.max())
        latent=rng.standard_normal((1,self.latent_dim*self.compress,latent_len),dtype=np.float32)
        latent_mask=length_to_mask(latent_lengths,latent_len);latent*=latent_mask
        total=np.asarray([total_steps],dtype=np.float32)
        for step in range(total_steps):
            latent=self.vector.run(None,{"noisy_latent":latent,"text_emb":text_emb,"style_ttl":style.ttl,
                "text_mask":text_mask,"latent_mask":latent_mask,"current_step":np.asarray([step],dtype=np.float32),
                "total_step":total})[0]
        wav=self.vocoder.run(None,{"latent":latent})[0]
        return _clean_tail(np.asarray(wav,dtype=np.float32).reshape(-1)[:int(float(duration[0])*self.rate)],self.rate)

    def synthesize(self,text,voice,total_steps=16,speed=1.0,seed=None):
        if not 1<=int(total_steps)<=MAX_TOTAL_STEPS:raise ValueError("Korva total_steps không hợp lệ.")
        if not .5<=float(speed)<=2:raise ValueError("Korva speed không hợp lệ.")
        chunks=chunk_text(text)
        if not chunks:raise ValueError("Nội dung tiếng Việt trống.")
        style=self.style(voice);rng=np.random.default_rng(seed);pieces=[];silence=np.zeros(int(.08*self.rate),dtype=np.float32)
        for chunk in chunks:
            if pieces:pieces.append(silence)
            pieces.append(self._infer(chunk,style,int(total_steps),float(speed),rng))
        result=np.concatenate(pieces).astype(np.float32,copy=False)
        if not len(result) or not np.isfinite(result).all() or not np.any(np.abs(result)>1e-7):
            raise RuntimeError("Korva trả audio rỗng hoặc không hợp lệ.")
        return result,self.rate
