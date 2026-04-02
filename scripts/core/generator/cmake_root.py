"""
core/generator/cmake_root.py — Root CMakeLists.txt and aggregator generators.

Generates:
  - CMakeLists.txt          (project root)
  - libs/CMakeLists.txt     (library aggregator)
  - apps/CMakeLists.txt     (application aggregator)
  - tests/CMakeLists.txt    (test framework + aggregator)
  - tests/unit/CMakeLists.txt
  - tests/fuzz/CMakeLists.txt
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext


# ---------------------------------------------------------------------------
# Root CMakeLists.txt
# ---------------------------------------------------------------------------

def _gen_root_cmake(ctx: ProjectContext) -> str:
    cmake_min = ctx.cmake_minimum
    name = ctx.name
    desc = ctx.description or "A C++ project"
    enabled = ctx.cmake_modules.get("enabled", [])

    # Module includes — order matters: CxxStandard and ProjectConfigs first
    priority_modules = ["CxxStandard", "ProjectConfigs"]
    remaining_modules = [m for m in enabled if m not in priority_modules]

    includes = ""
    for m in priority_modules:
        if m in enabled:
            includes += f"include({m})\n"

    includes += "\n# Modules\ninclude(FetchContent)\n"
    for m in ["ProjectOptions", "BuildInfo", "CodeCoverage", "Sanitizers",
              "Hardening", "StaticAnalyzers", "EmbeddedUtils", "FeatureFlags",
              "LTO", "PGO", "BuildCache", "Benchmark", "Allocators",
              "OpenMP", "Qt", "CUDA", "HIP", "SYCL", "Metal",
              "Reproducibility", "Fuzzing", "CxxModules", "IWYU"]:
        if m in remaining_modules:
            includes += f"include({m})\n"

    # Libs / Apps
    has_tests = bool(ctx.tests.get("framework"))
    has_fuzz = ctx.tests.get("fuzz", False)

    # CPack metadata
    author = ctx.author or "maintainer"
    contact = ctx.contact or ""

    return f'''\
cmake_minimum_required(VERSION {cmake_min})
# -----------------------------------------------------------------------------
# Project Information
# -----------------------------------------------------------------------------
file(READ "${{CMAKE_SOURCE_DIR}}/VERSION" _cmake_version_content OPTIONAL)
if(DEFINED _cmake_version_content)
    string(STRIP "${{_cmake_version_content}}" _cmake_version_content)
    string(REGEX MATCH "^[0-9]+\\\\.[0-9]+\\\\.[0-9]+" PROJECT_BASE_VERSION "${{_cmake_version_content}}")
endif()
if(NOT PROJECT_BASE_VERSION)
    set(PROJECT_BASE_VERSION "0.0.0")
endif()

project({name}
    VERSION ${{PROJECT_BASE_VERSION}}
    DESCRIPTION "{desc}"
    LANGUAGES CXX)

# -----------------------------------------------------------------------------
# Prevent In-Source Builds
# -----------------------------------------------------------------------------
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-source builds are prohibited. Please use a build directory.")
endif()

# -----------------------------------------------------------------------------
# Project Configuration & Options
# -----------------------------------------------------------------------------
list(APPEND CMAKE_MODULE_PATH "${{PROJECT_SOURCE_DIR}}/cmake")
{includes}
generate_feature_flags()

# INTERFACE library — all targets inherit FeatureFlags.h
add_library(project_feature_flags INTERFACE)
target_include_directories(project_feature_flags INTERFACE
    $<BUILD_INTERFACE:${{FEATURE_FLAGS_INCLUDE_DIR}}>
    $<INSTALL_INTERFACE:include>)

if(CMAKE_SYSTEM_NAME STREQUAL "Generic")
    message(STATUS "Embedded System Detected: ${{CMAKE_SYSTEM_PROCESSOR}}")
    set(ENABLE_QT OFF CACHE BOOL "Qt is disabled for embedded by default" FORCE)
    set(ENABLE_ASAN OFF CACHE BOOL "ASan is disabled for embedded by default" FORCE)
endif()

if(ENABLE_COVERAGE)
    add_coverage_report_target()
endif()

enable_static_analysis()

# -----------------------------------------------------------------------------
# Targets
# -----------------------------------------------------------------------------
add_subdirectory(libs)
add_subdirectory(apps)

{"if(ENABLE_UNIT_TESTS)" if has_tests else "# No test framework configured"}
{("    enable_testing()" + chr(10) + "    add_subdirectory(tests)" + chr(10) + "endif()") if has_tests else ""}

if(ENABLE_DOCS)
    add_subdirectory(docs)
endif()

# -----------------------------------------------------------------------------
# Packaging (CPack)
# -----------------------------------------------------------------------------
set(CPACK_PACKAGE_VENDOR "{author}")
set(CPACK_PACKAGE_CONTACT "{contact}")
set(CPACK_RESOURCE_FILE_LICENSE "${{PROJECT_SOURCE_DIR}}/LICENSE")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "${{PROJECT_DESCRIPTION}}")

if(WIN32)
    set(CPACK_GENERATOR "ZIP;NSIS")
else()
    set(CPACK_GENERATOR "TGZ;DEB")
endif()

include(CPack)
'''


# ---------------------------------------------------------------------------
# Aggregator CMakeLists
# ---------------------------------------------------------------------------

def _gen_libs_cmake(ctx: ProjectContext) -> str:
    lines = ["# libs/CMakeLists.txt",
             "# Generated — do not edit manually.\n"]
    for lib in ctx.libs:
        lines.append(f"add_subdirectory({lib['name']})")
    return "\n".join(lines) + "\n"


def _gen_apps_cmake(ctx: ProjectContext) -> str:
    lines = ["# apps/CMakeLists.txt",
             "# Generated — do not edit manually.\n"]
    for app in ctx.apps:
        lines.append(f"add_subdirectory({app['name']})")
    return "\n".join(lines) + "\n"


def _gen_tests_root_cmake(ctx: ProjectContext) -> str:
    framework = ctx.tests.get("framework", "gtest")
    has_fuzz = ctx.tests.get("fuzz", False)

    parts = [
        "# tests/CMakeLists.txt",
        "# Supports: GoogleTest (default), Catch2, Boost.Test, QTest\n",
        "include(FetchContent)\n",
    ]

    # GoogleTest
    parts.append("""\
