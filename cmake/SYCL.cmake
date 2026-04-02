# cmake/SYCL.cmake
# Intel oneAPI DPC++ / SYCL compute support for CppCmakeProjectTemplate.
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  CAVEAT — build system generated without SYCL SDK present               │
# │                                                                          │
# │  This file implements Intel oneAPI DPC++ / Clang -fsycl conventions but  │
# │  it cannot be compiled or tested without a SYCL-capable compiler.        │
# │  The logic will be skipped silently when ENABLE_SYCL=OFF (default).      │
# │                                                                          │
# │  To enable, first install Intel oneAPI:                                  │
# │    https://www.intel.com/content/www/us/en/developer/tools/oneapi/       │
# │  Then configure with: -DENABLE_SYCL=ON                                   │
# │                                                                          │
# │  Alternatively, use a Clang build with -fsycl support (hipSYCL /         │
# │  AdaptiveCpp / open-source LLVM SYCL branch).                            │
# │                                                                          │
# │  NOTE: CI will NOT run SYCL-specific paths until the SDK is available.   │
# └──────────────────────────────────────────────────────────────────────────┘
#
# Provides:
#   enable_sycl_support()                       — find SYCL compiler, set flags
#   target_add_sycl(<target>)                   — add -fsycl compile/link flags
#   set_sycl_targets(<target> <spec>)           — per-target -fsycl-targets=
#
# Global option : -DENABLE_SYCL=ON
# CLI           : tool build --sycl
#
# Target spec examples (-fsycl-targets=):
#   spir64                — generic SPIR-V (Intel GPUs, OpenCL)
#   spir64_gen            — Intel GPU ahead-of-time (Gen9/Gen11/Gen12/Xe)
#   nvidia_gpu_sm_80      — NVIDIA A100 via CUDA backend
#   amd_gpu_gfx90a        — AMD MI200 via HIP backend
#   spir64,nvidia_gpu_sm_80  — multi-target list (comma-separated)
#
# SYCL compiler detection paths searched:
#   $ONEAPI_ROOT/compiler/latest/bin, /opt/intel/oneapi/compiler/latest/bin,
#   PATH (icpx, clang++ with -fsycl support)

option(ENABLE_SYCL "Enable Intel SYCL / DPC++ language support (requires oneAPI or -fsycl)" OFF)
set(SYCL_TARGETS "" CACHE STRING
    "Comma-separated SYCL backend targets (e.g. spir64,nvidia_gpu_sm_80). Empty = default (spir64).")

# ---------------------------------------------------------------------------
# _sycl_find_compiler — locate icpx or clang++ with -fsycl support
# ---------------------------------------------------------------------------
function(_sycl_find_compiler)
    set(_sycl_hints
        "$ENV{ONEAPI_ROOT}/compiler/latest/bin"
        "$ENV{ONEAPI_ROOT}/compiler/latest/linux/bin"
        /opt/intel/oneapi/compiler/latest/bin
        /opt/intel/oneapi/compiler/latest/linux/bin
        /usr/bin
        /usr/local/bin)

    # Prefer Intel icpx (oneAPI DPC++ compiler)
    find_program(_sycl_compiler
        NAMES icpx
        HINTS ${_sycl_hints})

    if(_sycl_compiler)
        set(_SYCL_COMPILER "${_sycl_compiler}" CACHE FILEPATH
            "SYCL compiler (icpx)" FORCE)
        message(STATUS "[SYCL] Found Intel DPC++ compiler: ${_sycl_compiler}")
        return()
    endif()

    # Fallback: clang++ with -fsycl support (hipSYCL / AdaptiveCpp / LLVM SYCL)
    find_program(_clang_sycl
        NAMES clang++
        HINTS ${_sycl_hints})

    if(_clang_sycl)
        # Verify that this clang++ actually supports -fsycl
        execute_process(
            COMMAND ${_clang_sycl} -fsycl --version
            OUTPUT_VARIABLE _sycl_version
            ERROR_VARIABLE _sycl_err
            RESULT_VARIABLE _sycl_rc
            TIMEOUT 10)
        if(_sycl_rc EQUAL 0)
            set(_SYCL_COMPILER "${_clang_sycl}" CACHE FILEPATH
                "SYCL compiler (clang++ -fsycl)" FORCE)
            message(STATUS "[SYCL] Found clang++ with -fsycl support: ${_clang_sycl}")
            return()
        endif()
    endif()

    message(FATAL_ERROR
        "[SYCL] ENABLE_SYCL=ON but no SYCL-capable compiler was found.\n"
        "Install Intel oneAPI: https://www.intel.com/content/www/us/en/developer/tools/oneapi/\n"
        "   OR: use a clang++ with -fsycl (hipSYCL / AdaptiveCpp)\n"
        "   OR: set _SYCL_COMPILER=/path/to/icpx\n"
        "To disable: -DENABLE_SYCL=OFF"
    )
