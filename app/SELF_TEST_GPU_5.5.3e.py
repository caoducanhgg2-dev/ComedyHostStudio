from pathlib import Path
import ast
root=Path(__file__).resolve().parent
src=(root/'engine.py').read_text('utf-8')
ast.parse(src)
checks={
 'version_554':'beta5.5.4-clean-installer' in src,
 'safe_num_gpu_minus1':'"num_gpu": -1' in src,
 'no_num_gpu_999':'"num_gpu": 999' not in src,
 'http_error_handled':'except urllib.error.HTTPError' in src,
 'auto_retry':'ollama-auto' in src and 'safe-max-offload' in src,
 'preflight_553b':'GPU_PREFLIGHT_5.5.3b.json' in src,
 'fit_not_disabled':'LLAMA_ARG_FIT' not in src,
 'overhead_not_forced':'OLLAMA_GPU_OVERHEAD' not in src,
 'goldstyle_preserved':'GoldStyle' in src or 'gold' in src.lower(),
}
for k,v in checks.items(): print(('PASS' if v else 'FAIL'), k)
if not all(checks.values()): raise SystemExit(1)
print(f'PASS {sum(checks.values())}/{len(checks)} GPU recovery checks')
