"""
core/generator/cmake_targets.py — Per-library and per-app CMakeLists generators.

Generates from [[project.libs]] and [[project.apps]] in tool.toml:
  - libs/<name>/CMakeLists.txt
  - apps/<name>/CMakeLists.txt
  - tests/unit/<name>/CMakeLists.txt
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext


# ---------------------------------------------------------------------------
# Library CMakeLists.txt generator
# ---------------------------------------------------------------------------

def _gen_lib_cmake(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    NAME_UPPER = name.upper()
    lib_type = lib.get("type", "normal")
    is_header_only = lib_type == "header-only" or lib_type == "interface"
    has_export = lib.get("export", False)
    has_benchmarks = lib.get("benchmarks", False)
    has_fuzz = lib.get("fuzz", False)
    deps = lib.get("deps", [])
    cxx_override = lib.get("cxx_standard", "")
    cmake_min = ctx.cmake_minimum

    parts: list[str] = []

    # Stand-alone build support
    parts.append(f"""\
# libs/{name}/CMakeLists.txt

# --- Stand-alone Build Support ---
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION {cmake_min})
    project({name} LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_SOURCE_DIR}}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)
{"    include(Fuzzing OPTIONAL)" if has_fuzz else ""}
endif()
""")

    if has_export and not is_header_only:
        parts.append("include(GenerateExportHeader)\n")

    # Per-library C++ standard override
    if cxx_override:
        parts.append(f'''\
set({NAME_UPPER}_CXX_STANDARD "" CACHE STRING
    "C++ standard for {name} only (empty = inherit solution default)")
''')

    # Library target
    if is_header_only:
        parts.append(f"add_library({name} INTERFACE)\n")
    else:
        parts.append(f"add_library({name})\n")

    # Sources
    if not is_header_only:
        parts.append(f"""\
target_sources({name}
    PRIVATE
        src/{name}.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/{name}/{name}.h)
""")

    # Export header
    if has_export and not is_header_only:
        parts.append(f"""\
generate_export_header({name}
    BASE_NAME {NAME_UPPER}
    EXPORT_FILE_NAME "${{CMAKE_CURRENT_BINARY_DIR}}/generated/{name}/{name}_export.h")
""")

    # Include dirs
    visibility = "INTERFACE" if is_header_only else "PUBLIC"
    parts.append(f"""\
target_include_directories({name}
    {visibility}
        $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>
        $<BUILD_INTERFACE:${{CMAKE_CURRENT_BINARY_DIR}}/generated>
        $<INSTALL_INTERFACE:include>)
""")

    # Visibility settings
    if not is_header_only:
        if cxx_override:
            parts.append(f"""\
if({NAME_UPPER}_CXX_STANDARD AND NOT {NAME_UPPER}_CXX_STANDARD STREQUAL "")
    set_target_properties({name} PROPERTIES
        CXX_STANDARD          ${{{NAME_UPPER}_CXX_STANDARD}}
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS        OFF
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1)
else()
    set_target_properties({name} PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1)
endif()
""")
        else:
            parts.append(f"""\
set_target_properties({name} PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1)
""")

    # Dependencies
    if deps:
        dep_list = "\n        ".join(deps)
        parts.append(f"""\
target_link_libraries({name}
    {"INTERFACE" if is_header_only else "PUBLIC"}
        {dep_list})
""")

    # Coverage, sanitizers, hardening, warnings
    if not is_header_only:
        parts.append(f"""\
if(ENABLE_COVERAGE)
    enable_code_coverage({name})
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers({name})
endif()

if(COMMAND enable_hardening)
    enable_hardening({name})
endif()

if(COMMAND set_project_warnings)
    set_project_warnings({name})
endif()
""")

    # Install
    parts.append(f"""\
install(TARGETS {name}
    EXPORT {name}_Targets
    FILE_SET HEADERS)
""")

    # Benchmarks
    if has_benchmarks:
        parts.append(f"""\
# Google Benchmark targets
if(ENABLE_BENCHMARKS AND TARGET benchmark::benchmark)
    add_executable(bench_{name} benchmarks/bench_{name}.cpp)
    target_link_libraries(bench_{name} PRIVATE {name})
    if(COMMAND project_apply_allocator)
        project_apply_allocator(bench_{name})
    endif()
    target_apply_benchmark_options(bench_{name})
    message(STATUS "[{name}] Benchmark target 'bench_{name}' registered.")
