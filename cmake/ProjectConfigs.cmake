# cmake/ProjectConfigs.cmake
# Centralized configuration for all project-wide CMake defaults

# --- Build Options ---
option(BUILD_SHARED_LIBS    "Build libraries as shared"          OFF)
option(ENABLE_UNITY_BUILD   "Enable unity builds"                OFF)
option(ENABLE_WERROR        "Treat warnings as errors"           OFF)
option(ENABLE_UNIT_TESTS    "Build unit tests"                   ON)
option(ENABLE_DOCS          "Build documentation"                OFF)
option(ENABLE_COVERAGE      "Enable code coverage reporting"     OFF)

# --- Quality & Security Options ---
option(ENABLE_ASAN          "Enable Address Sanitizer"           OFF)
option(ENABLE_UBSAN         "Enable Undefined Behavior Sanitizer" OFF)
option(ENABLE_TSAN          "Enable Thread Sanitizer"            OFF)
option(ENABLE_HARDENING     "Enable security hardening flags"    OFF)
option(ENABLE_CLANG_TIDY    "Enable Clang-Tidy static analysis"  OFF)
option(ENABLE_CPPCHECK      "Enable Cppcheck static analysis"    OFF)
option(ENABLE_GCC_ANALYZER "Enable GCC -fanalyzer static analysis" OFF)
option(ENABLE_MSVC_ANALYZE "Enable MSVC /analyze static analysis" OFF)
option(ENABLE_FUZZING      "Enable fuzz testing targets"        OFF)
# NOTE: Valgrind support is planned (ENABLE_VALGRIND). Currently not implemented.
# When enabled it would wrap ctest runs with valgrind --leak-check=full.

# --- Performance & Optimization Options ---
option(ENABLE_LTO               "Enable Link-Time Optimization"             OFF)
option(ENABLE_CCACHE            "Enable compiler caching (ccache/sccache)"  ON)
option(ENABLE_BENCHMARKS        "Build Google Benchmark targets"             OFF)
option(ENABLE_VEC_REPORT        "Emit vectorization info (-fopt-info-vec / -Rpass)" OFF)
set(ENABLE_ALLOCATOR "default" CACHE STRING
    "Allocator backend (default|mimalloc|jemalloc|tcmalloc)")
set_property(CACHE ENABLE_ALLOCATOR PROPERTY STRINGS default mimalloc jemalloc tcmalloc)
option(ENABLE_ALLOCATOR_OVERRIDE_ALL
    "Apply selected allocator backend to all executables/benchmarks"
    OFF)

# --- Parallelization Options ---
option(ENABLE_OPENMP        "Enable OpenMP threading (links libgomp)"         OFF)
option(ENABLE_OPENMP_SIMD   "Enable OpenMP SIMD-only (no runtime dep)"         OFF)
option(ENABLE_AUTO_PARALLEL "Enable compiler auto-parallelization of loops"    OFF)

# --- Qt Options ---
option(ENABLE_QT            "Enable Qt5/Qt6 support (requires Qt install)"     OFF)
option(ENABLE_QML           "Enable Qt QML/Quick (requires ENABLE_QT)"         OFF)

# --- CUDA / GPU Options ---
option(ENABLE_CUDA          "Enable CUDA language and GPU target support"       OFF)

# --- AMD HIP / ROCm Options ---
option(ENABLE_HIP           "Enable AMD HIP language and GPU target support (requires ROCm)" OFF)

# --- SYCL Options ---
option(ENABLE_SYCL          "Enable Intel SYCL / DPC++ support"                OFF)

# --- Metal Options ---
option(ENABLE_METAL         "Enable Apple Metal compute support (macOS only)"   OFF)

# --- Master list — drives FeatureFlags.cmake dynamic generation ---
# Add new options here; FeatureFlags.h will update automatically on next cmake run.
set(PROJECT_ALL_OPTIONS
    # Tests
    UNIT_TESTS GTEST CATCH2 BOOST_TEST
    # Sanitizers
    ASAN UBSAN TSAN
    # Analysis / coverage
    CLANG_TIDY CPPCHECK GCC_ANALYZER MSVC_ANALYZE COVERAGE
    # Performance
    LTO BENCHMARKS VEC_REPORT
    # Parallelization
    OPENMP OPENMP_SIMD AUTO_PARALLEL
    # Frameworks
    QT QML CUDA HIP SYCL METAL BOOST
    # Misc
    DOCS
    CACHE STRING "All ENABLE_* toggle options (drives FeatureFlags.h generation)" FORCE
)

