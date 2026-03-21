#!/usr/bin/env python3
"""
add_new_lib.py — Projeye dummy_lib kalıbına uygun yeni bir kütüphane ekler.

Kullanım:
    python3 scripts/add_new_lib.py --name math_utils
    python3 scripts/add_new_lib.py --name math_utils --version 1.0.0 --namespace myns

Ne yapar:
    - libs/<name>/ iskeletini oluşturur (CMakeLists.txt, include, src, README)
    - tests/unit/<name>/ test iskeletini oluşturur
    - libs/CMakeLists.txt'e add_subdirectory ekler
    - tests/unit/CMakeLists.txt'e add_subdirectory ekler
    - apps/main_app/CMakeLists.txt'e bağımlılık EKLEMEZ (isteğe bağlı, --link-app ile)
"""

import argparse
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VALID_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')


# ──────────────────────────────────────────────────────────────────────────────
# Şablonlar
# ──────────────────────────────────────────────────────────────────────────────

def _lib_cmakelists(name: str, version: str, namespace: str) -> str:
    upper = name.upper()
    return f"""\
# libs/{name}/CMakeLists.txt

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project({name} VERSION {version} LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_SOURCE_DIR}}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)
endif()

include(GenerateExportHeader)

add_library({name})

target_generate_build_info({name}
    NAMESPACE {namespace}
    PROJECT_VERSION "{version}"
)

target_sources({name}
    PRIVATE src/{name}.cpp
    PUBLIC FILE_SET HEADERS BASE_DIRS include
           FILES include/{name}/{name}.h
)

generate_export_header({name}
    BASE_NAME {upper}
    EXPORT_FILE_NAME "${{CMAKE_CURRENT_BINARY_DIR}}/generated/{name}/{name}_export.h"
)

target_include_directories({name} PUBLIC
    $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>
    $<BUILD_INTERFACE:${{CMAKE_CURRENT_BINARY_DIR}}/generated>
    $<INSTALL_INTERFACE:include>
)

set_target_properties({name} PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

if(ENABLE_COVERAGE)     enable_code_coverage({name})         endif()
if(COMMAND enable_sanitizers)    enable_sanitizers({name})    endif()
if(COMMAND set_project_warnings) set_project_warnings({name}) endif()

install(TARGETS {name} EXPORT {name}_Targets FILE_SET HEADERS)
"""


def _lib_header(name: str, namespace: str) -> str:
    upper = name.upper()
    return f"""\
#pragma once

#include <string>
#include "{name}/{name}_export.h"

namespace {namespace} {{

{upper}_EXPORT std::string get_info();

}} // namespace {namespace}
"""


def _lib_source(name: str, namespace: str) -> str:
    return f"""\
#include "{name}/{name}.h"

namespace {namespace} {{

std::string get_info()
{{
    return "Hello from {name}!";
}}

}} // namespace {namespace}
"""


def _lib_readme(name: str) -> str:
    return f"""\
# {name}

TODO: Bu kütüphanenin ne yaptığını açıkla.

## Kullanım

```cpp
#include <{name}/{name}.h>

auto info = {name}::get_info();
```
"""


def _test_cmakelists(name: str) -> str:
    return f"""\
add_executable({name}_tests {name}_test.cpp)

target_link_libraries({name}_tests
    PRIVATE
        {name}
        GTest::gtest_main
)

set_project_warnings({name}_tests)

add_test(NAME {name}_tests COMMAND {name}_tests)
"""


