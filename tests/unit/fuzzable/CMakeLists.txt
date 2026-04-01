add_executable(test_fuzzable test_fuzzable.cpp)
target_link_libraries(test_fuzzable PRIVATE fuzzable gtest_main project_feature_flags)
# Tests are allowed to run with a relaxed analyzer configuration so they do not
# fail hardened builds but analyzers still provide useful feedback.
apply_relaxed_analyzers(test_fuzzable)
add_test(NAME test_fuzzable COMMAND test_fuzzable)
