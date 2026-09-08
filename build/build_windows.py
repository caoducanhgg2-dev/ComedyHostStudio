"""Build only from the two hash-pinned uploads; execute on a disposable Windows runner."""
from pathlib import Path
import ast
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PINNED = {
    ".exe": "76f865f699a51d9a5384e5ccefd12185fe3be50d7bc29189db40818d5667c7ab",
    ".zip": "ab66520762543dac11c8c9ea1ae1e0539f0434b103fab0f5e20bedc8f6f9e07f",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, cwd=ROOT):
    proc = subprocess.run([str(x) for x in argv], cwd=cwd, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          encoding="utf-8", errors="replace", timeout=900)
    with (DIST / "build-log.txt").open("a", encoding="utf-8") as log:
        log.write(str(argv[0]) + "\n" + proc.stdout + "\nexit=" + str(proc.returncode) + "\n")
    print(proc.stdout)
    if proc.returncode:
        raise RuntimeError(f"Command failed: {argv[0]}, exit={proc.returncode}")


def main():
    if os.name != "nt":
        raise RuntimeError("Windows verification runner required")
    DIST.mkdir(exist_ok=True)
    sources = {}
    for suffix, expected in PINNED.items():
        matches = [p for p in (ROOT / "sources").glob("*" + suffix) if digest(p) == expected]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one original {suffix} matching SHA-256")
        sources[suffix] = matches[0]
    seven = shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
    compiler = shutil.which("makensis") or r"C:\Program Files (x86)\NSIS\makensis.exe"
    if not Path(seven).is_file() or not Path(compiler).is_file():
        raise RuntimeError("7-Zip / NSIS compiler missing")

    with tempfile.TemporaryDirectory(prefix="comedyhost-554-") as work:
        work = Path(work)
        extracted = work / "original"
        run([seven, "x", "-y", "-o" + str(extracted), sources[".exe"]])
        engines = list(extracted.rglob("engine.py"))
        if len(engines) != 1:
            raise RuntimeError("Original installer engine path is ambiguous")
        base = engines[0].parent
        payload = ROOT / "payload"
        if payload.exists():
            raise RuntimeError("Payload already exists; use a fresh checkout")
        shutil.copytree(base, payload)
        shutil.rmtree(payload / "$PLUGINSDIR", ignore_errors=True)
        (payload / "Uninstall.exe").unlink(missing_ok=True)
        for name in ["engine.py", "voice_catalog.json", "trend_us.json", "trend_jp.json",
                     "GOLD_REFERENCE_METRICS_5.5.3.json"]:
            shutil.copy2(ROOT / "app" / name, payload / name)
        # Verify unchanged supporting patch files against the original ZIP bytes.
        with zipfile.ZipFile(sources[".zip"]) as patch:
            for name in ["voice_catalog.json", "trend_us.json", "trend_jp.json"]:
                match = [n for n in patch.namelist() if n.endswith("/" + name)]
                if len(match) != 1 or patch.read(match[0]) != (payload / name).read_bytes():
                    raise RuntimeError("Patch provenance mismatch: " + name)
        for file in list((ROOT / "app").glob("*.py")) + list((ROOT / "tests").glob("*.py")):
            ast.parse(file.read_text(encoding="utf-8-sig"))
        pythons = list(payload.rglob("python.exe"))
        if len(pythons) != 1:
            raise RuntimeError("Bundled Python is missing or ambiguous")
        python_relative = pythons[0].relative_to(payload)
        for test in [ROOT / "app/SELF_TEST_REPEAT_5.5.3e.py",
                     ROOT / "app/SELF_TEST_GPU_5.5.3e.py", ROOT / "tests/test_final_gate.py"]:
            run([pythons[0], test])
        run([compiler, "installer.nsi"], cwd=ROOT / "build")
        exe = DIST / "ComedyHostStudio_Setup_5.5.4.exe"
        if not exe.is_file() or exe.read_bytes()[:2] != b"MZ":
            raise RuntimeError("Real Windows EXE was not produced")
        run([seven, "t", exe])
        verification = work / "verification"
        run([seven, "x", "-y", "-o" + str(verification), exe])
        output_engines = list(verification.rglob("engine.py"))
        if len(output_engines) != 1 or digest(output_engines[0]) != digest(payload / "engine.py"):
            raise RuntimeError("Installer contains wrong engine")

        # Exercise old install -> old uninstall -> new install on the same path.
        target = work / "installed"
        run([sources[".exe"], "/S", "/D=" + str(target)])
        if not (target / "ComedyHostStudio.exe").is_file():
            raise RuntimeError("Beta 5.1 install failed")
        run([target / "Uninstall.exe", "/S", "_?=" + str(target)])
        if (target / "engine.py").exists():
            raise RuntimeError("Old uninstall left engine installed")
        shutil.rmtree(target, ignore_errors=True)
        run([exe, "/S", "/D=" + str(target)])
        for src in payload.rglob("*"):
            if src.is_file():
                dst = target / src.relative_to(payload)
                if not dst.is_file() or digest(src) != digest(dst):
                    raise RuntimeError("Installed payload mismatch: " + str(src.relative_to(payload)))
        run([target / python_relative, target / "engine.py", "--help"], cwd=target)
        run([target / "Uninstall.exe", "/S", "_?=" + str(target)])
        if (target / "engine.py").exists() or (target / "ComedyHostStudio.exe").exists():
            raise RuntimeError("5.5.4 uninstall did not remove application")
        (DIST / "SHA256.txt").write_text(digest(exe) + "  " + exe.name + "\n")
        (DIST / "verification.txt").write_text(
            "PASS source hashes; syntax; anti-repeat and static GPU tests; NSIS compilation; "
            "archive integrity; embedded engine hash; old install/uninstall; new install payload hashes; "
            "bundled Python engine CLI startup; new uninstall.\n"
            "NOT TESTED: RTX 2070 inference, GUI interaction, model downloads, actual video generation.\n")


if __name__ == "__main__":
    main()
