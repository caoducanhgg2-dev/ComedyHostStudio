"""Vietnamese display labels; stable backend IDs are stored as combo itemData."""
LANGUAGES={'English US':'Tiếng Anh (Mỹ)','English UK':'Tiếng Anh (Anh)','Japanese':'Tiếng Nhật','Vietnamese':'Tiếng Việt'}
MODES={'Manual':'Thủ công','Auto':'Tự động'}
INTENSITIES={'Mild':'Nhẹ','Medium':'Vừa','Strong':'Mạnh'}
EMOTIONS={'Natural':'Tự nhiên','Happy':'Vui vẻ','Excited':'Hào hứng','Funny / Playful':'Dí dỏm / Vui nhộn',
 'Serious':'Nghiêm túc','Calm':'Điềm tĩnh','Surprised':'Ngạc nhiên','Dramatic':'Kịch tính',
 'Sad':'Buồn','Angry':'Giận dữ','Whisper-like':'Mô phỏng thì thầm','Narrator':'Kể chuyện'}
EFFECTS={'None':'Không hiệu ứng','Deep Voice':'Giọng trầm','Bright Voice':'Giọng sáng','Radio':'Phát thanh',
 'Telephone':'Điện thoại','Walkie-Talkie':'Bộ đàm','Megaphone':'Loa phóng thanh','Intercom':'Loa nội bộ',
 'Robot':'Rô-bốt','Reverb':'Vang phòng','Cave':'Vang hang động','Echo':'Tiếng vọng','Distortion':'Méo tiếng',
 'Cheap Microphone':'Mic chất lượng thấp','Underwater':'Dưới nước','Old Tape':'Băng từ cũ'}
OVERFLOWS={'Safe Trim':'Cắt an toàn','Stop and Report':'Dừng và báo lỗi'}
PREVIEW_LABELS={'A':'A · Giọng gốc','B':'B · Đã xử lý','C':'C · Theo mốc SRT'}