endif()
""")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Application CMakeLists.txt generator
# ---------------------------------------------------------------------------

def _gen_app_cmake(app: dict[str, Any], ctx: ProjectContext) -> str:
    name = app["name"]
    deps = app.get("deps", [])
    gui = app.get("gui", False)
    qml = app.get("qml", False)
    hardening = app.get("hardening", False)
    build_info = app.get("build_info", False)

    parts: list[str] = []

    # GUI guard
    if gui:
        parts.append(f"""\
# apps/{name}/CMakeLists.txt
if(NOT ENABLE_QT)
    message(STATUS "{name}: Skipping — ENABLE_QT is OFF")
    return()
endif()
""")
    else:
        parts.append(f"# apps/{name}/CMakeLists.txt\n")

    parts.append(f"add_executable({name} src/main.cpp)\n")

    # Build info
    if build_info:
        parts.append(f"target_generate_build_info({name} NAMESPACE {name}_info)\n")

    # Qt linking
    if gui:
        if qml:
            parts.append(f"""\
if(ENABLE_QML)
    target_link_qt({name} QML)
else()
    target_link_qt({name})
endif()
""")
        else:
            parts.append(f"target_link_qt({name})\n")

    # Dependencies
    dep_items = list(deps)
    # Feature flags are commonly needed
    link_targets = " ".join(dep_items)
    if link_targets:
        dep_lines = "\n        ".join(dep_items)
        parts.append(f"""\
target_link_libraries({name}
    PRIVATE
        {dep_lines}
        project_feature_flags)
""")
    else:
        parts.append(f"""\
target_link_libraries({name}
    PRIVATE
        project_feature_flags)
""")

    # Allocator
    parts.append(f"""\
if(COMMAND project_apply_allocator)
    project_apply_allocator({name})
endif()
""")

    # Warnings
    parts.append(f"""\
if(COMMAND set_project_warnings)
    set_project_warnings({name})
endif()
""")

    # Hardening
    if hardening:
        parts.append(f"""\
if(COMMAND enable_hardening)
    enable_hardening({name})
endif()
""")

    # Sanitizers
    parts.append(f"""\
if(COMMAND enable_sanitizers)
    enable_sanitizers({name})
endif()
""")

    # Embedded
    parts.append(f"""\
if(COMMAND add_embedded_binary_outputs)
    add_embedded_binary_outputs({name})
endif()
""")

    # GUI properties
    if gui:
        parts.append(f"""\
set_target_properties({name} PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON)
""")

    # Install
    parts.append(f"""\
install(TARGETS {name}
    EXPORT {name}_Targets)
""")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Unit test CMakeLists.txt generator
# ---------------------------------------------------------------------------

def _gen_unit_test_cmake(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    framework = ctx.tests.get("framework", "gtest")

    if framework == "gtest":
        test_link = "GTest::gtest_main"
    elif framework == "catch2":
        test_link = "Catch2::Catch2WithMain"
    else:
        test_link = "GTest::gtest_main"

    test_target = f"{name}_tests"

    return f"""\
add_executable({test_target} {name}_test.cpp)

target_link_libraries({test_target}
    PRIVATE
        {name}
        project_feature_flags
        {test_link})

if(COMMAND project_apply_allocator)
    project_apply_allocator({test_target})
endif()

if(COMMAND set_project_warnings)
    set_project_warnings({test_target})
endif()

apply_relaxed_analyzers({test_target})

add_test(NAME {test_target} COMMAND {test_target})
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}

    for lib in ctx.libs:
        name = lib["name"]
        files[f"libs/{name}/CMakeLists.txt"] = _gen_lib_cmake(lib, ctx)
        # Unit tests
        if ctx.tests.get("auto_generate", True):
            files[f"tests/unit/{name}/CMakeLists.txt"] = _gen_unit_test_cmake(lib, ctx)

    for app in ctx.apps:
        name = app["name"]
        files[f"apps/{name}/CMakeLists.txt"] = _gen_app_cmake(app, ctx)

    return files
