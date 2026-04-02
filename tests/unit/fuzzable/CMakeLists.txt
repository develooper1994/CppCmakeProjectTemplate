add_executable(fuzzable_tests fuzzable_test.cpp)
target_link_libraries(fuzzable_tests PRIVATE fuzzable gtest_main project_feature_flags)
if(COMMAND project_apply_allocator)
	project_apply_allocator(fuzzable_tests)
endif()
# Tests are allowed to run with a relaxed analyzer configuration so they do not
# fail hardened builds but analyzers still provide useful feedback.
apply_relaxed_analyzers(fuzzable_tests)
add_test(NAME fuzzable_tests COMMAND fuzzable_tests)
