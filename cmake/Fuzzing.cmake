# cmake/Fuzzing.cmake
# Extended fuzzing support for libFuzzer and AFL++ targets.
# Provides `add_fuzz_target(<name> SOURCES ...)` which sets suitable
# compile/link flags when fuzzing is enabled. Supports both libFuzzer
# (default) and AFL++ (llvm-mode) when `-DENABLE_AFL=ON` or env var
# `ENABLE_AFL=1` is set at configure time. For best AFL++ results, use
# `CC=afl-clang-fast CXX=afl-clang-fast++` when configuring.

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

    # Decide whether to enable AFL (llvm-mode) instrumentation
    if(DEFINED ENABLE_AFL AND ENABLE_AFL)
        set(_use_afl TRUE)
    elseif(DEFINED ENV{ENABLE_AFL} AND NOT "$ENV{ENABLE_AFL}" STREQUAL "")
        set(_use_afl TRUE)
    else()
        set(_use_afl FALSE)
    endif()

    if(_use_afl)
        message(STATUS "Configuring ${name} for AFL++ (llvm-mode). For best results configure with CC=afl-clang-fast CXX=afl-clang-fast++")
        if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
            # LLVM-mode instrumentation flags (works with AFL++ and clang-fast)
            target_compile_options(${name} PRIVATE -g -O1 -fno-omit-frame-pointer -fsanitize-coverage=trace-pc-guard,indirect-calls)
            target_link_options(${name} PRIVATE -fsanitize-coverage=trace-pc-guard,indirect-calls)
        else()
            message(WARNING "AFL flags not configured for compiler: ${CMAKE_CXX_COMPILER_ID}")
        endif()
        target_compile_definitions(${name} PRIVATE FUZZ_AFL=1)
    else()
        if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
            # Default: libFuzzer-friendly flags
            target_compile_options(${name} PRIVATE -g -O1 -fno-omit-frame-pointer)
            target_compile_options(${name} PRIVATE -fsanitize=fuzzer,address)
            target_link_options(${name} PRIVATE -fsanitize=fuzzer,address)
        else()
            message(WARNING "Fuzzing flags not configured for compiler: ${CMAKE_CXX_COMPILER_ID}")
        endif()
        target_compile_definitions(${name} PRIVATE FUZZ_LIBFUZZER=1)
    endif()

    # Keep fuzz targets out of regular test runs by default
    set_target_properties(${name} PROPERTIES EXCLUDE_FROM_ALL TRUE)
endfunction()
