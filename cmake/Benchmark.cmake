# cmake/Benchmark.cmake
# Google Benchmark integration via FetchContent.
# Activated when ENABLE_BENCHMARKS=ON (set in ProjectConfigs.cmake).
#
# Usage in a library/app CMakeLists.txt:
#
#   if(ENABLE_BENCHMARKS)
#       add_executable(my_bench benchmarks/bench_my.cpp)
#       target_link_libraries(my_bench PRIVATE benchmark::benchmark my_lib)
#       target_apply_benchmark_options(my_bench)
#   endif()

include(FetchContent)

if(NOT ENABLE_BENCHMARKS)
    return()
endif()

# Avoid re-fetching if already in the dependency tree
if(TARGET benchmark::benchmark)
    return()
endif()

message(STATUS "[Benchmark] Fetching google/benchmark ...")

set(BENCHMARK_ENABLE_TESTING       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_ENABLE_INSTALL       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_ENABLE_GTEST_TESTS   OFF CACHE BOOL "" FORCE)
set(BENCHMARK_INSTALL_DOCS         OFF CACHE BOOL "" FORCE)
set(BENCHMARK_USE_BUNDLED_GTEST    OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
    googlebenchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG        v1.8.3
    GIT_SHALLOW    TRUE
)

FetchContent_MakeAvailable(googlebenchmark)

# Suppress warnings in benchmark headers for all compilers
if(TARGET benchmark)
    target_compile_options(benchmark PRIVATE
        $<$<CXX_COMPILER_ID:GNU,Clang>:-w>
        $<$<CXX_COMPILER_ID:MSVC>:/w>
    )
endif()

# ---------------------------------------------------------------------------
# Helper function: apply benchmark best-practice compiler flags to a target.
# Enables LTO-friendly settings and disables sanitizers for reliable timing.
# ---------------------------------------------------------------------------
function(target_apply_benchmark_options target)
    target_compile_options(${target} PRIVATE
        $<$<CXX_COMPILER_ID:GNU,Clang>:-O3 -DNDEBUG>
        $<$<CXX_COMPILER_ID:MSVC>:/O2 /DNDEBUG>
    )

    # Link benchmark and pthread
    target_link_libraries(${target} PRIVATE
        benchmark::benchmark
        benchmark::benchmark_main
        $<$<NOT:$<PLATFORM_ID:Windows>>:pthread>
    )

    # Name benchmark executables clearly
    set_target_properties(${target} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/benchmarks"
        OUTPUT_NAME              "${target}"
    )
endfunction()

message(STATUS "[Benchmark] google/benchmark ready — use target_apply_benchmark_options()")
