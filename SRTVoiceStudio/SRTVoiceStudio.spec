from PyInstaller.utils.hooks import collect_all, copy_metadata
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root/'models'), 'models'), (str(root/'third_party'),'third_party'),
         (str(root/'README_VI.md'),'.'), (str(root/'samples'),'samples')]
binaries = [(str(root/'bin'/'ffmpeg.exe'),'bin'), (str(root/'bin'/'ffprobe.exe'),'bin')]
hiddenimports = ['PySide6.QtMultimedia','PySide6.QtWidgets', 'misaki.cutlet', 'unidic_lite']
for package in ['kokoro_onnx','onnxruntime','espeakng_loader','phonemizer','fugashi','unidic_lite']:
    d,b,h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
# Collect Misaki's data without pulling in unrelated language engines / torch.
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('misaki')
for package in ['kokoro-onnx','misaki','phonemizer','espeakng-loader','fugashi','unidic-lite']:
    datas += copy_metadata(package)
a = Analysis([str(root/'main.py')],pathex=[str(root)],binaries=binaries,datas=datas,
    hiddenimports=hiddenimports,excludes=['tkinter','torch','spacy','transformers','pyopenjtalk','pytest'])
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='SRTVoiceStudio',console=False,
          debug=False,strip=False,upx=False,manifest=str(root/'app.manifest'))
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SRTVoiceStudio')
