# cmake/CodeCoverage.cmake

function(enable_code_coverage target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES ".*Clang")
        message(STATUS "Enabling code coverage for target: ${target}")
        target_compile_options(${target} PRIVATE --coverage -fno-inline -fno-inline-small-functions -fno-default-inline)
        target_link_options(${target} PUBLIC --coverage)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        message(STATUS "Enabling code coverage for target (MSVC): ${target} — collect via OpenCppCoverage at runtime")
        # MSVC has no compile-time coverage instrumentation flag.
        # Coverage is collected at runtime using OpenCppCoverage.
        # We enable debug info to get accurate line mapping.
        target_compile_options(${target} PRIVATE /Zi)
        target_link_options(${target} PUBLIC /DEBUG)
    else()
        message(AUTHOR_WARNING "Code coverage is only supported for GCC, Clang, and MSVC.")
    endif()
endfunction()

function(add_coverage_report_target)
    if(CMAKE_CXX_COMPILER_ID MATCHES ".*Clang")
        # LLVM coverage: llvm-profdata + llvm-cov
        find_program(LLVM_PROFDATA_PATH llvm-profdata)
        find_program(LLVM_COV_PATH llvm-cov)
        if(LLVM_PROFDATA_PATH AND LLVM_COV_PATH)
            add_custom_target(coverage_report
                COMMAND ${LLVM_PROFDATA_PATH} merge -sparse default.profraw -o default.profdata
                COMMAND ${LLVM_COV_PATH} show $<TARGET_FILE:${PROJECT_NAME}> -instr-profile=default.profdata -format=html -output-dir=coverage_report
                COMMAND ${CMAKE_COMMAND} -E echo "LLVM coverage report generated in: ${CMAKE_BINARY_DIR}/coverage_report/index.html"
                WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
                COMMENT "Generating LLVM HTML coverage report..."
            )
            return()
        endif()
        # Fall through to lcov if llvm tools not found
    endif()

    if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        find_program(OPENCPPCOVERAGE_PATH OpenCppCoverage)
        if(OPENCPPCOVERAGE_PATH)
            add_custom_target(coverage_report
                COMMAND ${OPENCPPCOVERAGE_PATH} --sources ${CMAKE_SOURCE_DIR} --export_type=html:coverage_report -- $<TARGET_FILE:${PROJECT_NAME}>
                COMMAND ${CMAKE_COMMAND} -E echo "OpenCppCoverage report generated in: ${CMAKE_BINARY_DIR}/coverage_report/"
                WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
                COMMENT "Generating OpenCppCoverage HTML report..."
            )
        else()
            message(AUTHOR_WARNING "OpenCppCoverage not found. Install from https://github.com/OpenCppCoverage/OpenCppCoverage")
        endif()
        return()
    endif()

    # GCC fallback: lcov + genhtml
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