# ── GoogleTest ───────────────────────────────────────────────────────────────
if(ENABLE_GTEST)
    FetchContent_Declare(googletest
        URL      https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
        URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        SYSTEM)
    FetchContent_MakeAvailable(googletest)
    message(STATUS "Test framework: GoogleTest")
    foreach(_gtest_target IN ITEMS gmock gmock_main gtest gtest_main)
        if(TARGET ${_gtest_target})
            set_target_properties(${_gtest_target} PROPERTIES CXX_CLANG_TIDY "")
            set_target_properties(${_gtest_target} PROPERTIES CXX_CPPCHECK "")
        endif()
    endforeach()
endif()
""")

    parts.append("""\
# ── Catch2 ───────────────────────────────────────────────────────────────────
if(ENABLE_CATCH2)
    FetchContent_Declare(Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG        v3.5.3
        SYSTEM)
    FetchContent_MakeAvailable(Catch2)
    list(APPEND CMAKE_MODULE_PATH ${catch2_SOURCE_DIR}/extras)
    message(STATUS "Test framework: Catch2")
endif()
""")

    parts.append("""\
# ── Boost.Test ───────────────────────────────────────────────────────────────
if(ENABLE_BOOST_TEST)
    if(NOT ENABLE_BOOST)
        message(FATAL_ERROR "ENABLE_BOOST_TEST requires ENABLE_BOOST=ON")
    endif()
    find_package(Boost REQUIRED COMPONENTS unit_test_framework)
    message(STATUS "Test framework: Boost.Test")
endif()
""")

    parts.append("""\
# ── QTest ────────────────────────────────────────────────────────────────────
if(ENABLE_QT AND Qt6_FOUND)
    message(STATUS "Test framework: QTest (Qt6)")
elseif(ENABLE_QT AND Qt5_FOUND)
    message(STATUS "Test framework: QTest (Qt5)")
endif()

add_subdirectory(unit)
""")

    if has_fuzz:
        parts.append("""\
if(ENABLE_FUZZING)
    add_subdirectory(fuzz)
endif()
""")

    return "\n".join(parts)


def _gen_tests_unit_cmake(ctx: ProjectContext) -> str:
    lines = ["# tests/unit/CMakeLists.txt",
             "# Generated — do not edit manually.\n"]
    for lib in ctx.libs:
        lines.append(f"add_subdirectory({lib['name']})")
    return "\n".join(lines) + "\n"


def _gen_tests_fuzz_cmake(ctx: ProjectContext) -> str:
    lines = [
        "# tests/fuzz/CMakeLists.txt",
        "if(NOT ENABLE_FUZZING)",
        "    return()",
        "endif()\n",
        "include(Fuzzing)\n",
    ]

    for lib in ctx.libs:
        if lib.get("fuzz"):
            name = lib["name"]
            lines.append(f"add_fuzz_target(fuzz_{name} SOURCES fuzz_{name}.cpp)")
            lines.append(f"target_link_libraries(fuzz_{name} PRIVATE {name})")
            lines.append(f"apply_relaxed_analyzers(fuzz_{name})")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    files["CMakeLists.txt"] = _gen_root_cmake(ctx)
    files["libs/CMakeLists.txt"] = _gen_libs_cmake(ctx)
    files["apps/CMakeLists.txt"] = _gen_apps_cmake(ctx)
    files["tests/CMakeLists.txt"] = _gen_tests_root_cmake(ctx)
    files["tests/unit/CMakeLists.txt"] = _gen_tests_unit_cmake(ctx)
    if ctx.tests.get("fuzz"):
        files["tests/fuzz/CMakeLists.txt"] = _gen_tests_fuzz_cmake(ctx)
    return files
