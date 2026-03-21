#!/usr/bin/env python3
"""
build_extension.py — Proje dosyalarını extension/templates/'a kopyalar ve .vsix paketler.

Kullanım:
    python3 scripts/build_extension.py             # kopyala + paketle
    python3 scripts/build_extension.py --install   # + VS Code'a yükle
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXT_DIR      = PROJECT_ROOT / "scripts" / "extension"
TEMPLATE_DIR = EXT_DIR / "templates"

# ── Templates'a kopyalanacaklar ───────────────────────────────────────────────
INCLUDE: list[str] = [
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

# ── Kopyadan hariç tutulacaklar ───────────────────────────────────────────────
EXCLUDE: set[str] = {
    "build", "build_logs", "__pycache__", ".cache", "coverage_report",
    # Extension'ın kendisi (döngüsel)
    "scripts/extension",

    # Dev-only scriptler
    "scripts/sync_to_extension.py",
    #"scripts/run_build_check.py",
    "scripts/run_build_check.sh",
    #"scripts/add_new_lib.py",
    #"scripts/remove_lib.py",
    "scripts/build_extension.py",

    # Geliştirici notları
    "İstekler-Eksikler-Sorunlar.md",
}


def is_excluded(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    return any(rel == ex or rel.startswith(ex + "/") for ex in EXCLUDE)


def sync_templates() -> int:
    """Proje dosyalarını TEMPLATE_DIR'e kopyalar. Kopyalanan dosya sayısını döndürür."""
    if TEMPLATE_DIR.exists():
        shutil.rmtree(TEMPLATE_DIR)
    TEMPLATE_DIR.mkdir(parents=True)

    count = 0
    for entry in INCLUDE:
        src = PROJECT_ROOT / entry
        if not src.exists():
            print(f"  [UYARI] Bulunamadı, atlandı: {entry}")
            continue

        if src.is_file():
            pairs = [(src, entry)]
        else:
            pairs = [
                (p, str(Path(entry) / p.relative_to(src)).replace("\\", "/"))
                for p in src.rglob("*") if p.is_file()
            ]

        for abs_src, rel in pairs:
            if is_excluded(rel):
                continue
            dst = TEMPLATE_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_src, dst)
            count += 1

    return count


def sync_version() -> str:
    """CMakeLists.txt'deki VERSION'ı package.json'a yazar."""
    cmake = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    m = re.search(r'project\s*\([^)]*VERSION\s+([\d.]+)', cmake, re.IGNORECASE)
    if not m:
        print("  [UYARI] CMakeLists.txt'de versiyon bulunamadı.")
        return ""
    version = m.group(1)
    pkg_path = EXT_DIR / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    if pkg.get("version") != version:
        pkg["version"] = version
        pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  ✅ Versiyon güncellendi: {version}")
    else:
        print(f"  ⏭  Versiyon güncel: {version}")
    return version


def sync_license() -> None:
    """LICENSE'ı extension köküne kopyalar (vsce zorunlu kılar)."""
    src = PROJECT_ROOT / "LICENSE"
    dst = EXT_DIR / "LICENSE"
    if src.exists():
        shutil.copy2(src, dst)
        print("  ✅ LICENSE güncellendi")


def run(cmd: list[str], cwd: Path) -> None:
    print(f"  --> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"  ❌ FAILED (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help=".vsix'i VS Code'a yükle")
    args = parser.parse_args()

    print("\n[1/4] Versiyon senkronize ediliyor...")
    sync_version()
    sync_license()

    print("\n[2/4] Template dosyaları kopyalanıyor...")
    count = sync_templates()
    print(f"  ✅ {count} dosya → templates/")

    # Eski .vsix temizle
    for f in PROJECT_ROOT.glob("*.vsix"):
        f.unlink()
        print(f"  🗑  Eski paket silindi: {f.name}")

    print("\n[3/4] npm install...")
    run(["npm", "install"], EXT_DIR)

    print("\n[4/4] vsce package...")
    run(["npx", "vsce", "package", "--out", str(PROJECT_ROOT)], EXT_DIR)

    vsix_files = sorted(PROJECT_ROOT.glob("*.vsix"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not vsix_files:
        print("  ❌ .vsix üretilemedi.", file=sys.stderr)
        sys.exit(1)
    vsix = vsix_files[0]
    print(f"\n  ✅ Paket: {vsix.name}")

    if args.install:
        print("\nVS Code'a yükleniyor...")
        run(["code", "--install-extension", str(vsix)], PROJECT_ROOT)
        print("  ✅ Yüklendi. VS Code'u yeniden başlatın.")


if __name__ == "__main__":
    main()
