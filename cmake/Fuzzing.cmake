# cmake/Fuzzing.cmake
# Minimal fuzzing support for libFuzzer/afl++ targets.
# Provides `add_fuzz_target(<name> SOURCES ...)` which sets suitable
# compile/link flags when ENABLE_FUZZING is enabled.

function(add_fuzz_target name)
    cmake_parse_arguments(_fuzz "" "" "SOURCES" ${ARGN})
    add_executable(${name} ${_fuzz_SOURCES})

    # Link with common project libs if they exist (caller may override)
    target_link_libraries(${name} PRIVATE project_feature_flags)

    # Allow per-target override: <TARGET>_ENABLE_FUZZING (ON/OFF). If explicitly
    # disabled, create executable but do not add fuzzer instrumentation.
    string(TOUPPER ${name} _tname_upper)
    set(_tgt_fuzz_var "${_tname_upper}_ENABLE_FUZZING")
    if(DEFINED ${_tgt_fuzz_var})
        if(NOT ${${_tgt_fuzz_var}})
            message(STATUS "Fuzzing explicitly disabled for target ${name}")
            set_target_properties(${name} PROPERTIES EXCLUDE_FROM_ALL TRUE)
            return()
        endif()
    endif()

    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        # Basic libFuzzer flags: address sanitizer + fuzzer runtime
        target_compile_options(${name} PRIVATE -g -O1 -fno-omit-frame-pointer)
        # Prefer using libFuzzer (Clang) or GCC's fuzzer sanitizer
        target_compile_options(${name} PRIVATE -fsanitize=fuzzer,address)
        target_link_options(${name} PRIVATE -fsanitize=fuzzer,address)
    else()
        message(WARNING "Fuzzing flags not configured for compiler: ${CMAKE_CXX_COMPILER_ID}")
    endif()

    # Keep fuzz targets out of regular test runs by default
    set_target_properties(${name} PROPERTIES EXCLUDE_FROM_ALL TRUE)
endfunction()
