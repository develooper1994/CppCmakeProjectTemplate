# cmake/CUDA.cmake
# CUDA / GPU compute support for CppCmakeProjectTemplate.
#
# Provides:
#   enable_cuda_support()                      — find CUDA toolkit, enable language
#   target_add_cuda(<target> [SEPARABLE])      — add CUDA to a target
#   set_cuda_architectures(<target> <spec>)    — set GPU architectures
#
# Global option: -DENABLE_CUDA=ON
# CLI: tool build --cuda
#
# Architecture spec  examples:
#   native       — auto-detect the installed GPU (requires nvcc ≥ 10.2)
#   all-major    — every major arch (Volta, Turing, Ampere, Ada, Hopper, …)
#   75;86;89     — explicit SM list (RTX 20/30/40)
#   89-real      — generate device code only (faster compile, same-device only)
#
# WSL / headless detection:
#   nvcc is searched in: PATH, /usr/bin, /usr/local/cuda/bin, /usr/lib/cuda/bin
#   If WSL is detected (/proc/version contains "microsoft"), those paths are
#   prepended automatically.
#
# Clang-as-CUDA-compiler:
#   Set -DCUDA_COMPILER=clang to use clang for .cu files (requires clang ≥ 14).

option(ENABLE_CUDA      "Enable CUDA language and GPU target support"   OFF)
option(CUDA_SEPARABLE_COMPILATION "Enable separable CUDA compilation globally" OFF)
set(CUDA_COMPILER "" CACHE STRING "CUDA compiler: empty = nvcc (default), 'clang' = clang")

# ---------------------------------------------------------------------------
# _cuda_detect_wsl — returns 1 if running inside WSL
# ---------------------------------------------------------------------------
function(_cuda_detect_wsl out_var)
    set(${out_var} FALSE PARENT_SCOPE)
    if(EXISTS "/proc/version")
        file(READ "/proc/version" _proc_version)
        if(_proc_version MATCHES "[Mm]icrosoft")
            set(${out_var} TRUE PARENT_SCOPE)
        endif()
    endif()
endfunction()

# ---------------------------------------------------------------------------
# _cuda_find_toolkit — locate nvcc and set CMAKE_CUDA_COMPILER if needed
# ---------------------------------------------------------------------------
function(_cuda_find_toolkit)
    _cuda_detect_wsl(_wsl)

    # Build search list: standard paths + WSL extras
    set(_nvcc_hints "")
    if(_wsl)
        list(APPEND _nvcc_hints
            /usr/bin
            /usr/local/cuda/bin
            /usr/lib/cuda/bin)
        message(STATUS "[CUDA] WSL environment detected — searching extra nvcc paths")
    else()
        list(APPEND _nvcc_hints
            /usr/bin
            /usr/local/cuda/bin
            /usr/lib/cuda/bin
            /opt/cuda/bin)
    endif()

    if(CUDA_COMPILER STREQUAL "clang")
        # Clang-as-CUDA compiler
        find_program(_clang_cuda clang++ HINTS ${_nvcc_hints} REQUIRED)
        set(CMAKE_CUDA_COMPILER "${_clang_cuda}" CACHE FILEPATH "CUDA compiler (clang)" FORCE)
        message(STATUS "[CUDA] Using clang as CUDA compiler: ${_clang_cuda}")
    else()
        # Standard nvcc path (may already be in PATH)
        if(NOT CMAKE_CUDA_COMPILER)
            find_program(_found_nvcc nvcc HINTS ${_nvcc_hints})
            if(_found_nvcc)
                set(CMAKE_CUDA_COMPILER "${_found_nvcc}" CACHE FILEPATH "CUDA compiler (nvcc)" FORCE)
                message(STATUS "[CUDA] Found nvcc: ${_found_nvcc}")
            else()
                message(FATAL_ERROR
                    "[CUDA] ENABLE_CUDA=ON but nvcc was not found.\n"
                    "Install: sudo apt install nvidia-cuda-toolkit\n"
                    "   OR:   set CMAKE_CUDA_COMPILER=/path/to/nvcc\n"
                    "   OR:   add nvcc to PATH before running cmake\n"
                    "To disable: -DENABLE_CUDA=OFF"
                )
            endif()
        endif()
    endif()
endfunction()

