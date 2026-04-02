"""
core/generator/cmake_static — Static cmake module generator.

Reads cmake files from the project's cmake/ directory and returns them as-is.
These files contain complex CMake logic that does not vary based on tool.toml.

Excludes:
  - ProjectConfigs.cmake (DYNAMIC — handled by cmake_dynamic.py)
  - FeatureFlags.cmake   (DYNAMIC — handled by cmake_dynamic.py)
"""
from __future__ import annotations

from pathlib import Path

from core.utils.common import Logger


# ---------------------------------------------------------------------------
# Static file inventory
# ---------------------------------------------------------------------------

STATIC_CMAKE_MODULES: list[str] = [
    "Allocators.cmake",
    "Benchmark.cmake",
    "BuildCache.cmake",
    "BuildInfo.cmake",
    "CodeCoverage.cmake",
    "CUDA.cmake",
    "CxxModules.cmake",
    "CxxStandard.cmake",
    "EmbeddedUtils.cmake",
    "Fuzzing.cmake",
    "HIP.cmake",
    "Hardening.cmake",
    "IWYU.cmake",
    "LTO.cmake",
    "Metal.cmake",
    "OpenMP.cmake",
    "PGO.cmake",
    "ProjectExport.cmake",
    "ProjectOptions.cmake",
    "Qt.cmake",
    "Reproducibility.cmake",
    "Sanitizers.cmake",
    "StaticAnalyzers.cmake",
    "SYCL.cmake",
]

STATIC_CMAKE_HEADERS: list[str] = [
    "BuildInfo.h.in",
    "BuildInfoHelper.h",
    "iwyu_mappings.imp",
    "LibraryConfig.cmake.in",
    "PoolAllocator.h",
    "ProjectInfo.h",
]

STATIC_TOOLCHAIN_FILES: list[str] = [
    "toolchains/aarch64-linux-gnu.cmake",
    "toolchains/aarch64-linux-musl-zig.cmake",
    "toolchains/aarch64-linux-musl.cmake",
    "toolchains/arm-cortex-m0.cmake",
    "toolchains/arm-cortex-m7.cmake",
    "toolchains/arm-none-eabi.cmake",
    "toolchains/armv7-linux-gnueabihf.cmake",
    "toolchains/linux-x86.cmake",
    "toolchains/mipsel-linux-gnu.cmake",
    "toolchains/powerpc64le-linux-gnu.cmake",
    "toolchains/riscv64-linux-gnu.cmake",
    "toolchains/template-custom-gnu.cmake",
    "toolchains/x86_64-linux-musl-zig.cmake",
    "toolchains/x86_64-linux-musl.cmake",
    "toolchains/x86_64-w64-mingw32.cmake",
]


def _find_cmake_source_dir() -> Path:
    """Locate the cmake/ directory relative to the project root."""
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        if (parent / "tool.toml").exists():
            cmake_dir = parent / "cmake"
            if cmake_dir.is_dir():
                return cmake_dir
    raise FileNotFoundError(
        "Could not locate cmake/ directory from generator. "
        "Ensure you are running from within the project tree."
    )


def generate_all(ctx, target_dir: str) -> dict[str, str]:
    """Return {rel_path: content} for all static cmake files."""
    cmake_dir = _find_cmake_source_dir()
    result: dict[str, str] = {}

    all_rel = (
        STATIC_CMAKE_MODULES
        + STATIC_CMAKE_HEADERS
        + STATIC_TOOLCHAIN_FILES
    )

    for filename in all_rel:
        rel_path = f"cmake/{filename}"
        src = cmake_dir / filename
        if src.exists():
            result[rel_path] = src.read_text(encoding="utf-8")
        else:
            Logger.warning(f"Static template not found: {src}")

    return result
