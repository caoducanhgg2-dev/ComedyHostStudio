# Third-party components

This source project does not include third-party binaries or model weights.
The Windows build installs and bundles the following upstream components.
Preserve license texts shipped in their distributions when redistributing.

| Component | Upstream / license |
| --- | --- |
| Kokoro weights | https://huggingface.co/hexgrad/Kokoro-82M — Apache-2.0 |
| kokoro-onnx | https://github.com/thewh1teagle/kokoro-onnx — MIT |
| Misaki | https://github.com/hexgrad/misaki — Apache-2.0, adapted Cutlet MIT |
| UniDic Lite | https://github.com/polm/unidic-lite — dictionary licenses included in package |
| fugashi | https://github.com/polm/fugashi — MIT, bundled MeCab notices |
| Qt / PySide6 | https://www.qt.io/licensing — LGPL/GPL/commercial terms in distribution |
| ONNX Runtime | https://github.com/microsoft/onnxruntime — MIT |
| eSpeak NG | https://github.com/espeak-ng/espeak-ng — GPL-3.0 |
| FFmpeg | https://github.com/GyanD/codexffmpeg — see the exact build's license/configuration |

FFmpeg is invoked as a separate process. Qt shared libraries are not statically linked.
The build records package versions and asset hashes; upstream release assets have no published
GitHub SHA-256 digest in the inspected release metadata. Generated hashes detect subsequent
corruption, and are not an independent upstream authenticity check.

Before public redistribution, assemble the corresponding source/license materials for the
exact bundled GPL/LGPL binary builds. The automated build is for personal acceptance testing;
this repository does not claim a completed third-party redistribution compliance package.

## Optional Aivis pack (not bundled in the core installer)

AivisSpeech Engine: https://github.com/Aivis-Project/AivisSpeech-Engine — LGPL-3.0; the original archive and its notices are preserved. Kohaku and Mao models: ACML-1.0, https://github.com/Aivis-Project/ACML/blob/master/ACML-1.0.md . Model use has content restrictions; commercial use is conditional.

Japanese BERT ONNX conversion by tsukumijima, based on ku-nlp/deberta-v2-large-japanese-char-wwm: https://huggingface.co/tsukumijima/deberta-v2-large-japanese-char-wwm-onnx — CC-BY-SA-4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Downloaded files are unmodified; source revision and integrity hashes are recorded in each installed pack manifest.

The optional archive extractor py7zr and its dependencies retain their distribution license metadata in the build. These licenses do not grant blanket rights to individual voice models.
