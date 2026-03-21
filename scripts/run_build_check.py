#!/usr/bin/env python3
"""
run_build_check.py — Configure + Build + Test + Extension Sync

Cross-platform (Windows/Linux/macOS).

Kullanım:
    python3 scripts/run_build_check.py
    python3 scripts/run_build_check.py --preset clang-debug-static-x86_64
    python3 scripts/run_build_check.py --no-sync
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "build_logs"

DEFAULT_PRESET = {
    "Linux":   "gcc-debug-static-x86_64",
    "Windows": "msvc-debug-static-x64",
    "Darwin":  "clang-debug-static-x86_64",
}


def run(cmd: list[str], log_file: Path) -> None:
    print(f"--> {' '.join(cmd)}")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as f:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        f.write(result.stdout)
        print(result.stdout, end="")
    if result.returncode != 0:
        print(f"\n❌ FAILED (exit {result.returncode}) — log: {log_file}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build + Test + Sync")
    parser.add_argument("--preset", default=None, help="CMake preset adı")
    parser.add_argument("--no-sync", action="store_true", help="Extension sync'i atla")
    args = parser.parse_args()

    preset = args.preset or DEFAULT_PRESET.get(platform.system(), "gcc-debug-static-x86_64")

    print("=" * 48)
    print(f"  CppCmakeProjectTemplate Build Check")
    print(f"  Preset : {preset}")
    print(f"  Root   : {PROJECT_ROOT}")
    print("=" * 48)

    # 1. Configure
    print("\n[1/4] CMake Configure...")
    run(["cmake", "--preset", preset], LOG_DIR / "configure.log")
    print("✅ Configure OK")

    # 2. Build
    print("\n[2/4] CMake Build...")
    run(["cmake", "--build", "--preset", preset], LOG_DIR / "build.log")
    print("✅ Build OK")

    # 3. Test
    print("\n[3/4] CTest...")
    run(["ctest", "--preset", preset, "--output-on-failure"], LOG_DIR / "test.log")
    print("✅ Tests OK")

    # 4. Extension bundle yenile
    if not args.no_sync:
        print("\n[4/4] Extension bundle yenileniyor...")
        bundle_script = PROJECT_ROOT / "scripts" / "build_extension.py"
        run([sys.executable, str(bundle_script)], LOG_DIR / "bundle.log")
        print("✅ Bundle OK")

    print("\n" + "=" * 48)
    print("✅ Tüm adımlar başarılı!")
    print(f"   Loglar: {LOG_DIR}/")
    print("=" * 48)


if __name__ == "__main__":
    main()
