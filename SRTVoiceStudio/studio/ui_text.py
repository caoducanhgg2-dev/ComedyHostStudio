"""Vietnamese display labels; stable backend IDs are stored as combo itemData."""
LANGUAGES={'English US':'Tiếng Anh (Mỹ)','English UK':'Tiếng Anh (Anh)','Japanese':'Tiếng Nhật'}
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

# Mô tả định hướng để người dùng chọn nhanh. Đây không phải điểm chất lượng
# và không thay thế đánh giá nghe thực tế trong ratings.csv.
VOICE_CHARACTERISTICS={
    'jf_alpha':'Sáng, trẻ trung, linh hoạt',
    'jf_gongitsune':'Mềm, dịu, hợp kể chuyện',
    'jf_nezumi':'Nhẹ, đáng yêu, thiên hoạt hình',
    'jf_tebukuro':'Ấm, điềm tĩnh, tự nhiên',
    'jm_kumo':'Trầm vừa, bình tĩnh, hợp thuyết minh',
    'aivis:e756b8e4-b606-4e15-99b1-3f9c6a1b2317':'Tự nhiên, mềm, hội thoại đời thường',
    'aivis:5680ac39-43c9-487a-bc3e-018c0d29cc38':'Nhẹ, ngọt, thư giãn',
    'am_onyx':'Trầm, kể chuyện',
}

def voice_label(voice):
    if not isinstance(voice,str):return 'Chưa chọn giọng'
    if len(voice)<4 or voice[:3] not in ('af_','am_','bf_','bm_','jf_','jm_'):return voice
    name=voice.split('_',1)[1].replace('_',' ').title()
    gender='Nữ' if voice[1]=='f' else 'Nam'
    region=' · Anh' if voice[0]=='b' else ''
    return f'{name} — {gender}{region}'

def voice_characteristic(voice):
    return VOICE_CHARACTERISTICS.get(voice,'') if isinstance(voice,str) else ''

def voice_display_label(voice,fallback=None):
    base=voice_label(voice) if isinstance(voice,str) and len(voice)>=4 and voice[:3] in ('af_','am_','bf_','bm_','jf_','jm_') else (fallback or voice_label(voice))
    trait=voice_characteristic(voice)
    return f'{base} · {trait}' if trait else base

def display(value):
    for mapping in (LANGUAGES,MODES,INTENSITIES,EMOTIONS,EFFECTS,OVERFLOWS):
        if value in mapping:return mapping[value]
    return value

def message(text):
    if text == 'SHORT SCRIPT / REMAINING SILENCE':return 'CÂU THOẠI NGẮN / CÒN KHOẢNG LẶNG'
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
