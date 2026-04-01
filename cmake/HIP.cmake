# cmake/HIP.cmake
# AMD HIP / ROCm GPU compute support for CppCmakeProjectTemplate.
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  CAVEAT — build system generated without HIP SDK present                 │
# │                                                                          │
# │  This file implements the correct ROCm ≥ 5.x CMake conventions but it   │
# │  cannot be compiled or tested without the HIP/ROCm stack installed.      │
# │  The logic will be skipped silently when ENABLE_HIP=OFF (default).       │
# │                                                                          │
# │  To enable, first install ROCm:                                          │
# │    https://rocm.docs.amd.com/en/latest/deploy/linux/index.html          │
# │  Then configure with: -DENABLE_HIP=ON                                    │
# │                                                                          │
# │  NOTE: CI will NOT run HIP-specific paths until the SDK is available.    │
# └──────────────────────────────────────────────────────────────────────────┘
#
# Provides:
#   enable_hip_support()                       — find ROCm/HIP, enable language
#   target_add_hip(<target>)                   — link HIP runtime, set arch
#   set_hip_architectures(<target> <spec>)     — per-target gfx* override
#
# Global option : -DENABLE_HIP=ON
# CLI           : tool build --hip
#
# Architecture spec examples (semicolon-separated):
#   gfx906          — Vega 20  (Radeon VII / Instinct MI50)
#   gfx908          — Arcturus (Instinct MI100)
#   gfx90a          — Aldebaran (Instinct MI200)
#   gfx1030         — RDNA 2  (RX 6800 / 6900)
#   gfx1100         — RDNA 3  (RX 7900)
#   gfx906;gfx90a   — multi-arch list
#
# HIP / ROCm detection paths searched:
#   $ROCM_PATH/bin, /opt/rocm/bin, /opt/rocm/llvm/bin, /usr/bin

option(ENABLE_HIP "Enable AMD HIP language and GPU target support (requires ROCm)" OFF)
set(HIP_ARCHITECTURES "" CACHE STRING
    "Semicolon-separated HIP GPU targets (e.g. gfx906;gfx90a). Empty = auto-detect.")

# ---------------------------------------------------------------------------
# _hip_find_toolkit — locate amdclang++ / hipcc and ROCm root
# ---------------------------------------------------------------------------
function(_hip_find_toolkit)
    set(_hip_hints
        "$ENV{ROCM_PATH}/bin"
        /opt/rocm/bin
        /opt/rocm/llvm/bin
        /usr/bin)

    # Prefer amdclang++ (ROCm ≥ 5.2) over the legacy hipcc wrapper
    find_program(_hip_compiler
        NAMES amdclang++ hipcc
        HINTS ${_hip_hints})

    if(NOT _hip_compiler)
        message(FATAL_ERROR
            "[HIP] ENABLE_HIP=ON but neither 'amdclang++' nor 'hipcc' was found.\n"
            "Install ROCm: https://rocm.docs.amd.com/en/latest/deploy/linux/index.html\n"
            "   OR: set CMAKE_HIP_COMPILER=/path/to/amdclang++\n"
            "   OR: add /opt/rocm/bin to PATH before running cmake\n"
            "To disable: -DENABLE_HIP=OFF"
        )
    endif()

    if(NOT CMAKE_HIP_COMPILER)
        set(CMAKE_HIP_COMPILER "${_hip_compiler}" CACHE FILEPATH
            "HIP compiler (amdclang++ or hipcc)" FORCE)
        message(STATUS "[HIP] Found HIP compiler: ${_hip_compiler}")
    endif()

    # Locate ROCm root (for include paths and library hints)
    find_path(_rocm_root
        NAMES include/hip/hip_runtime.h
        HINTS "$ENV{ROCM_PATH}" /opt/rocm)
    if(_rocm_root)
        set(ROCM_PATH "${_rocm_root}" CACHE PATH "ROCm installation root" FORCE)
        message(STATUS "[HIP] ROCm root: ${_rocm_root}")
    else()
        message(WARNING
            "[HIP] Could not locate ROCm root (hip_runtime.h not found).\n"
            "Set ROCM_PATH or verify your ROCm installation.")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# _hip_detect_architectures — use rocm_agent_enumerator when available
