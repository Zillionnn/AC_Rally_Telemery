"""Build the single-file client, and verify the bundle before packaging.

Kept as a script rather than a shell one-liner because Git Bash rewrites
arguments that contain '=' (the --include-data-dir=SRC=DST form), which
silently dropped the Qt plugin directories and produced an exe that could not
start. A Python argument list cannot be rewritten.

Usage:
    python acr_build.py check       # standalone build, then assert bundle files
    python acr_build.py onefile     # the shipped single exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".build_venv" / "Scripts" / "python.exe"
SITE = ROOT / ".build_venv" / "Lib" / "site-packages"
SP = str(SITE).replace("\\", "/")

COMMON = [
    "--assume-yes-for-downloads",
    "--windows-console-mode=disable",
    "--windows-file-version=0.3.8.0",
    "--windows-product-version=0.3.8.0",
    "--product-name=ACR Telemetry",
    "--file-description=ACR Telemetry Studio",
    "--company-name=ACRallyRec",
    "--windows-icon-from-ico=assets/acr.ico",
    "acr_desktop.py",
]


def data_args() -> list[str]:
    """Every file the frozen app needs that static analysis cannot find."""
    args = [
        # without this Nuitka bundles no Qt platform plugin at all and the exe
        # dies with "no Qt platform plugin could be initialized"
        "--enable-plugin=pyside6",
    ]
    args += [
        f"--include-data-files={p}={p}"
        for p in ("pacenotes/pacenotes.json", "pacenotes/ACR_Pacenote.usmap")
    ]
    args += [
        "--include-package=windows_capture",
        "--include-package=av",
        "--include-package-data=av",
        "--include-package=pyaudiowpatch",
        "--include-package=cv2",
        # pyqtgraph imports these with importlib, so Nuitka cannot see them
        "--include-module=PySide6.QtOpenGL",
        "--include-module=PySide6.QtOpenGLWidgets",
        "--include-module=PySide6.QtSvg",
    ]
    # NOTE: --include-data-dir cannot deliver Qt plugins: Nuitka treats .dll as
    # code and reports "No data files in directory". --enable-plugin=pyside6
    # above is what actually bundles them, under PySide6/qt-plugins/.
    return args


def run(mode: str, output_dir: str,
        output_filename: str | None = None) -> int:
    cmd = [str(VENV), "-m", "nuitka", mode, f"--output-dir={output_dir}"]
    if output_filename:
        # only for the shipped exe: naming the standalone would rename its
        # dist folder, which the check mode relies on
        cmd.append(f"--output-filename={output_filename}")
    cmd += data_args() + COMMON
    print(" ".join(cmd[:8]), "...", flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


REQUIRED = (
    "PySide6/qt-plugins/platforms/qwindows.dll",
    "PySide6/QtWidgets.pyd",
    "windows_capture/windows_capture.pyd",
    "av/_core.pyd",
    "_portaudiowpatch.pyd",
    "pacenotes/pacenotes.json",
)


def verify(dist: Path) -> bool:
    ok = True
    for rel in REQUIRED:
        path = dist / rel
        exists = path.exists()
        print(("  ok   " if exists else "  MISS") + f" {rel}"
              + ("" if exists else f"   (looked in {path})"))
        ok = ok and exists
    return ok


def main() -> int:
    if not VENV.exists():
        print(f"build venv missing: {VENV}")
        return 2
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "check":
        dist = ROOT / "build_check" / "acr_desktop.dist"
        if run("--standalone", "build_check") != 0:
            return 1
        if not dist.exists():
            print("dist folder not produced:", dist)
            return 1
        print("bundle contents:")
        good = verify(dist)
        print("CHECK:", "PASS" if good else "FAIL")
        return 0 if good else 1
    if mode == "onefile":
        exe = ROOT / "build_exe" / "ACR Telemetry.exe"
        if run("--onefile", "build_exe", "ACR Telemetry.exe") != 0:
            return 1
        if not exe.exists():
            print("exe not produced")
            return 1
        print(f"built {exe} {exe.stat().st_size / 1048576:.1f} MB")
        return 0
    print("usage: python acr_build.py [check|onefile]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
