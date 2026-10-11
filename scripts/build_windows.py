"""Build a self-contained x64 Windows app and an NSIS installer with public assets only."""

import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from scripts.build_pages import DOCUMENTS

VERSION = "1.1.1"
ROOT = Path(__file__).resolve().parent.parent


def safe_output(path):
    if path.is_symlink() or path.resolve() != path or not path.is_relative_to(ROOT):
        raise ValueError("Build output must stay in its named workspace directory.")
    return path


def make_icon(path):
    """Draw a small DNA mark directly as code; no external bitmap dependency."""
    images = []
    for size in (16, 32, 48, 256):
        pixels = bytearray()
        for y in reversed(range(size)):
            yy = (y + 0.5) / size
            left = 0.5 + 0.18 * math.sin((yy - 0.13) * 10)
            right = 1 - left
            for x in range(size):
                xx = (x + 0.5) / size
                radius = math.hypot(xx - 0.5, yy - 0.5)
                color = (0, 0, 0, 0)
                if radius < 0.46:
                    color = (239, 246, 242, 255) if radius < 0.42 else (183, 202, 199, 255)
                    if 0.15 < yy < 0.85:
                        if min(abs(xx - left), abs(xx - right)) < 0.029:
                            color = (50, 96, 104, 255)
                        elif min(left, right) < xx < max(left, right) and abs((yy - 0.2) * 8 - round((yy - 0.2) * 8)) < 0.09:
                            color = (111, 148, 161, 255)
                pixels.extend((color[2], color[1], color[0], color[3]))
        mask = bytes(((size + 31) // 32) * 4 * size)
        header = struct.pack("<IIIHHIIIIII", 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
        images.append(header + pixels + mask)
    offset = 6 + 16 * len(images)
    entries = []
    for size, image in zip((16, 32, 48, 256), images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(image), offset))
        offset += len(image)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(images))


def verify_bundle(bundle):
    if bundle.is_symlink():
        raise ValueError("Linked bundle roots are not allowed.")
    # Windows TEMP may use a DOS short path while resolve() returns the long path.
    bundle = bundle.resolve()
    private_paths = []
    for path in bundle.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(bundle):
            raise ValueError("Linked or external bundle content is not allowed.")
        if path.name in {".env", ".git", ".idea", "node_modules", ".venv"} or path.suffix == ".iml" or path.name.startswith(".env."):
            private_paths.append(path.relative_to(bundle).as_posix())
    if private_paths:
        raise ValueError("The bundle contains private paths.")
    from dotenv import dotenv_values
    private_key = dotenv_values(ROOT / ".env").get("OPENAI_API_KEY", "")
    if private_key:
        for path in bundle.rglob("*"):
            if path.is_file() and private_key.encode() in path.read_bytes():
                raise ValueError("The bundle contains a private key.")


def nsis_compiler():
    candidates = [os.getenv("NSIS_COMPILER"), shutil.which("makensis"), ROOT / "build/tools/nsis-3.11/makensis.exe", r"C:\Program Files (x86)\NSIS\makensis.exe", r"C:\Program Files\NSIS\makensis.exe"]
    for item in candidates:
        if item and Path(item).is_file():
            return Path(item)
    raise RuntimeError("NSIS is required on the build PC only.")


def build():
    if os.name != "nt" or struct.calcsize("P") != 8:
        raise RuntimeError("Build on 64-bit Windows with Python 3.12.")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use Python 3.12 for the supported Windows build.")
    compiler = nsis_compiler()
    output = safe_output(ROOT / "build" / "windows")
    for name in ("assets", "work", "spec", "dist"):
        safe_output(output / name).mkdir(parents=True, exist_ok=True)
    assets = output / "assets"
    icon = assets / "rei.ico"
    make_icon(icon)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    pyinstaller_distribution = importlib.metadata.distribution("pyinstaller")
    license_files = [file for file in pyinstaller_distribution.files or [] if Path(str(file)).name == "COPYING.txt"]
    if not license_files:
        raise RuntimeError("PyInstaller's redistribution license is missing.")
    pyinstaller_license = Path(pyinstaller_distribution.locate_file(license_files[0]))
    nsis_license = compiler.parent / "COPYING"
    for source, name in ((python_license, "python-runtime-license.txt"), (pyinstaller_license, "pyinstaller-license.txt"), (nsis_license, "nsis-license.txt")):
        if not source.is_file():
            raise RuntimeError("A runtime/installer license text is missing: " + name)
        shutil.copyfile(source, assets / name)
    document_names = (*DOCUMENTS, "index.html")
    for name in document_names:
        path = ROOT / name
        if path.is_symlink() or path.resolve().parent != ROOT or not path.is_file():
            raise ValueError("Public bundle document is missing or linked.")
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
            "--name", "REIResearchExplorer", "--icon", str(icon),
            "--distpath", str(output / "dist"), "--workpath", str(output / "work"), "--specpath", str(output / "spec"),
            "--paths", str(ROOT), "--hidden-import", "uvicorn.loops.asyncio", "--hidden-import", "uvicorn.protocols.http.h11_impl",
            "--hidden-import", "uvicorn.lifespan.on", "--collect-data", "certifi"]
    # Include Python's VC runtime DLLs explicitly, avoiding a prerequisite installer/admin step.
    runtime_dlls = list(Path(sys.base_prefix).glob("vcruntime*.dll"))
    if not runtime_dlls:
        raise RuntimeError("The Python Windows runtime DLLs are missing.")
    for path in runtime_dlls:
        args += ["--add-binary", str(path) + os.pathsep + "."]
    for name in document_names:
        args += ["--add-data", str(ROOT / name) + os.pathsep + "."]
    # Bundle only checked runtime assets, never generated profiles or library data.
    for folder, suffixes in {"assets": {".js", ".css"}, "templates": {".json"},
                             "themes": {".json"}, "prompts/runtime": {".json", ".md"},
                             "schemas": {".json"}, "documentation": {".md"}}.items():
        directory = ROOT / folder
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("Missing or linked runtime asset directory: " + folder)
        for path in sorted(directory.rglob("*")):
            if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("Linked runtime asset rejected.")
            if path.is_file() and path.suffix in suffixes:
                args += ["--add-data", str(path) + os.pathsep + str(path.parent.relative_to(ROOT))]
    args += ["--hidden-import", "sqlite3", "--hidden-import", "_sqlite3"]
    for path in sorted((ROOT / "licenses").glob("*.txt")):
        if path.is_symlink() or path.resolve().parent != ROOT / "licenses":
            raise ValueError("Linked dependency license rejected.")
        args += ["--add-data", str(path) + os.pathsep + "licenses"]
    for path in assets.glob("*-license.txt"):
        args += ["--add-data", str(path) + os.pathsep + "licenses"]
    args += ["--add-data", str(icon) + os.pathsep + "installer",
             "--add-data", str(ROOT / "installer" / "INSTALLATION.txt") + os.pathsep + ".",
             str(ROOT / "installer" / "desktop.py")]
    subprocess.run(args, cwd=ROOT, check=True)
    bundle = safe_output(output / "dist" / "REIResearchExplorer")
    verify_bundle(bundle)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "source checkout"
    manifest = {"version": VERSION, "source_commit": commit, "python": sys.version.split()[0],
                "architecture": "x64", "pyinstaller": importlib.metadata.version("pyinstaller"),
                "nsis": subprocess.check_output([str(compiler), "/VERSION"], text=True).strip(),
                "private_files_included": False}
    (bundle / "BUILD-INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # The uninstaller removes only known packaged files; it never recursively deletes a user's folder.
    uninstall = assets / "uninstall-files.nsh"
    lines = ['Delete "$INSTDIR\\' + str(p.relative_to(bundle)).replace('$', '$$') + '"' for p in sorted(bundle.rglob("*")) if p.is_file()]
    directories = sorted((p for p in bundle.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    lines += ['RMDir "$INSTDIR\\' + str(p.relative_to(bundle)).replace('$', '$$') + '"' for p in directories]
    uninstall.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    setup = safe_output(ROOT / "dist" / f"OpenBEXIDiscovery-{VERSION}-Windows-x64-Setup.exe")
    setup.parent.mkdir(exist_ok=True)
    subprocess.run([str(compiler), "/DBUNDLE=" + str(bundle), "/DOUTPUT=" + str(setup), "/DICON=" + str(icon),
                    "/DUNINSTALL_FILES=" + str(uninstall), "/DVERSION=" + VERSION, str(ROOT / "installer" / "windows.nsi")], check=True)
    checksum = hashlib.sha256(setup.read_bytes()).hexdigest()
    (setup.parent / "SHA256SUMS-Windows.txt").write_text(checksum + "  " + setup.name + "\n", encoding="ascii")
    print("Windows installer built: " + setup.name)
    return setup


if __name__ == "__main__":
    build()