# Falls back to gfx906 with an informational warning.
# ---------------------------------------------------------------------------
function(_hip_detect_architectures out_var)
    find_program(_roc_enum
        NAMES rocm_agent_enumerator
        HINTS "${ROCM_PATH}/bin" /opt/rocm/bin)

    if(_roc_enum)
        execute_process(
            COMMAND ${_roc_enum} -t GPU
            OUTPUT_VARIABLE _gpus
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET)
        if(_gpus)
            string(REPLACE "\n" ";" _gfx_list "${_gpus}")
            list(REMOVE_DUPLICATES _gfx_list)
            set(${out_var} "${_gfx_list}" PARENT_SCOPE)
            return()
        endif()
        message(WARNING
            "[HIP] rocm_agent_enumerator returned no GPUs — "
            "defaulting to gfx906. Override: -DHIP_ARCHITECTURES=gfxXXX")
    else()
        message(WARNING
            "[HIP] rocm_agent_enumerator not found — "
            "defaulting to gfx906. Override: -DHIP_ARCHITECTURES=gfxXXX")
    endif()
    set(${out_var} "gfx906" PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# enable_hip_support()
# Call once in CMakeLists.txt (guard below handles this automatically).
# Enables HIP language, finds hip::host runtime, sets default architectures.
# ---------------------------------------------------------------------------
function(enable_hip_support)
    if(NOT ENABLE_HIP)
        return()
    endif()

    _hip_find_toolkit()

    # Requires CMake ≥ 3.21 with HIP language support (shipped with ROCm ≥ 4.5)
    enable_language(HIP)

    # Modern CMake: find_package(hip) provides imported targets (hip::host, hip::device)
    find_package(hip QUIET
        HINTS "${ROCM_PATH}" /opt/rocm
        PATH_SUFFIXES lib/cmake/hip)

    if(hip_FOUND)
        message(STATUS "[HIP] hip package found: ${hip_VERSION}")
    else()
        # Fallback: build an IMPORTED target from the raw amdhip64 library
        find_library(_hiprt_lib
            NAMES amdhip64 hip_hcc
            HINTS "${ROCM_PATH}/lib" /opt/rocm/lib)

        if(_hiprt_lib)
            message(STATUS "[HIP] HIP runtime library (fallback): ${_hiprt_lib}")
            add_library(hip::host UNKNOWN IMPORTED GLOBAL)
            set_target_properties(hip::host PROPERTIES
                IMPORTED_LOCATION "${_hiprt_lib}"
                INTERFACE_INCLUDE_DIRECTORIES "${ROCM_PATH}/include")
        else()
            message(WARNING
                "[HIP] HIP runtime library (amdhip64) not found — "
                "target_add_hip() will warn at link time.")
        endif()
    endif()

    # Resolve GPU architecture list (cache to avoid re-running enumerator)
    if(NOT HIP_ARCHITECTURES)
        _hip_detect_architectures(_auto_archs)
        set(HIP_ARCHITECTURES "${_auto_archs}" CACHE STRING
            "HIP GPU targets (auto-detected)" FORCE)
    endif()
    message(STATUS "[HIP] HIP_ARCHITECTURES = ${HIP_ARCHITECTURES}")

    # Expose to FeatureFlags.cmake
    set(FEATURE_HIP ON PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# target_add_hip(<target>)
# Links hip::host (amdhip64) runtime and sets GPU architecture list.
# ---------------------------------------------------------------------------
function(target_add_hip target)
    if(NOT ENABLE_HIP)
        message(WARNING "[HIP] target_add_hip(${target}): ENABLE_HIP=OFF — skipping.")
        return()
    endif()

    if(TARGET hip::host)
        target_link_libraries(${target} PRIVATE hip::host)
    elseif(TARGET hip::hiprt)
        target_link_libraries(${target} PRIVATE hip::hiprt)
    else()
        message(WARNING
            "[HIP] HIP runtime imported target not found for '${target}'. "
            "Link hip::host manually or ensure find_package(hip) ran successfully.")
    endif()

    target_compile_definitions(${target} PRIVATE FEATURE_HIP=1)

    if(HIP_ARCHITECTURES)
        set_target_properties(${target} PROPERTIES
            HIP_ARCHITECTURES "${HIP_ARCHITECTURES}")
        message(STATUS "[HIP] Configured '${target}': HIP_ARCHITECTURES=${HIP_ARCHITECTURES}")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# set_hip_architectures(<target> <spec>)
# Per-target override: semicolon-separated gfx* target list.
# ---------------------------------------------------------------------------
function(set_hip_architectures target spec)
    if(NOT ENABLE_HIP)
        return()
    endif()
    set_target_properties(${target} PROPERTIES HIP_ARCHITECTURES "${spec}")
    message(STATUS "[HIP] '${target}': HIP_ARCHITECTURES = ${spec}")
endfunction()

# ---------------------------------------------------------------------------
# Module-level: auto-run enable_hip_support() when ENABLE_HIP=ON
# (Called once via include(HIP) in CMakeLists.txt)
# ---------------------------------------------------------------------------
if(ENABLE_HIP)
    enable_hip_support()
endif()
