Comedy Host Studio 5.5.6 - Visual Quality + Stability

Muc tieu:
- SRT bam sat hinh anh, giu du thong tin de dua sang ChatGPT Project viet lai sau.
- Khong ep dung 10 tu/caption.
- 8-12 tu la vung dep; 7-14 binh thuong; 15-18 duoc phep neu chi tiet hinh anh huu ich.
- Khong dung raw Visual Brain paragraph/fragment lam caption.
- Exact duplicate repair tung caption, khong huy ca SRT.
- Visual_Context.json tiep tuc duoc xuat de lam context viet lai.

Loi RAM/GPU da sua:
Log thuc te cho thay Qwen3-VL khoi dong voi Ollama BatchSize=512 khi Windows chi con ~1.2-1.6 GiB RAM vat ly trong. CPU compute graph len toi ~4.2 GiB, lam Ollama bao model requires more system memory.
5.5.6 dat num_batch 64 cho Vision binh thuong, 32 khi RAM trong <2.5 GiB; khi RAM rat thap, Vision context duoc ha tam thoi toi 3072. Writer dung batch 128/64 tuy ap luc RAM.

Video lien tiep:
- Truoc video thu 2 tro di trong cung runtime, app unload model Ollama con resident.
- Reset backend diagnostic state, khong xoa model/cache/output.

Cai dat:
1. Dong han Comedy Host Studio.
2. Chay INSTALL_5.5.6.bat.
3. Mo app va test 2 video lien tiep.

Nguon sach:
- Base: 5.5.4 Clean core + 5.5.5 Visual-Grounded clean wrapper.
- Khong VideoScriptAI/6.0.x.
- Khong 5.5.3f/g/h.
- Khong PowerShell chen code.
