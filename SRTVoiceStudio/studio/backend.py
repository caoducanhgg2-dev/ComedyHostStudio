import hashlib
import json
import os
from .paths import root, native_data_path
from .audio import check_cancel

EN_US_VOICES = ['af_heart', 'af_alloy', 'af_aoede', 'af_bella', 'af_jessica',
                'af_kore', 'af_nicole', 'af_nova', 'af_river', 'af_sarah', 'af_sky',
                'am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam',
                'am_michael', 'am_onyx', 'am_puck', 'am_santa']
# Kokoro v1.0 ships these British speakers in the same voices-v1.0.bin bundle.
EN_GB_VOICES = ['bf_alice', 'bf_emma', 'bf_isabella', 'bf_lily',
                'bm_daniel', 'bm_fable', 'bm_george', 'bm_lewis']
# Backward-compatible name used by 1.0–1.2 code/tests: US English only.
EN_VOICES = EN_US_VOICES
JA_VOICES = ['jf_alpha', 'jf_gongitsune', 'jf_nezumi', 'jf_tebukuro', 'jm_kumo']
PREVIEW = {'English US': 'This is a preview of the selected American voice.',
           'English UK': 'This is a preview of the selected British voice.',
           'Japanese': 'これは選択した音声のプレビューです。'}

class Backend:
    def __init__(self):
        self.model = None
        self.japanese = None

    def load(self, cancel, progress):
        if self.model is not None:
            return
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        folder = root() / 'models'
        manifest = folder / 'manifest.json'
        if not manifest.is_file():
            raise RuntimeError('Thiếu model offline trong bộ cài. Hãy cài lại bản đầy đủ.')
        entries = json.loads(manifest.read_text('utf-8'))
        for name, digest in entries.items():
            check_cancel(cancel)
            progress(f'Kiểm tra model: {name}')
            file = folder / name
            valid = False
            if file.is_file():
                with file.open('rb') as stream:
                    valid = hashlib.file_digest(stream, 'sha256').hexdigest() == digest
            if not valid:
                raise RuntimeError(f'Model thiếu hoặc sai checksum: {name}. Hãy cài lại.')
        progress('Đang nạp Kokoro • CPU')
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = min(6, max(1, (os.cpu_count() or 2)//2))
        opts.inter_op_num_threads = 1
        session = ort.InferenceSession(str(folder/'kokoro-v1.0.onnx'), sess_options=opts,
                                       providers=['CPUExecutionProvider'])
        progress('ONNX đã nạp • Đang nạp phonemizer')
        import espeakng_loader
        from kokoro_onnx.config import EspeakConfig
        config = EspeakConfig(lib_path=espeakng_loader.get_library_path(),
                              data_path=native_data_path(espeakng_loader.get_data_path()))
        self.model = Kokoro.from_session(session, str(folder/'voices-v1.0.bin'), espeak_config=config)
        progress('Phonemizer đã nạp')
        missing = set(EN_US_VOICES + EN_GB_VOICES + JA_VOICES) - set(self.model.get_voices())
        if missing:
            self.model = None
            raise RuntimeError(f'Gói model thiếu voice: {sorted(missing)}')
        check_cancel(cancel)

    def synthesize(self, text, language, voice, cancel, progress=lambda _: None):
        self.load(cancel, progress)
        check_cancel(cancel)
        if language == 'Japanese':
            choices = JA_VOICES
            if voice not in choices:
                raise ValueError('Voice không khớp ngôn ngữ.')
            if self.japanese is None:
                # Import Cutlet directly: no pyopenjtalk, torch, or runtime downloads.
                # fugashi automatically finds the bundled unidic_lite dictionary.
                from misaki.cutlet import Cutlet
                self.japanese = Cutlet()
            phonemes, _ = self.japanese(text)
            if not phonemes.strip():
                raise RuntimeError('Không chuyển được nội dung tiếng Nhật thành âm vị.')
            result = self.model.create(phonemes, voice=voice, speed=1.0,
                is_phonemes=True, lang='ja', trim=True, sentence_pause=0.10, clause_pause=0.05)
        elif language == 'English US':
            if voice not in EN_US_VOICES:
                raise ValueError('Voice không khớp ngôn ngữ.')
            result = self.model.create(text, voice=voice, speed=1.0,
                lang='en-us', trim=True, sentence_pause=0.10, clause_pause=0.05)
        elif language == 'English UK':
            if voice not in EN_GB_VOICES:
                raise ValueError('Voice không khớp ngôn ngữ.')
            result = self.model.create(text, voice=voice, speed=1.0,
                lang='en-gb', trim=True, sentence_pause=0.10, clause_pause=0.05)
        else:
            raise ValueError('Ngôn ngữ chưa được hỗ trợ.')
        check_cancel(cancel)
        return result
