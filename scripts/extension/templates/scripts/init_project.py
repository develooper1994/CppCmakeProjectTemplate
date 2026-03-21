#!/usr/bin/env python3
"""
init_project.py — CppCmakeProjectTemplate proje renamer.

Kullanım:
    python3 scripts/init_project.py --name MyAwesomeProject
"""
import os
import sys
import argparse
import re

# CMake/C++ uyumlu isim: harf/rakam/alt çizgi, rakamla başlamaz
_VALID_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# Text dosyası olarak işlenecek uzantılar (binary'ler atlanır)
_TEXT_EXTENSIONS = {
    '.txt', '.cmake', '.json', '.py', '.md', '.yml', '.yaml',
    '.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx', '.in',
    '.sh', '.bat', '.ps1', '.toml', '.cfg', '.ini', '.xml',
    '.js', '.ts', '.qml', '.gitignore', '.clang-format',
    '.dockerignore', '.geminiignore', '.mdc',
}

# Atlanacak dizinler
_SKIP_DIRS = {'.git', 'build', '.cache', 'coverage_report', '__pycache__', '.venv'}


def is_text_file(path: str) -> bool:
    """Uzantıya göre text dosyası mı karar ver."""
    _, ext = os.path.splitext(path)
    if ext in _TEXT_EXTENSIONS:
        return True
    # Uzantısız dosyalar: küçük bir probe ile binary mi kontrol et
    if ext == '':
        try:
            with open(path, 'rb') as f:
                chunk = f.read(512)
            return b'\x00' not in chunk  # null byte → binary
        except OSError:
            return False
    return False


def rename_project(old_name: str, new_name: str) -> None:
    print(f"--> '{old_name}' → '{new_name}' rename işlemi başlatılıyor...")
    changed = 0

    for root, dirs, files in os.walk('.', topdown=True):
        # Skip dirs in-place (modifying dirs[:] affects os.walk)
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]

        for file in files:
            if file == 'init_project.py' or file.endswith('.pyc'):
                continue

            file_path = os.path.join(root, file)

            if not is_text_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                if old_name in content:
                    new_content = content.replace(old_name, new_name)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"    Güncellendi: {file_path}")
                    changed += 1

            except OSError as e:
                print(f"    [UYARI] {file_path} işlenemedi: {e}", file=sys.stderr)

    print(f"--> Tamamlandı. {changed} dosya güncellendi.")
    print("    Not: LICENSE dosyasını manuel olarak güncellemeyi unutmayın.")
    print(f"    Not: Dizin adını da yeniden adlandırmak istiyorsanız:")
    print(f"         mv ../{old_name} ../{new_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CppCmakeProjectTemplate projesini yeniden adlandırır."
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Yeni proje adı (CMake uyumlu: harf/rakam/alt çizgi, rakamla başlayamaz)"
    )
    parser.add_argument(
        "--old-name",
        default="CppCmakeProjectTemplate",
        help="Eski proje adı (default: CppCmakeProjectTemplate)"
    )
    args = parser.parse_args()

    if not _VALID_NAME_RE.match(args.name):
        print(
            f"Hata: '{args.name}' geçersiz proje adı.\n"
            "CMake uyumlu isim: sadece harf, rakam ve alt çizgi; rakamla başlayamaz.\n"
            "Örnek: MyProject, my_project_2",
            file=sys.stderr
        )
        sys.exit(1)

    if args.name == args.old_name:
        print("Hata: Yeni isim eski isimle aynı.", file=sys.stderr)
        sys.exit(1)

    rename_project(args.old_name, args.name)


if __name__ == "__main__":
    main()
