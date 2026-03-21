#!/usr/bin/env python3
"""
remove_lib.py — Projeden bir kütüphaneyi kaldırır.

Kullanım:
    python3 scripts/remove_lib.py --name math_utils           # Bağımlılıkları kaldır, dosyaları koru
    python3 scripts/remove_lib.py --name math_utils --delete  # + dosyaları da sil
    python3 scripts/remove_lib.py --name math_utils --dry-run # Sadece ne yapacağını göster
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Korumalı lib'ler silinemez/kaldırılamaz
PROTECTED_LIBS = {"dummy_lib"}


# ──────────────────────────────────────────────────────────────────────────────
# CMake yardımcıları
# ──────────────────────────────────────────────────────────────────────────────

def _remove_subdirectory_line(cmake_path: Path, name: str) -> bool:
    """add_subdirectory(<n>) satırını kaldırır. True → değişti."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf'^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*\n?', re.MULTILINE
    )
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    cmake_path.write_text(new_content, encoding="utf-8")
    return True


def _remove_link_from_target(cmake_path: Path, name: str) -> bool:
    """target_link_libraries bloğundan <n> satırını kaldırır. True → değişti."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    pattern = re.compile(rf'^\s+{re.escape(name)}\s*\n', re.MULTILINE)
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    cmake_path.write_text(new_content, encoding="utf-8")
    return True


def _contains_reference(cmake_path: Path, name: str) -> bool:
    """Dosyada hâlâ lib'e referans var mı?"""
    if not cmake_path.exists():
        return False
    return name in cmake_path.read_text(encoding="utf-8")


def _find_app_cmake_files() -> list[Path]:
    return list((PROJECT_ROOT / "apps").rglob("CMakeLists.txt"))


# ──────────────────────────────────────────────────────────────────────────────
# Referans doğrulama
# ──────────────────────────────────────────────────────────────────────────────

def _verify_no_references(name: str) -> list[str]:
    """
    Projede hâlâ bu lib'e referans veren CMake dosyalarını döndürür.
    Boş liste → temiz.
    """
    dirty: list[str] = []
    check_files = [
        PROJECT_ROOT / "libs" / "CMakeLists.txt",
        PROJECT_ROOT / "tests" / "unit" / "CMakeLists.txt",
        *_find_app_cmake_files(),
    ]
    for f in check_files:
        if _contains_reference(f, name):
            dirty.append(str(f.relative_to(PROJECT_ROOT)))
    return dirty


# ──────────────────────────────────────────────────────────────────────────────
# Ana işlem
# ──────────────────────────────────────────────────────────────────────────────

def remove_lib(name: str, delete: bool, dry_run: bool) -> None:
    mode = "KRU ÇALIŞMA" if dry_run else ("SİLME DAHİL" if delete else "SADECE BAĞIMLILIK")
    print(f"\n=== remove_lib: {name} [{mode}] ===\n")

    if name in PROTECTED_LIBS:
        print(f"  ❌ '{name}' korumalı bir kütüphanedir, kaldırılamaz.", file=sys.stderr)
        sys.exit(1)

    lib_dir  = PROJECT_ROOT / "libs" / name
    test_dir = PROJECT_ROOT / "tests" / "unit" / name

    if not lib_dir.exists():
        print(f"  ❌ libs/{name}/ bulunamadı.", file=sys.stderr)
        sys.exit(1)

    actions: list[str] = []

    # ── 1. libs/CMakeLists.txt ──
    cmake_libs = PROJECT_ROOT / "libs" / "CMakeLists.txt"
    if dry_run:
        if _contains_reference(cmake_libs, name):
            actions.append(f"  ~ libs/CMakeLists.txt → add_subdirectory({name}) kaldırılacak")
    else:
        changed = _remove_subdirectory_line(cmake_libs, name)
        actions.append(f"  {'✅' if changed else '⏭ '} libs/CMakeLists.txt → add_subdirectory({name})")

    # ── 2. tests/unit/CMakeLists.txt ──
    cmake_unit = PROJECT_ROOT / "tests" / "unit" / "CMakeLists.txt"
    if test_dir.exists():
        if dry_run:
            if _contains_reference(cmake_unit, name):
                actions.append(f"  ~ tests/unit/CMakeLists.txt → add_subdirectory({name}) kaldırılacak")
        else:
            changed = _remove_subdirectory_line(cmake_unit, name)
            actions.append(f"  {'✅' if changed else '⏭ '} tests/unit/CMakeLists.txt → add_subdirectory({name})")

    # ── 3. App bağımlılıkları ──
    for app_cmake in _find_app_cmake_files():
        rel = app_cmake.relative_to(PROJECT_ROOT)
        if _contains_reference(app_cmake, name):
            if dry_run:
                actions.append(f"  ~ {rel} → {name} bağımlılığı kaldırılacak")
            else:
                changed = _remove_link_from_target(app_cmake, name)
                actions.append(f"  {'✅' if changed else '⏭ '} {rel} → {name} bağımlılığı")

    for a in actions:
        print(a)

    # ── 4. Silme öncesi doğrulama ──
    if delete and not dry_run:
        print()
        dirty = _verify_no_references(name)
        if dirty:
            print("  ❌ DOSYALAR SİLİNMEDİ — hâlâ referans bulunan CMake dosyaları:", file=sys.stderr)
            for f in dirty:
                print(f"     • {f}", file=sys.stderr)
            print(
                "\n  Manuel temizleyip tekrar çalıştırın ya da --delete olmadan çalıştırın.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Doğrulama geçti → sil
        for d, label in [(lib_dir, f"libs/{name}/"), (test_dir, f"tests/unit/{name}/")]:
            if d.exists():
                shutil.rmtree(d)
                print(f"  ✅ {label} silindi")
            else:
                print(f"  ⏭  {label} zaten yok")

    elif delete and dry_run:
        print(f"  - libs/{name}/ SİLİNECEK")
        if test_dir.exists():
            print(f"  - tests/unit/{name}/ SİLİNECEK")
    else:
        print(f"\n  ℹ️  Dosyalar korundu (silmek için --delete ekle)")

    # ── 5. Özet ──
    if dry_run:
        print(f"\n  → Uygulamak için: python3 scripts/remove_lib.py --name {name}" +
              (" --delete" if delete else ""))
    else:
        print(f"\n  Sonraki adım: bash scripts/run_build_check.sh")


def main() -> None:
    parser = argparse.ArgumentParser(description="Projeden bir kütüphaneyi kaldırır.")
    parser.add_argument("--name",    required=True,       help="Kaldırılacak kütüphane adı")
    parser.add_argument("--delete",  action="store_true", help="Dosyaları da sil (libs/ ve tests/unit/)")
    parser.add_argument("--dry-run", action="store_true", help="Sadece ne yapacağını göster")
    args = parser.parse_args()
    remove_lib(args.name, args.delete, args.dry_run)


if __name__ == "__main__":
    main()
