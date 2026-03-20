# cmake/StaticAnalyzers.cmake

function(enable_static_analysis)
    if(ENABLE_CLANG_TIDY)
        find_program(CLANG_TIDY_PATH clang-tidy)
        if(CLANG_TIDY_PATH)
            message(STATUS "Found clang-tidy: ${CLANG_TIDY_PATH}")
            set(CMAKE_CXX_CLANG_TIDY "${CLANG_TIDY_PATH};-extra-arg=-Wno-unknown-warning-option" PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "clang-tidy not found.")
        endif()
    endif()

    if(ENABLE_CPPCHECK)
        find_program(CPPCHECK_PATH cppcheck)
        if(CPPCHECK_PATH)
            message(STATUS "Found cppcheck: ${CPPCHECK_PATH}")
            set(CMAKE_CXX_CPPCHECK 
                "${CPPCHECK_PATH};--enable=all;--inconclusive;--force;--inline-suppr;--suppress=missingIncludeSystem" 
                PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "cppcheck not found.")
        endif()
    endif()
endfunction()
