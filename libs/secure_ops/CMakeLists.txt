# libs/secure_ops/CMakeLists.txt

# --- Stand-alone Build Support ---
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project(secure_ops LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)
    include(Fuzzing OPTIONAL)
endif()

add_library(secure_ops)

target_generate_build_info(secure_ops
    NAMESPACE secure_ops_info)

target_sources(secure_ops
    PRIVATE
        src/secure_ops.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/secure_ops/secure_ops.h)

target_include_directories(secure_ops
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated>
        $<INSTALL_INTERFACE:include>)

set_target_properties(secure_ops PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1)

if(ENABLE_COVERAGE)
    enable_code_coverage(secure_ops)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(secure_ops)
endif()

if(COMMAND enable_hardening)
    enable_hardening(secure_ops)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(secure_ops)
endif()

install(TARGETS secure_ops
    EXPORT secure_ops_Targets
    FILE_SET HEADERS)

apply_project_analyzers(secure_ops)
