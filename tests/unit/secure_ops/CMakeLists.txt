add_executable(secure_ops_tests secure_ops_test.cpp)

target_link_libraries(secure_ops_tests
    PRIVATE
        secure_ops
        project_feature_flags
        GTest::gtest_main)

if(COMMAND project_apply_allocator)
    project_apply_allocator(secure_ops_tests)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(secure_ops_tests)
endif()

apply_relaxed_analyzers(secure_ops_tests)

add_test(NAME secure_ops_tests COMMAND secure_ops_tests)
