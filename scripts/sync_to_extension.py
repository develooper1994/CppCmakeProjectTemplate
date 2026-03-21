#!/usr/bin/env python3
"""
sync_to_extension.py — Proje dosyalarını VSCode extension templates/ dizinine senkronize eder.

Kullanım:
    python3 scripts/sync_to_extension.py          # Kuru çalıştırma (ne değişeceğini göster)
    python3 scripts/sync_to_extension.py --apply  # Gerçekten uygula
"""
import os
import sys
import shutil
import argparse
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / ".vscode" / "extension" / "templates"

# Kaynak'tan template'e kopyalanacak dosya ve dizinler
# (proje kökündeki yol → template'deki aynı yol)
SYNC_INCLUDE: list[str] = [
    "CMakeLists.txt",
    "CMakePresets.json",
    "conanfile.py",
    "vcpkg.json",
    "Dockerfile",
    ".dockerignore",
    ".gitignore",
    ".geminiignore",
    ".clang-format",
    "LICENSE",
    "README.md",
    "AGENTS.md",
    "GEMINI.md",
    "MASTER_GENERATOR_PROMPT.md",
    # Dizinler
    "cmake",
    "apps",
    "libs",
    "tests",
    "scripts",
    "docs",
    "external",
    ".github",
    ".cursor",
]

# Bu yollar kopyalamadan HARİÇ tutulur (glob-style suffix match)
SYNC_EXCLUDE: set[str] = {
    # Geçici/build çıktıları
    "build",
    "build_logs",
    "__pycache__",
    ".cache",
    "coverage_report",
    # Extension'ın kendi dosyaları (döngüsel kopya önlemi)
    ".vscode/extension",
    # Dev-only scriptler — template kullanıcısının işi değil
    "scripts/sync_to_extension.py",
    "scripts/run_build_check.py",
    "scripts/add_new_lib.py",
    "scripts/remove_lib.py",
    "scripts/build_extension.py",
    # Geliştirici notları
    "İstekler-Eksikler-Sorunlar.md",
}


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_excluded(rel: str) -> bool:
    rel_norm = rel.replace("\\", "/")
    for ex in SYNC_EXCLUDE:
        if rel_norm == ex or rel_norm.startswith(ex + "/"):
            return True
    return False


def sync(apply: bool) -> None:
    added = modified = skipped = deleted = 0
    actions: list[str] = []

    # --- Kaynak → Template (copy/update) ---
    for entry in SYNC_INCLUDE:
        src = PROJECT_ROOT / entry
        if not src.exists():
            print(f"  [UYARI] Kaynak bulunamadı, atlanıyor: {entry}")
            continue

        if src.is_file():
            paths = [(src, Path(entry))]
        else:
            paths = [
                (p, Path(entry) / p.relative_to(src))
                for p in src.rglob("*")
                if p.is_file()
            ]

        for src_file, rel in paths:
            rel_str = str(rel).replace("\\", "/")
            if _is_excluded(rel_str):
                continue

            dst_file = TEMPLATE_DIR / rel
            if not dst_file.parent.exists():
                if apply:
                    dst_file.parent.mkdir(parents=True, exist_ok=True)

            if not dst_file.exists():
                actions.append(f"  + EKLE    {rel_str}")
                added += 1
                if apply:
                    shutil.copy2(src_file, dst_file)
            elif _file_hash(src_file) != _file_hash(dst_file):
                actions.append(f"  ~ GÜNCELLE {rel_str}")
                modified += 1
                if apply:
                    shutil.copy2(src_file, dst_file)
            else:
                skipped += 1

    # --- Template'de fazladan olan dosyaları sil ---
    if TEMPLATE_DIR.exists():
        sync_roots = {entry.split("/")[0] for entry in SYNC_INCLUDE}
        for dst_file in TEMPLATE_DIR.rglob("*"):
            if not dst_file.is_file():
                continue
            rel = dst_file.relative_to(TEMPLATE_DIR)
            rel_str = str(rel).replace("\\", "/")
            # Bu dosyanın sync kapsamında olup olmadığını kontrol et
            root = rel_str.split("/")[0]
            if root not in sync_roots:
                continue  # Sync kapsamı dışı, dokunma
            # Karşılık gelen kaynak var mı?
            src_file = PROJECT_ROOT / rel
            if not src_file.exists() or _is_excluded(rel_str):
                actions.append(f"  - SİL     {rel_str}")
                deleted += 1
                if apply:
                    dst_file.unlink()

    # --- Rapor ---
    mode = "UYGULANDI" if apply else "KRU ÇALIŞMA (--apply ile uygula)"
    print(f"\n=== Sync Raporu [{mode}] ===")
    if actions:
        for a in sorted(actions):
            print(a)
    else:
        print("  Değişiklik yok — template güncel.")

    print(f"\n  + Eklenen : {added}")
    print(f"  ~ Değişen : {modified}")
    print(f"  - Silinen : {deleted}")
    print(f"  = Aynı    : {skipped}")

    if not apply and (added + modified + deleted) > 0:
        print("\n  → Uygulamak için: python3 scripts/sync_to_extension.py --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proje → Extension template sync")
    parser.add_argument("--apply", action="store_true", help="Değişiklikleri gerçekten uygula")
    args = parser.parse_args()
    sync(apply=args.apply)
