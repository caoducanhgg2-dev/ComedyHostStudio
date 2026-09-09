Comedy Host Studio 5.5.7 - Visual Continuity + Fast

Muc tieu:
- SRT bam sat hinh anh va giu chi tiet huu ich de dua sang ChatGPT Project viet lai sau.
- Khong ep dung 10 tu/caption.
- 8-12 tu la vung dep; 7-14 binh thuong; 15-18 duoc phep neu can giu chi tiet hinh anh.
- Moi caption uu tien MOT cau tu nhien, khong raw Visual Brain paragraph.

Sua theo test Vietnamese_Translation(8).txt:
- Chan ro ri ky thuat nhu "at 11", TIME, timestamp, frame, pts_time, "across frames".
- Loai mo ta suy dien nhu "suggesting agitation"/"erratic" khi khong can thiet.
- "flame-like object" duoc trung hoa ve visible object thay vi suy dien hinh dang.
- Neu boi canh khong thay doi (aquarium/gravel/filter/bubbles...), caption sau khong lap lai toan bo boilerplate; uu tien chi tiet moi dang thay doi.
- Fallback uu tien chi tiet cu the moi/khac biet nhu mau sac, vi tri, huong di chuyen, vat the moi thay vi boi canh tinh.
- Exact duplicate chi sua caption bi loi; similarity cua hanh dong that chi la warning/repair best-effort.
- Regression bat buoc dung chinh cac mau loi tren de tranh tai xuat hien o ban sau.

Toc do:
- Writer batch 10 caption tren Qwen3 8B, 8 caption tren writer nho hon.
- Repair chi chay cho caption co loi; khong rewrite ca window neu mot caption loi.
- Moi caption repair toi da 2 lan cho loi chat luong; continuity similarity chi 1 lan best-effort.
- Giu Vision->Writer RAM/VRAM handoff, adaptive Memory Guard, unload Writer sau moi video va khong restart Ollama.
- Vietnamese review translation giu batch 24 va khong co AI summary pass rieng.

Timing:
- Giu full timeline.
- Gap muc tieu 0.10s.
- Khong thay doi sampling Visual Brain cua core 5.5.4: quet timeline + scene cut + regular sample.

Cai dat:
1. Dong han Comedy Host Studio.
2. Giai nen goi update.
3. Chay INSTALL_5.5.7.bat.
4. Mo app va test lai video aquarium truoc, sau do chay video thu hai ma khong dong app.

Nguon sach:
- Base: 5.5.4 Clean core + 5.5.6 Fast Stability.
- Khong VideoScriptAI/6.0.x.
- Khong 5.5.3f/g/h.
- Khong PowerShell chen code.
