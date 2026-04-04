# tests/fuzz/CMakeLists.txt
if(NOT ENABLE_FUZZING)
    return()
endif()

include(Fuzzing)

add_fuzz_target(fuzz_fuzzable SOURCES fuzz_fuzzable.cpp)
target_link_libraries(fuzz_fuzzable PRIVATE fuzzable)
apply_relaxed_analyzers(fuzz_fuzzable)

add_fuzz_target(fuzz_secure_ops SOURCES fuzz_secure_ops.cpp)
target_link_libraries(fuzz_secure_ops PRIVATE secure_ops)
apply_relaxed_analyzers(fuzz_secure_ops)
