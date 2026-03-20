# cmake/BuildInfo.cmake

function(generate_build_info_header)
    find_package(Git QUIET)
    
    set(GIT_HASH "unknown")
    set(GIT_BRANCH "unknown")
    set(GIT_DESCRIBE "unknown")
    set(GIT_DIRTY "false")

    if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
        execute_process(
            COMMAND ${GIT_EXECUTABLE} rev-parse --abbrev-ref HEAD
            WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
            OUTPUT_VARIABLE GIT_BRANCH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} rev-parse HEAD
            WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
            OUTPUT_VARIABLE GIT_HASH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} describe --tags --always --dirty
            WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
            OUTPUT_VARIABLE GIT_DESCRIBE
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} status --porcelain
            WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
            OUTPUT_VARIABLE GIT_STATUS
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        if(GIT_STATUS)
            set(GIT_DIRTY "true")
        endif()
    endif()

    # Detect Architecture
    if(CMAKE_SIZEOF_VOID_P EQUAL 8)
        set(PROJECT_ARCH "x64")
    else()
        set(PROJECT_ARCH "x86")
    endif()

    if(BUILD_SHARED_LIBS)
        set(LIB_TYPE_STR "Shared")
    else()
        set(LIB_TYPE_STR "Static")
    endif()

    string(TIMESTAMP BUILD_TIMESTAMP "%Y-%m-%d %H:%M:%S UTC" UTC)

    set(BUILD_TYPE ${CMAKE_BUILD_TYPE})
    if(NOT BUILD_TYPE)
        set(BUILD_TYPE "None")
    endif()

    configure_file(
        ${PROJECT_SOURCE_DIR}/cmake/BuildInfo.h.in
        ${PROJECT_BINARY_DIR}/generated/BuildInfo.h
        @ONLY
    )
    
    # Create an interface target for the generated header
    if(NOT TARGET project_build_info)
        add_library(project_build_info INTERFACE)
        target_include_directories(project_build_info INTERFACE ${PROJECT_BINARY_DIR}/generated)
    endif()
endfunction()
