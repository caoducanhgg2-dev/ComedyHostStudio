COMEDY HOST STUDIO 5.5.5 - VISUAL-GROUNDED SRT
================================================

BASE BAT BUOC
- Comedy Host Studio 5.5.4 Clean dang duoc cai tai:
  %LOCALAPPDATA%\Programs\ComedyHostStudio
- Dong han app truoc khi cai.

MUC TIEU 5.5.5
- SRT la ban nen bam sat hinh anh de dua sang ChatGPT/Project viet lai sau.
- Khong co nghia la mo ta ngheo thong tin: caption van giu chu the, hanh dong, vat the/vat lieu, trang thai va thay doi nhin thay khi co the.
- US: thuong 8-12 tu/caption, uu tien 9-11; 10 tu khong con la luat cung.
- Timing US: giu khoang 4.08 giay/caption, gap 0.10 giay, full timeline.
- Khong ep hook/comedy/trend/catchphrase trong SRT-only.
- Khong raw Visual Brain paragraph, khong fragment, khong filler rong.
- Khong biet dong co, suy nghi, cam xuc, danh tinh, nguy hiem, thoi gian da troi qua, muc dich an hoac ket qua ngoai khung hinh.
- Cung mot hanh dong that co the giong y; chi exact sentence duplicate la loi lap cung.
- Mot caption loi duoc xu ly rieng; khong reject ca batch chi vi mot dong.

GIU NGUYEN TU 5.5.4
- Visual Brain Qwen3-VL 4B
- Smart Reviewer Writer local Qwen3 8B/4B theo hardware profile
- GPU Recovery / Safe GPU Auto / mot model mot luc
- analysis cache/resume
- che do Giữ thoại gốc: neu bat, thoai chi dung de hieu ngu canh, khong chep transcript vao SRT
- Vietnamese_Translation.txt sau SRT
- Audio+SRT cu khong bi thay doi boi writer 5.5.5

FILE MOI TRONG KET QUA
- Visual_Context.json: evidence chi tiet theo timestamp de dung khi viet lai sau.
- Visual_SRT_QA.json: word count, fragment, duplicate, fallback/review flags cua writer 5.5.5.

CAI DAT
1. Dong han Comedy Host Studio.
2. Giai nen goi 5.5.5.
3. Chay INSTALL_5.5.5.bat.
4. Neu muon, chay VERIFY_5.5.5.bat de kiem tra file/marker.
5. Mo app va test SRT US tren video da dung o 5.5.4 de so sanh.

ROLLBACK
- Chay RESTORE_5.5.4.bat khi app dang dong.
- Installer da sao luu engine 5.5.4 thanh engine_554_core.py va voice_catalog.5.5.4.bak.json.

AN TOAN SOURCE
- Khong dung VideoScriptAI/6.0.x.
- Khong dung 5.5.3f/g/h.
- Khong dung PowerShell chen code vao engine.py.
- Installer chi xac minh 5.5.4 Clean, sao luu file, roi thay file hoan chinh.
