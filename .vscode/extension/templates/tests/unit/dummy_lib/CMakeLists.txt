add_executable(dummy_lib_tests greet_test.cpp)

target_link_libraries(dummy_lib_tests 
    PRIVATE 
        dummy_lib 
        GTest::gtest_main
)

# Apply project-wide warnings
set_project_warnings(dummy_lib_tests)

add_test(NAME dummy_lib_tests COMMAND dummy_lib_tests)
