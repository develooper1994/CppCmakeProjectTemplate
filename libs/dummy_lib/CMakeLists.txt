# libs/dummy_lib/CMakeLists.txt

# --- Stand-alone Build Support ---
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project(dummy_lib LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)

endif()

include(GenerateExportHeader)

set(DUMMY_LIB_CXX_STANDARD "" CACHE STRING
    "C++ standard for dummy_lib only (empty = inherit solution default)")

add_library(dummy_lib)

target_generate_build_info(dummy_lib
    NAMESPACE dummy_lib_info)

target_sources(dummy_lib
    PRIVATE
        src/dummy_lib.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/dummy_lib/dummy_lib.h)

generate_export_header(dummy_lib
    BASE_NAME DUMMY_LIB
    EXPORT_FILE_NAME "${CMAKE_CURRENT_BINARY_DIR}/generated/dummy_lib/dummy_lib_export.h")

target_include_directories(dummy_lib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated>
        $<INSTALL_INTERFACE:include>)

if(DUMMY_LIB_CXX_STANDARD AND NOT DUMMY_LIB_CXX_STANDARD STREQUAL "")
    set_target_properties(dummy_lib PROPERTIES
        CXX_STANDARD          ${DUMMY_LIB_CXX_STANDARD}
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS        OFF
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1)
else()
    set_target_properties(dummy_lib PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1)
endif()

if(ENABLE_COVERAGE)
    enable_code_coverage(dummy_lib)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(dummy_lib)
endif()

if(COMMAND enable_hardening)
    enable_hardening(dummy_lib)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(dummy_lib)
endif()

install(TARGETS dummy_lib
    EXPORT dummy_lib_Targets
    FILE_SET HEADERS)

apply_project_analyzers(dummy_lib)

# Google Benchmark targets
if(ENABLE_BENCHMARKS AND TARGET benchmark::benchmark)
    add_executable(bench_dummy_lib benchmarks/bench_dummy_lib.cpp)
    target_link_libraries(bench_dummy_lib PRIVATE dummy_lib)
    if(COMMAND project_apply_allocator)
        project_apply_allocator(bench_dummy_lib)
    endif()
    target_apply_benchmark_options(bench_dummy_lib)
    message(STATUS "[dummy_lib] Benchmark target 'bench_dummy_lib' registered.")
endif()
