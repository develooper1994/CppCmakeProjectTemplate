# tests/fuzz/CMakeLists.txt
# Simple fuzz targets (enabled via -DENABLE_FUZZING=ON)
if(NOT ENABLE_FUZZING)
    return()
endif()

include(Fuzzing)

# Example fuzz target that exercises dummy_lib API.
add_fuzz_target(fuzz_dummy_lib SOURCES dummy_fuzzer.cpp)
# Link with library under test
target_link_libraries(fuzz_dummy_lib PRIVATE dummy_lib)

# Fuzz target for the new `fuzzable` library
add_fuzz_target(fuzz_fuzzable SOURCES fuzz_fuzzable.cpp)
target_link_libraries(fuzz_fuzzable PRIVATE fuzzable)
# Fuzz harnesses may use patterns that trigger style warnings; run relaxed
# analyzers to collect findings without failing hardened builds.
apply_relaxed_analyzers(fuzz_fuzzable)
