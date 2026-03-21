# cmake/BuildInfo.cmake

function(target_generate_build_info target)
    set(options)
    set(oneValueArgs NAMESPACE PROJECT_NAME PROJECT_VERSION)
    set(multiValueArgs)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # 1. Defaults
    if(NOT ARG_NAMESPACE)
        set(BUILD_INFO_NAMESPACE "${target}_build_info")
    else()
        set(BUILD_INFO_NAMESPACE "${ARG_NAMESPACE}")
    endif()

    if(NOT ARG_PROJECT_NAME)
        set(PROJECT_NAME "${PROJECT_NAME}")
    else()
        set(PROJECT_NAME "${ARG_PROJECT_NAME}")
    endif()

    if(NOT ARG_PROJECT_VERSION)
        set(PROJECT_VERSION "${PROJECT_VERSION}")
    else()
        set(PROJECT_VERSION "${ARG_PROJECT_VERSION}")
    endif()

    # 2. Git Metadata
    # Always use PROJECT_SOURCE_DIR (repo root) — not CMAKE_CURRENT_SOURCE_DIR,
    # which points to a sub-library directory that has no .git folder.
    find_package(Git QUIET)
    if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
        execute_process(
            COMMAND ${GIT_EXECUTABLE} describe --tags --always --dirty
            WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
            OUTPUT_VARIABLE GIT_DESCRIBE
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} rev-parse HEAD
            WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
            OUTPUT_VARIABLE GIT_HASH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} rev-parse --abbrev-ref HEAD
            WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
            OUTPUT_VARIABLE GIT_BRANCH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
        )
        execute_process(
            COMMAND ${GIT_EXECUTABLE} diff --quiet
            WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
            RESULT_VARIABLE GIT_STATUS
            ERROR_QUIET
        )
        if(GIT_STATUS EQUAL 0)
            set(GIT_DIRTY "false")
        else()
            set(GIT_DIRTY "true")
        endif()
    else()
        # Fallback if no git or not a repo
        set(GIT_DESCRIBE "N/A")
        set(GIT_HASH "N/A")
        set(GIT_BRANCH "N/A")
        set(GIT_DIRTY "false")
    endif()

    # 3. System & Build Metadata
    if(CMAKE_SIZEOF_VOID_P EQUAL 8)
        set(PROJECT_ARCH "x64")
    else()
        set(PROJECT_ARCH "x86")
    endif()

    # Check actual target property for shared/static
    get_target_property(target_type ${target} TYPE)
    if(target_type STREQUAL "SHARED_LIBRARY" OR target_type STREQUAL "MODULE_LIBRARY")
        set(LIB_TYPE_STR "Shared")
    elseif(target_type STREQUAL "STATIC_LIBRARY")
        set(LIB_TYPE_STR "Static")
    elseif(target_type STREQUAL "EXECUTABLE")
        set(LIB_TYPE_STR "Executable")
    else()
        set(LIB_TYPE_STR "Unknown")
    endif()

    string(TIMESTAMP BUILD_TIMESTAMP "%Y-%m-%d %H:%M:%S UTC" UTC)
    set(BUILD_TYPE ${CMAKE_BUILD_TYPE})
    if(NOT BUILD_TYPE)
        set(BUILD_TYPE "None")
    endif()

    # 4. Generate Header
    set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated/${target}")
    file(MAKE_DIRECTORY "${GENERATED_DIR}")
    
    set(HEADER_FILE "${GENERATED_DIR}/BuildInfo.h")
    configure_file("${PROJECT_SOURCE_DIR}/cmake/BuildInfo.h.in" "${HEADER_FILE}" @ONLY)

    # 5. Link Interface
    # Use a specific include directory so <BuildInfo.h> can be found by this target
    target_include_directories(${target} PUBLIC 
        $<BUILD_INTERFACE:${GENERATED_DIR}>
        $<INSTALL_INTERFACE:include>
    )

    message(STATUS "BuildInfo generated for target: ${target} (Namespace: ${BUILD_INFO_NAMESPACE}, Version: ${PROJECT_VERSION})")

endfunction()
