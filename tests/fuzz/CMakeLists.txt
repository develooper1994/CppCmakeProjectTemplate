# tests/fuzz/CMakeLists.txt
# Simple fuzz targets (enabled via -DENABLE_FUZZING=ON)
if(NOT ENABLE_FUZZING)
    return()
endif()

include(Fuzzing)

# Fuzz target for the secure_ops library
add_fuzz_target(fuzz_secure_ops SOURCES fuzz_secure_ops.cpp)
target_link_libraries(fuzz_secure_ops PRIVATE secure_ops)
apply_relaxed_analyzers(fuzz_secure_ops)

# Fuzz target for the new `fuzzable` library
add_fuzz_target(fuzz_fuzzable SOURCES fuzz_fuzzable.cpp)
target_link_libraries(fuzz_fuzzable PRIVATE fuzzable)
# Fuzz harnesses may use patterns that trigger style warnings; run relaxed
# analyzers to collect findings without failing hardened builds.
apply_relaxed_analyzers(fuzz_fuzzable)
