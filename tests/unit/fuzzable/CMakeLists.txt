add_executable(test_fuzzable test_fuzzable.cpp)
target_link_libraries(test_fuzzable PRIVATE fuzzable gtest_main project_feature_flags)
# Tests are allowed to skip heavy clang-tidy/cppcheck enforcement since they may
# intentionally exercise edge cases or test harness patterns that violate
# style rules. Production libraries remain covered by analyzers.
set_target_properties(test_fuzzable PROPERTIES CXX_CLANG_TIDY "" CXX_CPPCHECK "")
add_test(NAME test_fuzzable COMMAND test_fuzzable)