def _test_source(name: str, namespace: str) -> str:
    return f"""\
#include <gtest/gtest.h>
#include "{name}/{name}.h"

TEST({name}_Test, GetInfoReturnsNonEmptyString)
{{
    EXPECT_FALSE({namespace}::get_info().empty());
}}

TEST({name}_Test, GetInfoContainsLibName)
{{
    EXPECT_NE({namespace}::get_info().find("{name}"), std::string::npos);
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# CMakeLists.txt düzenleyici
# ──────────────────────────────────────────────────────────────────────────────

def _append_subdirectory(cmake_path: Path, subdir: str) -> bool:
    """add_subdirectory(subdir) satırı yoksa dosyanın sonuna ekler. True → değişti."""
    content = cmake_path.read_text(encoding="utf-8")
    line = f"add_subdirectory({subdir})"
    if line in content:
        return False
    # Boş satır bırak
    sep = "\n" if content.endswith("\n") else "\n\n"
    cmake_path.write_text(content + sep + line + "\n", encoding="utf-8")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# main_app bağlama (isteğe bağlı)
# ──────────────────────────────────────────────────────────────────────────────

def _link_to_main_app(name: str) -> bool:
    """apps/main_app/CMakeLists.txt içindeki target_link_libraries bloğuna ekler."""
    cmake_path = PROJECT_ROOT / "apps" / "main_app" / "CMakeLists.txt"
    content = cmake_path.read_text(encoding="utf-8")
    if name in content:
        print(f"  [UYARI] {name} zaten main_app'e bağlı, atlanıyor.")
        return False
    # "dummy_lib" satırının altına ekle (varsa), yoksa blok içine ekle
    if "dummy_lib" in content:
        content = content.replace(
            "        dummy_lib \n",
            f"        dummy_lib \n        {name} \n",
            1,
        )
        # Whitespace farklıysa dene
        if name not in content:
            content = re.sub(
                r"(target_link_libraries\(main_app[^)]+PRIVATE\s*\n)([ \t]+dummy_lib)",
                rf"\1\2\n        {name}",
                content,
            )
    cmake_path.write_text(content, encoding="utf-8")
    return name in cmake_path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Asıl işlem
# ──────────────────────────────────────────────────────────────────────────────

def create_lib(name: str, version: str, namespace: str, link_app: bool) -> None:
    if not _VALID_NAME_RE.match(name):
        print(
            f"Hata: '{name}' geçersiz isim.\n"
            "Sadece küçük harf, rakam, alt çizgi; harf ile başlamalı.\n"
            "Örnek: math_utils, image_proc",
            file=sys.stderr,
        )
        sys.exit(1)

    lib_dir   = PROJECT_ROOT / "libs" / name
    test_dir  = PROJECT_ROOT / "tests" / "unit" / name

    if lib_dir.exists():
        print(f"Hata: {lib_dir} zaten mevcut.", file=sys.stderr)
        sys.exit(1)

    # ── Lib iskelet ──
    (lib_dir / "src").mkdir(parents=True)
    (lib_dir / "include" / name).mkdir(parents=True)
    (lib_dir / "docs").mkdir()

    (lib_dir / "CMakeLists.txt").write_text(_lib_cmakelists(name, version, namespace), encoding="utf-8")
    (lib_dir / "include" / name / f"{name}.h").write_text(_lib_header(name, namespace), encoding="utf-8")
    (lib_dir / "src" / f"{name}.cpp").write_text(_lib_source(name, namespace), encoding="utf-8")
    (lib_dir / "README.md").write_text(_lib_readme(name), encoding="utf-8")
    print(f"  ✅ libs/{name}/ oluşturuldu")

    # ── Test iskelet ──
    test_dir.mkdir(parents=True)
    (test_dir / "CMakeLists.txt").write_text(_test_cmakelists(name), encoding="utf-8")
    (test_dir / f"{name}_test.cpp").write_text(_test_source(name, namespace), encoding="utf-8")
    print(f"  ✅ tests/unit/{name}/ oluşturuldu")

    # ── libs/CMakeLists.txt ──
    libs_cmake = PROJECT_ROOT / "libs" / "CMakeLists.txt"
    changed = _append_subdirectory(libs_cmake, name)
    print(f"  {'✅' if changed else '⏭ '} libs/CMakeLists.txt → add_subdirectory({name})")

    # ── tests/unit/CMakeLists.txt ──
    unit_cmake = PROJECT_ROOT / "tests" / "unit" / "CMakeLists.txt"
    changed = _append_subdirectory(unit_cmake, name)
    print(f"  {'✅' if changed else '⏭ '} tests/unit/CMakeLists.txt → add_subdirectory({name})")

    # ── Opsiyonel: main_app bağlama ──
    if link_app:
        ok = _link_to_main_app(name)
        print(f"  {'✅' if ok else '❌'} apps/main_app/CMakeLists.txt → {name} bağlandı")

    print(f"\n  Sonraki adım:")
    print(f"    bash scripts/run_build_check.sh")
    if not link_app:
        print(f"\n  main_app'e bağlamak için:")
        print(f"    python3 scripts/add_new_lib.py --name {name} --link-app   (ya da manuel ekle)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Projeye yeni kütüphane ekler.")
    parser.add_argument("--name",      required=True,          help="Kütüphane adı (küçük harf, alt çizgi)")
    parser.add_argument("--version",   default="1.0.0",        help="Versiyon (default: 1.0.0)")
    parser.add_argument("--namespace", default=None,           help="C++ namespace (default: lib adıyla aynı)")
    parser.add_argument("--link-app",  action="store_true",    help="main_app'e otomatik bağla")
    args = parser.parse_args()

    namespace = args.namespace or args.name
    print(f"\n=== Yeni kütüphane: {args.name} (namespace: {namespace}, v{args.version}) ===\n")
    create_lib(args.name, args.version, namespace, args.link_app)


if __name__ == "__main__":
    main()