# ---------------------------------------------------------------------------
# enable_cuda_support()
# Call once in CMakeLists.txt (already done via include(CUDA) guard below).
# Enables CUDA language, finds CUDAToolkit, sets default architectures.
# ---------------------------------------------------------------------------
function(enable_cuda_support)
    if(NOT ENABLE_CUDA)
        return()
    endif()

    _cuda_find_toolkit()

    # Enable CUDA language (must be before find_package(CUDAToolkit))
    enable_language(CUDA)

    # Modern CMake (3.17+): CUDAToolkit provides imported targets
    find_package(CUDAToolkit REQUIRED)
    message(STATUS "[CUDA] CUDAToolkit ${CUDAToolkit_VERSION} found at ${CUDAToolkit_LIBRARY_DIR}")

    # -------------------------------------------------------------------------
    # Determine maximum C++ standard for CUDA device code
    # cuda_compatible_cxx_standard() is provided by cmake/CxxStandard.cmake.
    # -------------------------------------------------------------------------
    if(COMMAND cuda_compatible_cxx_standard)
        cuda_compatible_cxx_standard("${CUDAToolkit_VERSION}" _cuda_max_std)
    else()
        # Fallback if CxxStandard.cmake was not loaded
        set(_cuda_max_std 17)
        message(WARNING "[CUDA] CxxStandard.cmake not loaded — defaulting device C++ to C++17.")
    endif()

    message(STATUS
        "[CUDA] CUDA ${CUDAToolkit_VERSION} → "
        "max device-code C++ standard: C++${_cuda_max_std}")

    # Store for use by target_add_cuda() and external callers
    set(_CUDA_DEVICE_CXX_STD ${_cuda_max_std} CACHE INTERNAL
        "Max C++ standard for CUDA device code (derived from toolkit version)")

    # Apply to CUDA language globally (per-target override still possible)
    if(NOT DEFINED CACHE{CMAKE_CUDA_STANDARD})
        set(CMAKE_CUDA_STANDARD "${_cuda_max_std}" CACHE STRING
            "C++ standard for CUDA device code (auto: C++${_cuda_max_std} from CUDA ${CUDAToolkit_VERSION})")
        set_property(CACHE CMAKE_CUDA_STANDARD PROPERTY STRINGS 11 14 17 20)
    endif()
    set(CMAKE_CUDA_STANDARD_REQUIRED ON CACHE BOOL
        "Require CUDA C++ standard to be met" FORCE)

    # Warn when host C++ standard exceeds the CUDA device-code limit
    if(DEFINED CMAKE_CXX_STANDARD AND CMAKE_CXX_STANDARD GREATER _cuda_max_std)
        message(WARNING
            "[CUDA] Host C++ standard (C++${CMAKE_CXX_STANDARD}) exceeds "
            "CUDA ${CUDAToolkit_VERSION} device-code limit (C++${_cuda_max_std}).\n"
            "  • .cu device code will be compiled with C++${_cuda_max_std}.\n"
            "  • Host .cpp files are unaffected (still C++${CMAKE_CXX_STANDARD}).\n"
            "  To silence: -DCMAKE_CXX_STANDARD=${_cuda_max_std} or upgrade to CUDA ≥12.2.")
    endif()

    # Default architecture: "native" auto-detects the installed GPU at build time.
    # Override per-target with set_cuda_architectures() or globally via:
    #   cmake -DCMAKE_CUDA_ARCHITECTURES=75;86
    if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
        set(CMAKE_CUDA_ARCHITECTURES "native" CACHE STRING
            "CUDA GPU architectures: native | all-major | 75;86;89 | ..." FORCE)
        message(STATUS "[CUDA] CMAKE_CUDA_ARCHITECTURES = native (auto GPU detect)")
    endif()

    # Expose to FeatureFlags
    set(FEATURE_CUDA ON PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# target_add_cuda(<target> [SEPARABLE])
# Configures <target> for CUDA:
#   - Enables CUDA language on the target's source files
#   - Links CUDART
#   - Optionally enables separable compilation
# ---------------------------------------------------------------------------
function(target_add_cuda target)
    cmake_parse_arguments(_TAC "SEPARABLE" "" "" ${ARGN})

    if(NOT ENABLE_CUDA)
        message(WARNING "[CUDA] target_add_cuda(${target}): ENABLE_CUDA=OFF — skipping.")
        return()
    endif()

    find_package(CUDAToolkit REQUIRED)

    # Link CUDA runtime
    target_link_libraries(${target} PRIVATE CUDA::cudart)
    target_compile_definitions(${target} PRIVATE FEATURE_CUDA=1)

    if(_TAC_SEPARABLE OR CUDA_SEPARABLE_COMPILATION)
        set_target_properties(${target} PROPERTIES
            CUDA_SEPARABLE_COMPILATION ON)
        message(STATUS "[CUDA] Separable compilation enabled for '${target}'")
    endif()

    # Use CUDA-version-appropriate C++ standard for device code.
    # Determined during enable_cuda_support() from the toolkit version.
    if(DEFINED _CUDA_DEVICE_CXX_STD)
        set(_tgt_cuda_std "${_CUDA_DEVICE_CXX_STD}")
    elseif(DEFINED CMAKE_CUDA_STANDARD)
        set(_tgt_cuda_std "${CMAKE_CUDA_STANDARD}")
    else()
        set(_tgt_cuda_std 17)    # safe fallback
    endif()

    set_target_properties(${target} PROPERTIES
        CUDA_STANDARD          "${_tgt_cuda_std}"
        CUDA_STANDARD_REQUIRED ON)

    message(STATUS "[CUDA] Configured '${target}': device C++${_tgt_cuda_std} / CUDA runtime")
endfunction()

# ---------------------------------------------------------------------------
# set_cuda_architectures(<target> <spec>)
# <spec> examples: native | all-major | 75;86;89 | 89-real
# ---------------------------------------------------------------------------
function(set_cuda_architectures target spec)
    if(NOT ENABLE_CUDA)
        return()
    endif()
    set_target_properties(${target} PROPERTIES
        CUDA_ARCHITECTURES "${spec}")
    message(STATUS "[CUDA] '${target}': CUDA_ARCHITECTURES = ${spec}")
endfunction()

# ---------------------------------------------------------------------------
# Module-level: auto-run enable_cuda_support() when ENABLE_CUDA=ON
# (Called once via include(CUDA) in CMakeLists.txt)
# ---------------------------------------------------------------------------
if(ENABLE_CUDA)
    enable_cuda_support()
endif()
