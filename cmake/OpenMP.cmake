# cmake/OpenMP.cmake
# OpenMP support: per-target and project-wide parallelization.
#
# Provides:
#   enable_openmp(<target>)              — link OpenMP to a single target
#   enable_openmp_simd(<target>)         — SIMD-only (no threading, no runtime dep)
#   enable_auto_parallelization(<target>) — GCC/Clang loop auto-parallelization
#
# Global toggle:  -DENABLE_OPENMP=ON
# SIMD-only:      -DENABLE_OPENMP_SIMD=ON  (safe on embedded, no libgomp dep)
# Auto-parallel:  -DENABLE_AUTO_PARALLEL=ON (GCC: -floop-parallelize-all)
#
# Usage in CMakeLists.txt:
#   enable_openmp(my_target)
#   enable_openmp_simd(my_target)
#   enable_auto_parallelization(my_target)
#
# Usage from CLI:
#   cmake --preset gcc-release-static-x86_64 -DENABLE_OPENMP=ON
#   tool build --openmp   (sets -DENABLE_OPENMP=ON)

option(ENABLE_OPENMP        "Enable OpenMP threading support (links libgomp)"    OFF)
option(ENABLE_OPENMP_SIMD   "Enable OpenMP SIMD pragmas only (no runtime dep)"   OFF)
option(ENABLE_AUTO_PARALLEL "Enable compiler auto-parallelization (-floop-parallelize-all / -ftree-parallelize-loops)" OFF)

# ---------------------------------------------------------------------------
# enable_openmp(<target>)
# Links OpenMP to <target>. Requires ENABLE_OPENMP=ON OR ENABLE_OPENMP_SIMD=ON
# at cmake configure time, or can be called unconditionally per-target.
# ---------------------------------------------------------------------------
function(enable_openmp target)
    # Full OpenMP (threading + SIMD)
    find_package(OpenMP QUIET)
    if(NOT OpenMP_CXX_FOUND)
        message(WARNING "[OpenMP] OpenMP not found — target '${target}' will not use OpenMP.")
        return()
    endif()
    target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
    target_compile_definitions(${target} PRIVATE FEATURE_OPENMP=1)
    message(STATUS "[OpenMP] Linked to '${target}' (spec ${OpenMP_CXX_VERSION})")
endfunction()

# ---------------------------------------------------------------------------
# enable_openmp_simd(<target>)
# Adds -fopenmp-simd (Clang) / -fopenmp-simd (GCC ≥ 4.9).
# Does NOT link libgomp — safe for embedded and minimal builds.
# ---------------------------------------------------------------------------
function(enable_openmp_simd target)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU|Intel")
        target_compile_options(${target} PRIVATE -fopenmp-simd)
        target_compile_definitions(${target} PRIVATE FEATURE_OPENMP_SIMD=1)
        message(STATUS "[OpenMP SIMD] Applied -fopenmp-simd to '${target}'")
    elseif(MSVC)
        target_compile_options(${target} PRIVATE /openmp:experimental)
        target_compile_definitions(${target} PRIVATE FEATURE_OPENMP_SIMD=1)
        message(STATUS "[OpenMP SIMD] Applied /openmp:experimental to '${target}'")
    else()
        message(WARNING "[OpenMP SIMD] Compiler '${CMAKE_CXX_COMPILER_ID}' not supported for SIMD-only OpenMP.")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# enable_auto_parallelization(<target>)
# Instructs the compiler to auto-parallelize loops where it deems safe.
# GCC:   -floop-parallelize-all -ftree-parallelize-loops=N (N = detected cores)
# Clang: -fopenmp (full) or -fopenmp-simd (safer); true auto-parallel needs polly
# MSVC:  /Qpar (auto-parallelizer)
# ---------------------------------------------------------------------------
function(enable_auto_parallelization target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        # Detect logical CPU count for loop parallelization depth
        include(ProcessorCount)
        ProcessorCount(_cpu_count)
        if(_cpu_count EQUAL 0)
            set(_cpu_count 4)
        endif()
        target_compile_options(${target} PRIVATE
            -floop-parallelize-all
            -ftree-parallelize-loops=${_cpu_count})
        message(STATUS "[AutoParallel] GCC auto-parallelization (${_cpu_count} threads) → '${target}'")
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        # Clang: Polly (loop optimizer) for auto-vectorization/parallelization
        # -mllvm -polly enables Polly (only if Clang was built with Polly)
        include(CheckCXXCompilerFlag)
        check_cxx_compiler_flag("-mllvm -polly" _POLLY_SUPPORTED)
        if(_POLLY_SUPPORTED)
            target_compile_options(${target} PRIVATE -mllvm -polly -mllvm -polly-parallel)
            target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
            find_package(OpenMP QUIET)
            message(STATUS "[AutoParallel] Clang Polly parallelization → '${target}'")
        else()
            target_compile_options(${target} PRIVATE -fopenmp-simd)
            message(STATUS "[AutoParallel] Clang: Polly not found — using -fopenmp-simd for '${target}'")
        endif()
    elseif(MSVC)
        target_compile_options(${target} PRIVATE /Qpar /Qpar-report:1)
        message(STATUS "[AutoParallel] MSVC /Qpar auto-parallelizer → '${target}'")
    else()
        message(WARNING "[AutoParallel] Compiler '${CMAKE_CXX_COMPILER_ID}' not supported.")
    endif()
    target_compile_definitions(${target} PRIVATE FEATURE_AUTO_PARALLEL=1)
endfunction()

# ---------------------------------------------------------------------------
# Apply project-wide defaults when global options are ON
# Call after add_executable/add_library via:
#   apply_openmp_defaults(<target>)
# ---------------------------------------------------------------------------
function(apply_openmp_defaults target)
    if(ENABLE_OPENMP)
        enable_openmp(${target})
    endif()
    if(ENABLE_OPENMP_SIMD AND NOT ENABLE_OPENMP)
        enable_openmp_simd(${target})
    endif()
    if(ENABLE_AUTO_PARALLEL)
        enable_auto_parallelization(${target})
    endif()
endfunction()
