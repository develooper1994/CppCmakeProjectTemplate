# cmake/CodeCoverage.cmake

function(enable_code_coverage target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES ".*Clang")
        message(STATUS "Enabling code coverage for target: ${target}")
        target_compile_options(${target} PRIVATE --coverage -fno-inline -fno-inline-small-functions -fno-default-inline)
        target_link_options(${target} PUBLIC --coverage)
    else()
        message(AUTHOR_WARNING "Code coverage is only supported for GCC and Clang.")
    endif()
endfunction()

function(add_coverage_report_target)
    find_program(LCOV_PATH lcov)
    find_program(GENHTML_PATH genhtml)

    if(LCOV_PATH AND GENHTML_PATH)
        add_custom_target(coverage_report
            COMMAND ${LCOV_PATH} --directory . --capture --output-file coverage.info
            COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' '*/_deps/*' '*/tests/*' --output-file coverage.info.cleaned
            COMMAND ${GENHTML_PATH} coverage.info.cleaned --output-directory coverage_report
            COMMAND ${CMAKE_COMMAND} -E echo "Coverage report generated in: ${CMAKE_BINARY_DIR}/coverage_report/index.html"
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating HTML coverage report..."
        )
    else()
        message(AUTHOR_WARNING "lcov or genhtml not found. Coverage report target will not be available.")
    endif()
endfunction()