# Mô tả định hướng để người dùng chọn nhanh. Đây là chú thích biên tập,
# không phải điểm chất lượng và không thay thế đánh giá nghe trong ratings.csv.
VOICE_CHARACTERISTICS={
    # Kokoro English US — 20 voices
    'af_heart':'Ấm, thân thiện, tự nhiên',
    'af_alloy':'Cân bằng, rõ, hiện đại',
    'af_aoede':'Sáng, mềm, giàu biểu cảm',
    'af_bella':'Ấm, nữ tính, hợp kể chuyện',
    'af_jessica':'Rõ, chuyên nghiệp, hội thoại',
    'af_kore':'Trẻ, chắc, giàu năng lượng',
    'af_nicole':'Trầm vừa, điềm tĩnh, hợp podcast',
    'af_nova':'Sáng, nhanh, hiện đại',
    'af_river':'Mềm, trung tính, thư giãn',
    'af_sarah':'Rõ, ấm, hợp thuyết minh',
    'af_sky':'Nhẹ, trẻ, tươi sáng',
    'am_adam':'Trầm vừa, rõ, hợp thuyết minh',
    'am_echo':'Mềm, hiện đại, hội thoại',
    'am_eric':'Ổn định, rõ, chuyên nghiệp',
    'am_fenrir':'Mạnh, năng lượng, kịch tính',
    'am_liam':'Trẻ, thân thiện, tự nhiên',
    'am_michael':'Ấm, chắc, hợp kể chuyện',
    'am_onyx':'Trầm, dày, hợp kể chuyện',
    'am_puck':'Sáng, nhanh, hợp reviewer / comedy',
    'am_santa':'Trầm ấm, chậm rãi, thiên nhân vật',

    # Kokoro English UK — 8 voices
    'bf_alice':'Rõ, thanh lịch, hợp thuyết minh',
    'bf_emma':'Tự nhiên, thân thiện, hội thoại',
    'bf_isabella':'Ấm, mềm, hợp kể chuyện',
    'bf_lily':'Nhẹ, trẻ, tinh tế',
    'bm_daniel':'Trầm vừa, rõ, chuyên nghiệp',
    'bm_fable':'Biểu cảm, kể chuyện, thiên nhân vật',
    'bm_george':'Ấm, chững chạc, hợp thuyết minh',
    'bm_lewis':'Tự nhiên, bình tĩnh, hội thoại',

    # Kokoro Japanese — 5 voices
    'jf_alpha':'Sáng, trẻ trung, linh hoạt',
    'jf_gongitsune':'Mềm, dịu, hợp kể chuyện',
    'jf_nezumi':'Nhẹ, đáng yêu, thiên hoạt hình',
    'jf_tebukuro':'Ấm, điềm tĩnh, tự nhiên',
    'jm_kumo':'Trầm vừa, bình tĩnh, hợp thuyết minh',

    # Aivis Japanese — optional local voices
    'aivis:e756b8e4-b606-4e15-99b1-3f9c6a1b2317':'Tự nhiên, mềm, hội thoại đời thường',
    'aivis:5680ac39-43c9-487a-bc3e-018c0d29cc38':'Nhẹ, ngọt, thư giãn',
    'aivis:d2c99ca6-73e5-486c-994e-ee0ce2d74928':'Trẻ, sáng, giàu cảm xúc',
    'aivis:561e4e59-3bc9-4726-9028-44a3c12a6f1d':'Baritone, trung niên, hợp kể chuyện',
    'aivis:41b7785f-35cc-4089-a360-dd8a63da5e75':'Trẻ, mềm, biểu cảm',
    'aivis:bf56410a-d8e6-430d-a477-f789e16206d3':'Trẻ, tự nhiên, hội thoại',
    'aivis:c99b650e-4d24-4528-a7a3-6d0f9692f839':'Nam trẻ, thấp, điềm tĩnh, hội thoại',
    'aivis:161ab385-07a5-4dd6-a045-5b0f21dfd9ec':'Nữ trẻ, tự nhiên, nhiều sắc thái',
    'aivis:ef92118d-eda3-49d9-858d-1e9ae4dae714':'Nữ trẻ, sáng, biểu cảm',
    'aivis:4a43610f-8ace-4fe2-9541-eb26255f1927':'Nữ trẻ, tự nhiên, hội thoại',
    'aivis:47ddff3b-10b4-48e8-8d5d-692461fa7f96':'Nữ trẻ, mềm, nhiều sắc thái',

    # KorvaTTS Vietnamese — 10 optional offline voices
    'korva:bao_kim':'Nữ · rõ, hiện đại, hợp podcast / reviewer',
    'korva:khanh_vy':'Nữ · trẻ, sáng, hợp short-form / hội thoại',
    'korva:ngoc_huyen':'Nữ · mềm, tự nhiên, hợp kể chuyện',
    'korva:phuong_linh':'Nữ · rõ, cân bằng, hợp thuyết minh',
    'korva:quynh_nhu':'Nữ · nhẹ, thân thiện, hợp nội dung đời thường',
    'korva:gia_bao':'Nam · rõ, trẻ, hợp reviewer',
    'korva:hoang_nam':'Nam · chắc, tự nhiên, hợp thuyết minh',
    'korva:huu_dat':'Nam · trầm vừa, hợp kể chuyện',
    'korva:quang_huy':'Nam · sáng, hiện đại, hợp short-form',
    'korva:thanh_phong':'Nam · điềm tĩnh, rõ, hợp documentary',
}

def voice_characteristic(voice):
    return VOICE_CHARACTERISTICS.get(voice,'') if isinstance(voice,str) else ''

def voice_label(voice):
    if not isinstance(voice,str):return 'Chưa chọn giọng'
    if len(voice)<4 or voice[:3] not in ('af_','am_','bf_','bm_','jf_','jm_'):return voice
    name=voice.split('_',1)[1].replace('_',' ').title()
    gender='Nữ' if voice[1]=='f' else 'Nam'
    region=' · Anh' if voice[0]=='b' else ''
    base=f'{name} — {gender}{region}'
    trait=voice_characteristic(voice)
    return f'{base} · {trait}' if trait else base

