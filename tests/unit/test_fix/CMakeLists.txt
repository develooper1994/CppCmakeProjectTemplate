add_executable(test_fix_tests test_fix_test.cpp)
target_link_libraries(test_fix_tests PRIVATE GTest::gtest_main)
add_test(NAME test_fix_tests COMMAND test_fix_tests)