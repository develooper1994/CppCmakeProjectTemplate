# cmake/StaticAnalyzers.cmake

function(enable_static_analysis)
    if(ENABLE_CLANG_TIDY)
        find_program(CLANG_TIDY_PATH clang-tidy)
        if(CLANG_TIDY_PATH)
            message(STATUS "Found clang-tidy: ${CLANG_TIDY_PATH}")
            set(TIDY_FLAGS "${CLANG_TIDY_PATH};-extra-arg=-Wno-unknown-warning-option")
            # Restrict clang-tidy analysis to project source directories to avoid
            # analyzing bundled third-party code (e.g., deps under build/_deps).
            # Do NOT include generated headers in the header-filter (they are
            # machine-generated and often violate style rules). Instead, add the
            # generated include path so clang-tidy can resolve symbols without
            # analyzing the generated files themselves.
            list(APPEND TIDY_FLAGS "-header-filter=^${CMAKE_SOURCE_DIR}/(libs|apps|tests|gui_app|main_app|extension)/")
            list(APPEND TIDY_FLAGS "-extra-arg=-I${CMAKE_BINARY_DIR}/generated")

            # Treat warnings as errors if WARNING_LEVEL is ERROR
            if(WARNING_LEVEL STREQUAL "ERROR" OR ENABLE_WERROR)
                list(APPEND TIDY_FLAGS "-warnings-as-errors=*")
            endif()

            set(CMAKE_CXX_CLANG_TIDY "${TIDY_FLAGS}" PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "clang-tidy not found.")
        endif()
    endif()

    if(ENABLE_CPPCHECK)
        find_program(CPPCHECK_PATH cppcheck)
        if(CPPCHECK_PATH)
            message(STATUS "Found cppcheck: ${CPPCHECK_PATH}")
            set(CPPCHECK_ARGS "${CPPCHECK_PATH};--enable=all;--inconclusive;--force;--inline-suppr;--suppress=missingIncludeSystem")
            if(ENABLE_WERROR)
                list(APPEND CPPCHECK_ARGS "--error-exitcode=1")
            endif()
            set(CMAKE_CXX_CPPCHECK "${CPPCHECK_ARGS}" PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "cppcheck not found.")
        endif()
    endif()
endfunction()