def voice_display_label(voice,fallback=None):
    if isinstance(voice,str) and len(voice)>=4 and voice[:3] in ('af_','am_','bf_','bm_','jf_','jm_'):
        return voice_label(voice)
    base=fallback or voice_label(voice)
    trait=voice_characteristic(voice)
    if trait and trait not in str(base):return f'{base} · {trait}'
    return base

def display(value):
    for mapping in (LANGUAGES,MODES,INTENSITIES,EMOTIONS,EFFECTS,OVERFLOWS):
        if value in mapping:return mapping[value]
    return value

def message(text):
    if text == 'SHORT SCRIPT / REMAINING SILENCE':return 'CÂU THOẠI NGẮN / CÒN KHOẢNG LẶNG'
    if text == 'CONTINUOUS TARGET UNREACHABLE / SHORT SCRIPT':
        return 'CÂU THOẠI NGẮN / KHÔNG THỂ ĐẠT KHOẢNG CHUYỂN MỤC TIÊU'
    replacements={
     'SHORT SCRIPT / UNDERFILLED SLOT':'LỜI THOẠI NGẮN / CHƯA LẤP ĐẦY KHUNG',
     'TIMELINE VALID':'MỐC THỜI GIAN HỢP LỆ','Creating voice':'Đang tạo giọng',
     'CAPTION':'CÂU','Caption':'Câu','TOO LONG':'QUÁ DÀI','Processed':'Sau xử lý',
     'Slot':'Khung','Speed':'Tốc độ','Adjusted':'Sau căn chỉnh','Fit':'Tốc độ',
     'Overlap':'Chồng tiếng','Silence':'Im lặng',
     'Temporary directory':'Thư mục tạm','Timeline engine':'Bộ căn mốc thời gian',
     'Timeline Preview C':'Nghe thử C theo mốc','Preview A':'Nghe thử A','Preview B':'Nghe thử B',
     'Natural / None reference':'Tham chiếu giọng sạch','Emotion Processor':'Bộ xử lý cảm xúc',
     'Voice FX Processor':'Bộ hiệu ứng giọng','FFmpeg filters':'Bộ lọc FFmpeg',
     'Reverb Tail Guard':'Chặn đuôi vang phòng','Echo Tail Guard':'Chặn đuôi tiếng vọng',
     'Cave Tail Guard':'Chặn đuôi vang hang động','Underfill Fit':'Căn câu ngắn',
     'Japanese G2P':'Chuyển âm vị tiếng Nhật','Kokoro backend':'Bộ tạo giọng Kokoro',
     'Overlap Validator':'Kiểm tra chồng tiếng','MP3 encoder / output directory':'Bộ mã hóa MP3 / thư mục đầu ra',
     'MP3 encoder':'Bộ mã hóa MP3','English US TTS':'Tạo giọng tiếng Anh (Mỹ)',
     'English UK TTS':'Tạo giọng tiếng Anh (Anh)','Japanese TTS':'Tạo giọng tiếng Nhật',
     'Emotion / FX / Preview':'Cảm xúc / hiệu ứng / nghe thử',
     'Backend / G2P / Validator':'Bộ tạo giọng / âm vị / kiểm tra',
     'audio generated':'đã tạo âm thanh','same immutable A':'dùng cùng giọng gốc A',
     'production fit':'dùng chung bộ căn thời gian','invalid boundary rejected':'đã chặn vượt mốc',
     '12 presets x 3 intensities':'12 cảm xúc × 3 mức độ','16 choices x 3 strengths':'16 lựa chọn × 3 mức độ',
     'FAILED':'LỖI','OK':'ĐẠT'}
    for old in sorted(replacements,key=len,reverse=True):text=text.replace(old,replacements[old])
    return text