# Apply vectorization report flags globally when requested.
# Per-target override: target_compile_options(<tgt> PRIVATE ${_VEC_FLAGS})
if(ENABLE_VEC_REPORT)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        set(_VEC_FLAGS
            -Rpass=loop-vectorize
            -Rpass-missed=loop-vectorize
            -Rpass-analysis=loop-vectorize)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        set(_VEC_FLAGS -fopt-info-vec-optimized -fopt-info-vec-missed)
    else()
        set(_VEC_FLAGS "")
    endif()
    if(_VEC_FLAGS)
        add_compile_options(${_VEC_FLAGS})
        message(STATUS "[VecReport] Vectorization info enabled: ${_VEC_FLAGS}")
    endif()
endif()

# --- Test Framework Options ---
# Only one framework should be ON at a time per build.
option(ENABLE_GTEST         "Use GoogleTest as test framework"   ON)
option(ENABLE_CATCH2        "Use Catch2 as test framework"       OFF)
option(ENABLE_BOOST_TEST    "Use Boost.Test as test framework"   OFF)
# QTest is enabled automatically when ENABLE_QT=ON (no separate option needed)

# --- Qt & GUI Options ---
# Note: ENABLE_QT and ENABLE_QML are declared above — these are aliases kept
# for backward compatibility with older presets (CMake ignores re-declarations
# when the value is already cached).

# --- Boost Options ---
option(ENABLE_BOOST         "Enable Boost libraries"             OFF)
set(BOOST_COMPONENTS "" CACHE STRING
    "Semicolon-separated Boost components to find (e.g. filesystem;system)")

# --- Compiler Defaults ---
# C++ standard is auto-detected by cmake/CxxStandard.cmake (included before this
# file in CMakeLists.txt). The detected value is already in the cache as
# CMAKE_CXX_STANDARD. We only set a fallback here in case CxxStandard.cmake
# was skipped or the user cleared the cache manually.
#
# Override: -DCMAKE_CXX_STANDARD=20  or set in a CMakePresets.json cacheVariable.
# Per-target: set_target_properties(<t> PROPERTIES CXX_STANDARD 20)
if(NOT DEFINED CACHE{CMAKE_CXX_STANDARD})
    # CxxStandard.cmake was not loaded — apply a safe baseline
    message(WARNING
        "[CxxStd] cmake/CxxStandard.cmake was not included. "
        "Defaulting to C++17. Include CxxStandard before ProjectConfigs "
        "in CMakeLists.txt for full auto-detection.")
    set(CMAKE_CXX_STANDARD 17 CACHE STRING
        "C++ standard (14|17|20|23) — set cmake/CxxStandard.cmake for auto-detect")
    set_property(CACHE CMAKE_CXX_STANDARD PROPERTY STRINGS 11 14 17 20 23)
endif()

set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS        OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- MSVC Runtime Consistency ---
# Ensures all targets (including FetchContent deps like GTest) use the same CRT.
# /MD  (MultiThreadedDLL)      when BUILD_SHARED_LIBS=ON  or DLL build
# /MT  (MultiThreaded)         when BUILD_SHARED_LIBS=OFF (static build)
# Without this, mixing /MT and /MD causes linker errors (LNK2038).
if(MSVC)
    if(BUILD_SHARED_LIBS)
        set(CMAKE_MSVC_RUNTIME_LIBRARY
            "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL"
            CACHE STRING "MSVC runtime library" FORCE)
    else()
        set(CMAKE_MSVC_RUNTIME_LIBRARY
            "MultiThreaded$<$<CONFIG:Debug>:Debug>"
            CACHE STRING "MSVC runtime library" FORCE)
    endif()
    # GTest must follow the same CRT — set before FetchContent_MakeAvailable
    set(gtest_force_shared_crt ${BUILD_SHARED_LIBS} CACHE BOOL "" FORCE)
endif()

# --- Boost (optional) ---
if(ENABLE_BOOST)
    if(BOOST_COMPONENTS)
        find_package(Boost REQUIRED COMPONENTS ${BOOST_COMPONENTS})
    else()
        find_package(Boost REQUIRED)
    endif()
    if(Boost_FOUND)
        message(STATUS "Found Boost ${Boost_VERSION}")
    endif()
endif()

# --- Project Paths ---
set(PROJECT_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated"
    CACHE PATH "Directory for generated files")
file(MAKE_DIRECTORY ${PROJECT_GENERATED_DIR})