endfunction()

# ---------------------------------------------------------------------------
# _sycl_detect_devices — use sycl-ls to enumerate available devices
# Falls back to spir64 (generic SPIR-V) with a warning.
# ---------------------------------------------------------------------------
function(_sycl_detect_devices out_var)
    find_program(_sycl_ls
        NAMES sycl-ls
        HINTS "$ENV{ONEAPI_ROOT}/compiler/latest/bin"
              /opt/intel/oneapi/compiler/latest/bin
              /usr/bin)

    if(_sycl_ls)
        execute_process(
            COMMAND ${_sycl_ls}
            OUTPUT_VARIABLE _devs
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
            TIMEOUT 10)
        if(_devs)
            message(STATUS "[SYCL] Detected devices via sycl-ls:\n${_devs}")
            # sycl-ls output is informational; default to spir64 for build targets
            # Users should set SYCL_TARGETS explicitly for AOT compilation
            set(${out_var} "spir64" PARENT_SCOPE)
            return()
        endif()
        message(WARNING
            "[SYCL] sycl-ls returned no devices — defaulting to spir64.")
    else()
        message(WARNING
            "[SYCL] sycl-ls not found — defaulting to spir64 (generic SPIR-V).\n"
            "Override: -DSYCL_TARGETS=spir64_gen (Intel GPU AOT)")
    endif()
    set(${out_var} "spir64" PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# enable_sycl_support()
# Call once in CMakeLists.txt (guard below handles this automatically).
# Finds SYCL compiler, sets global compile/link flags.
# ---------------------------------------------------------------------------
function(enable_sycl_support)
    if(NOT ENABLE_SYCL)
        return()
    endif()

    _sycl_find_compiler()

    # Set the CXX compiler to the SYCL compiler if not already set by user
    if(_SYCL_COMPILER AND NOT CMAKE_CXX_COMPILER STREQUAL _SYCL_COMPILER)
        message(STATUS "[SYCL] Note: For full SYCL support, configure with "
                       "-DCMAKE_CXX_COMPILER=${_SYCL_COMPILER}")
    endif()

    # Resolve default target if user did not override
    if(NOT SYCL_TARGETS)
        _sycl_detect_devices(_auto_targets)
        set(SYCL_TARGETS "${_auto_targets}" CACHE STRING
            "SYCL targets (auto-detected)" FORCE)
    endif()
    message(STATUS "[SYCL] SYCL_TARGETS = ${SYCL_TARGETS}")

    # Expose to FeatureFlags.cmake
    set(FEATURE_SYCL ON PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# target_add_sycl(<target>)
# Adds -fsycl compile and link flags, defines FEATURE_SYCL=1.
# ---------------------------------------------------------------------------
function(target_add_sycl target)
    if(NOT ENABLE_SYCL)
        message(WARNING "[SYCL] target_add_sycl(${target}): ENABLE_SYCL=OFF — skipping.")
        return()
    endif()

    target_compile_options(${target} PRIVATE -fsycl)
    target_link_options(${target} PRIVATE -fsycl)
    target_compile_definitions(${target} PRIVATE FEATURE_SYCL=1)

    # Apply target-specific backend targets if set globally
    if(SYCL_TARGETS)
        target_compile_options(${target} PRIVATE
            "-fsycl-targets=${SYCL_TARGETS}")
        target_link_options(${target} PRIVATE
            "-fsycl-targets=${SYCL_TARGETS}")
        message(STATUS "[SYCL] Configured '${target}': -fsycl-targets=${SYCL_TARGETS}")
    else()
        message(STATUS "[SYCL] Configured '${target}': -fsycl (default targets)")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# set_sycl_targets(<target> <spec>)
# Per-target override: comma-separated backend target list.
# Example: set_sycl_targets(my_app "spir64_gen,nvidia_gpu_sm_80")
# ---------------------------------------------------------------------------
function(set_sycl_targets target spec)
    if(NOT ENABLE_SYCL)
        return()
    endif()
    # Remove any prior -fsycl-targets= and set the new one
    target_compile_options(${target} PRIVATE "-fsycl-targets=${spec}")
    target_link_options(${target} PRIVATE "-fsycl-targets=${spec}")
    message(STATUS "[SYCL] '${target}': -fsycl-targets=${spec}")
endfunction()

# ---------------------------------------------------------------------------
# Module-level: auto-run enable_sycl_support() when ENABLE_SYCL=ON
# (Called once via include(SYCL) in CMakeLists.txt)
# ---------------------------------------------------------------------------
if(ENABLE_SYCL)
    enable_sycl_support()
endif()
