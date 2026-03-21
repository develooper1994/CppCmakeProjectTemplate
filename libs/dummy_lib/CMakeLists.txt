# libs/dummy_lib/CMakeLists.txt

# --- Stand-alone Build Support ---
# Allows this library to be built independently (e.g. via FetchContent from another project)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project(DummyLib VERSION 1.0.0 LANGUAGES CXX)
    
    # Try to load project configs if available
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)
endif()

include(GenerateExportHeader)

# Per-library C++ standard override.
# Default: inherits CMAKE_CXX_STANDARD (solution-wide).
# Override: -DDUMMY_LIB_CXX_STANDARD=20
set(DUMMY_LIB_CXX_STANDARD "" CACHE STRING
    "C++ standard for dummy_lib only (empty = inherit solution default)")

add_library(dummy_lib)

# Generate specific build info for this library
# This proves libraries can have independent versioning
target_generate_build_info(dummy_lib 
    NAMESPACE dummy_lib_info 
    PROJECT_VERSION "2.5.0"
)

target_sources(dummy_lib 
    PRIVATE 
        src/greet.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/dummy_lib/greet.h
)

# Generate export header for Windows/DLL support
# Place it in the binary directory to keep source clean
generate_export_header(dummy_lib
    BASE_NAME DUMMY_LIB
    EXPORT_FILE_NAME "${CMAKE_CURRENT_BINARY_DIR}/generated/dummy_lib/dummy_lib_export.h"
)

target_include_directories(dummy_lib 
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated> # Build tree includes
        $<INSTALL_INTERFACE:include>
)

# Professional visibility settings (Hidden by default)
# CXX_STANDARD can be overridden per-library via DUMMY_LIB_CXX_STANDARD cache var.
if(DUMMY_LIB_CXX_STANDARD AND NOT DUMMY_LIB_CXX_STANDARD STREQUAL "")
    set_target_properties(dummy_lib PROPERTIES
        CXX_STANDARD          ${DUMMY_LIB_CXX_STANDARD}
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS        OFF
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1
    )
else()
    set_target_properties(dummy_lib PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1
    )
endif()

if(ENABLE_COVERAGE)
    enable_code_coverage(dummy_lib)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(dummy_lib)
endif()

# Apply project-wide warnings
if(COMMAND set_project_warnings)
    set_project_warnings(dummy_lib)
endif()

# Install rules
install(TARGETS dummy_lib
    EXPORT dummy_lib_Targets
    FILE_SET HEADERS
)
