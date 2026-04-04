add_executable(dummy_lib_tests dummy_lib_test.cpp)

target_link_libraries(dummy_lib_tests
    PRIVATE
        dummy_lib
        project_feature_flags
        GTest::gtest_main)

if(COMMAND project_apply_allocator)
    project_apply_allocator(dummy_lib_tests)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(dummy_lib_tests)
endif()

apply_relaxed_analyzers(dummy_lib_tests)

add_test(NAME dummy_lib_tests COMMAND dummy_lib_tests)
