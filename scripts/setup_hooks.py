#!/usr/bin/env python3
"""
setup_hooks.py — Git pre-commit hook'u yükler.

Cross-platform: Windows, Linux, macOS.

Kullanım:
    python3 scripts/setup_hooks.py
"""
import os
import sys
import stat
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR    = PROJECT_ROOT / ".git" / "hooks"

# Linux/macOS hook — bash
HOOK_BASH = """\
#!/bin/bash
# Pre-commit hook — scripts/setup_hooks.py tarafından üretildi

echo "--> Pre-Commit Checks..."

# 1. Clang-Format
if command -v clang-format &>/dev/null; then
    echo "    [1/3] Clang-Format..."
    find . -name "*.cpp" -o -name "*.h" | xargs clang-format --dry-run --Werror 2>&1
else
    echo "    [1/3] clang-format bulunamadı, atlandı."
fi

# 2. CMake Health Check
echo "    [2/3] CMake Health Check..."
cmake -S . -B /tmp/cmake_hook_check -G Ninja > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: CMake configuration failed!"
    rm -rf /tmp/cmake_hook_check
    exit 1
fi
rm -rf /tmp/cmake_hook_check

# 3. Secret Scanner
echo "    [3/3] Secret Scanner..."
if git diff --cached | grep -Ei "API_KEY|SECRET|PASSWORD|-----BEGIN" > /dev/null; then
    echo "ERROR: Potential secret detected in staged changes!"
    exit 1
fi

echo "--> Pre-Commit Checks Passed!"
exit 0
"""

# Windows hook — Python üzerinden çalışır
HOOK_WINDOWS = """\
#!/bin/sh
# Pre-commit hook (Windows compat) — scripts/setup_hooks.py tarafından üretildi
python3 scripts/pre_commit_check.py
"""

PRE_COMMIT_PY = """\
#!/usr/bin/env python3
\"\"\"
pre_commit_check.py — Windows uyumlu pre-commit kontrolleri.
setup_hooks.py tarafından oluşturulur, doğrudan çalıştırılmamalıdır.
\"\"\"
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def check_secrets():
    r = run(["git", "diff", "--cached"])
    keywords = ["API_KEY", "SECRET", "PASSWORD", "-----BEGIN"]
    for kw in keywords:
        if kw in r.stdout:
            print(f"ERROR: Potential secret ({kw}) detected in staged changes!")
            return False
    return True


def check_cmake():
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    r = run(["cmake", "-S", ".", "-B", str(tmp), "-G", "Ninja"])
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        print("ERROR: CMake configuration failed!")
        print(r.stderr)
        return False
    return True


passed = check_secrets() and check_cmake()
print("--> Pre-Commit Checks Passed!" if passed else "--> Pre-Commit Checks FAILED!")
sys.exit(0 if passed else 1)
"""


def main() -> None:
    if not HOOKS_DIR.exists():
        print("Hata: .git/hooks dizini bulunamadı. Proje kökünde misiniz?", file=sys.stderr)
        sys.exit(1)

    is_windows = platform.system() == "Windows"
    hook_path  = HOOKS_DIR / "pre-commit"

    # Hook dosyasını yaz
    hook_content = HOOK_WINDOWS if is_windows else HOOK_BASH
    hook_path.write_text(hook_content, encoding="utf-8")

    # Çalıştırılabilir yap (Linux/macOS)
    if not is_windows:
        mode = hook_path.stat().st_mode
        hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"  ✅ Pre-commit hook yüklendi: {hook_path}")

    # Windows'ta yardımcı Python scripti de yaz
    if is_windows:
        py_path = Path(__file__).resolve().parent / "pre_commit_check.py"
        py_path.write_text(PRE_COMMIT_PY, encoding="utf-8")
        print(f"  ✅ Windows check scripti: {py_path}")

    print("  Kontroller: CMake Health + Secret Scanner")
    print("  clang-format için: Linux/macOS'ta otomatik, Windows'ta manuel kurulum gerekir.")


if __name__ == "__main__":
    main()
