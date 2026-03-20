cmake_minimum_required(VERSION 3.25)

# -----------------------------------------------------------------------------
# Project Information
# -----------------------------------------------------------------------------
project(CppCmakeProjectTemplate
    VERSION 0.1.0
    DESCRIPTION "Professional Modern C++ / CMake Project Template"
    LANGUAGES CXX
)

# -----------------------------------------------------------------------------
# Prevent In-Source Builds
# -----------------------------------------------------------------------------
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-source builds are prohibited. Please use a build directory (e.g., build/).")
endif()

# -----------------------------------------------------------------------------
# Project Configuration & Options
# -----------------------------------------------------------------------------
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_SHARED_LIBS "Build libraries as shared" OFF)
option(ENABLE_UNITY_BUILD "Enable unity builds" OFF)
option(ENABLE_WERROR "Treat warnings as errors" ON)
option(ENABLE_UNIT_TESTS "Build unit tests" ON)
option(ENABLE_DOCS "Build documentation" OFF)
option(ENABLE_COVERAGE "Enable code coverage reporting" OFF)

# -----------------------------------------------------------------------------
# Module Paths
# -----------------------------------------------------------------------------
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

# -----------------------------------------------------------------------------
# Include Modules
# -----------------------------------------------------------------------------
include(FetchContent)
include(ProjectOptions) # Custom module for warnings and compiler options
include(BuildInfo)      # Custom module for Git metadata
include(CodeCoverage)   # Custom module for coverage reporting

if(ENABLE_COVERAGE)
    add_coverage_report_target()
endif()

# -----------------------------------------------------------------------------
# Global Compile Definitions
# -----------------------------------------------------------------------------
# Avoid using global defines; prefer target-based. 
# However, we can set some project-wide defaults here if needed.

# -----------------------------------------------------------------------------
# External Dependencies (Isolated)
# -----------------------------------------------------------------------------
# add_subdirectory(external SYSTEM) # Future use

# -----------------------------------------------------------------------------
# Build Info Generator
# -----------------------------------------------------------------------------
generate_build_info_header()

# -----------------------------------------------------------------------------
# Project Targets
# -----------------------------------------------------------------------------
add_subdirectory(libs)
add_subdirectory(apps)

# -----------------------------------------------------------------------------
# Testing (CTest)
# -----------------------------------------------------------------------------
if(ENABLE_UNIT_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# -----------------------------------------------------------------------------
# Documentation
# -----------------------------------------------------------------------------
if(ENABLE_DOCS)
    add_subdirectory(docs)
endif()
