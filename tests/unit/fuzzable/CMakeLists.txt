add_executable(fuzzable_tests fuzzable_test.cpp)

target_link_libraries(fuzzable_tests
    PRIVATE
        fuzzable
        project_feature_flags
        GTest::gtest_main)

if(COMMAND project_apply_allocator)
    project_apply_allocator(fuzzable_tests)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(fuzzable_tests)
endif()

apply_relaxed_analyzers(fuzzable_tests)

add_test(NAME fuzzable_tests COMMAND fuzzable_tests)
