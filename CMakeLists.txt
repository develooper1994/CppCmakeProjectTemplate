cmake_minimum_required(VERSION 3.25)
# -----------------------------------------------------------------------------
# Project Information
# -----------------------------------------------------------------------------
# Read base version from repository `VERSION` file if present. The file may
# contain a build metadata suffix (e.g. 1.2.3+45); we only use the three-part
# base version for CMake's `project(... VERSION 1.3.0)` invocation.
file(READ "${CMAKE_SOURCE_DIR}/VERSION" _cmake_version_content OPTIONAL)
if(DEFINED _cmake_version_content)
    string(STRIP "${_cmake_version_content}" _cmake_version_content)
    string(REGEX MATCH "^[0-9]+\.[0-9]+\.[0-9]+" PROJECT_BASE_VERSION "${_cmake_version_content}")
endif()
if(NOT PROJECT_BASE_VERSION)
    set(PROJECT_BASE_VERSION "0.0.0")
endif()

project(CppCmakeProjectTemplate
    VERSION ${PROJECT_BASE_VERSION}
    DESCRIPTION "Professional C++ CMake Project Template"
    LANGUAGES CXX)

# -----------------------------------------------------------------------------
# Prevent In-Source Builds
# -----------------------------------------------------------------------------
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-source builds are prohibited. Please use a build directory (e.g., build/).")
endif()

# -----------------------------------------------------------------------------
# Project Configuration & Options (Centralized)
# -----------------------------------------------------------------------------
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")
include(CxxStandard)     # Auto-detect C++ standard — must come first
include(ProjectConfigs)

# -----------------------------------------------------------------------------
# Include Modules
# -----------------------------------------------------------------------------
include(FetchContent)
include(ProjectOptions)
include(BuildInfo)
include(CodeCoverage)
include(Sanitizers)
include(Hardening)
include(StaticAnalyzers)
include(EmbeddedUtils)
include(FeatureFlags)
include(LTO)
include(PGO)
include(BuildCache)
include(Benchmark)
include(Allocators)
include(OpenMP)
include(Qt)
include(CUDA)
include(HIP)
include(SYCL)
include(Metal)
include(Reproducibility)
include(Fuzzing)
include(CxxModules)
include(IWYU)

generate_feature_flags()

# INTERFACE library — attach once, all targets inherit FeatureFlags.h
add_library(project_feature_flags INTERFACE)
target_include_directories(project_feature_flags INTERFACE
    $<BUILD_INTERFACE:${FEATURE_FLAGS_INCLUDE_DIR}>
    $<INSTALL_INTERFACE:include>)

if(CMAKE_SYSTEM_NAME STREQUAL "Generic")
    message(STATUS "Embedded System Detected: ${CMAKE_SYSTEM_PROCESSOR}")
    set(ENABLE_QT OFF CACHE BOOL "Qt is disabled for embedded by default" FORCE)
    set(ENABLE_ASAN OFF CACHE BOOL "ASan is disabled for embedded by default" FORCE)
endif()

if(ENABLE_COVERAGE)
    add_coverage_report_target()
endif()

enable_static_analysis()

# -----------------------------------------------------------------------------
# Targets
# -----------------------------------------------------------------------------
add_subdirectory(libs)
add_subdirectory(apps)

if(ENABLE_UNIT_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

if(ENABLE_DOCS)
    add_subdirectory(docs)
endif()

# -----------------------------------------------------------------------------
# Packaging (CPack)
# -----------------------------------------------------------------------------
set(CPACK_PACKAGE_VENDOR "develooper1994")
set(CPACK_PACKAGE_CONTACT "https://github.com/develooper1994")
set(CPACK_RESOURCE_FILE_LICENSE "${PROJECT_SOURCE_DIR}/LICENSE")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "${PROJECT_DESCRIPTION}")

if(WIN32)
    set(CPACK_GENERATOR "ZIP;NSIS")
else()
    set(CPACK_GENERATOR "TGZ;DEB")
endif()

include(CPack)
