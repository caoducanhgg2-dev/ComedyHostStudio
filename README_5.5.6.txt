Comedy Host Studio 5.5.6 - Visual Quality + Fast Stability

Muc tieu:
- SRT bam sat hinh anh, giu du thong tin de dua sang ChatGPT Project viet lai sau.
- Khong ep dung 10 tu/caption.
- 8-12 tu la vung dep; 7-14 binh thuong; 15-18 duoc phep neu chi tiet hinh anh huu ich.
- Khong dung raw Visual Brain paragraph/fragment lam caption.
- Exact duplicate repair tung caption, khong huy ca SRT.
- Visual_Context.json tiep tuc duoc xuat de lam context viet lai.

Toi uu toc do:
- Bo GoldStyle/Hook/Personality/Global Editor trong SRT-only.
- Creative plan SRT-only la deterministic, khong goi AI rieng.
- Writer viet theo batch, chi sua caption loi thay vi viet lai ca window.
- Truoc khi Writer tai, Visual Brain duoc unload truc tiep de nhan toan bo RAM/VRAM; Ollama server van giu, khong restart.
- Ket thuc moi video, Writer duoc unload ngay de RAM Windows hoi phuc va video tiep theo bat dau sach.
- Dich Viet dung batch 24 (thuong 2 call cho ~45 caption), bo AI summary khong con can thiet.

Memory Guard cho RTX 2070 / RAM 16GB:
Log thuc te cho thay Ollama BatchSize=512 tao CPU compute graph ~4.2 GiB khi RAM vat ly chi con ~1.2-1.6 GiB.
5.5.6 tu chon batch lon nhat an toan:
- Vision: 64 khi RAM du; 48 / 24 / 16 khi RAM giam.
- Writer: 128 / 96 / 64 / 32 tuy RAM.
- Chi ha Vision context 4096 -> 3072/2560 khi RAM rat thap.
- Neu preflight gap dung loi system-memory, retry 1 lan bang batch nho; khong CPU-fallback am tham.

Cai dat:
1. Dong han Comedy Host Studio.
2. Chay INSTALL_5.5.6.bat.
3. Mo app va test video.
4. Nen test them 2 video lien tiep trong cung phien app.

Nguon sach:
- Base: 5.5.4 Clean core + Visual-Grounded clean wrapper.
- Khong VideoScriptAI/6.0.x.
- Khong 5.5.3f/g/h.
- Khong PowerShell chen code.
