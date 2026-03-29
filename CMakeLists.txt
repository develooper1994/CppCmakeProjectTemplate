cmake_minimum_required(VERSION 3.25)

# -----------------------------------------------------------------------------
# Project Information
# -----------------------------------------------------------------------------
project(CppCmakeProjectTemplate
    VERSION 1.0.4
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
# Project Configuration & Options (Centralized)
# -----------------------------------------------------------------------------
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")
include(ProjectConfigs)

# -----------------------------------------------------------------------------
# Qt & QML Support (Optional)
# -----------------------------------------------------------------------------
if(ENABLE_QT)
    set(QT_COMPONENTS Widgets)
    if(ENABLE_QML)
        list(APPEND QT_COMPONENTS Quick Qml)
    endif()

    # Try to find Qt6, fallback to Qt5
    find_package(Qt6 COMPONENTS ${QT_COMPONENTS} QUIET)
    if(Qt6_FOUND)
        message(STATUS "Found Qt6")
        set(QT_LIBRARIES Qt6::Widgets)
        if(ENABLE_QML)
            list(APPEND QT_LIBRARIES Qt6::Quick Qt6::Qml)
        endif()
    else()
        find_package(Qt5 COMPONENTS ${QT_COMPONENTS} REQUIRED)
        message(STATUS "Found Qt5")
        set(QT_LIBRARIES Qt5::Widgets)
        if(ENABLE_QML)
            list(APPEND QT_LIBRARIES Qt5::Quick Qt5::Qml)
        endif()
    endif()

    # Required for Qt's meta-build system
    set(CMAKE_AUTOMOC ON)
    set(CMAKE_AUTOUIC ON)
    set(CMAKE_AUTORCC ON)
endif()

# -----------------------------------------------------------------------------
# Include Modules
# -----------------------------------------------------------------------------
include(FetchContent)
include(ProjectOptions)  # Custom module for warnings and compiler options
include(BuildInfo)       # Custom module for Git metadata
include(CodeCoverage)    # Custom module for coverage reporting
include(Sanitizers)      # Custom module for ASan/UBSan/TSan
include(StaticAnalyzers) # Custom module for Clang-Tidy/Cppcheck
include(EmbeddedUtils)   # Custom module for Embedded tools
include(FeatureFlags)    # Generates FeatureFlags.h for C++ compile-time feature detection
generate_feature_flags()

# INTERFACE library — attach once, all targets inherit FeatureFlags.h
add_library(project_feature_flags INTERFACE)
target_include_directories(project_feature_flags INTERFACE
    $<BUILD_INTERFACE:${FEATURE_FLAGS_INCLUDE_DIR}>
    $<INSTALL_INTERFACE:include>
)

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
# Documentation (Doxygen)
# -----------------------------------------------------------------------------
find_package(Doxygen QUIET)
if(DOXYGEN_FOUND)
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/docs/Doxyfile.in" "${CMAKE_CURRENT_BINARY_DIR}/Doxyfile" @ONLY)
    add_custom_target(docs
        COMMAND ${DOXYGEN_EXECUTABLE} "${CMAKE_CURRENT_BINARY_DIR}/Doxyfile"
        WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
        COMMENT "Generating API documentation with Doxygen"
        VERBATIM
    )
endif()
# Avoid using global defines; prefer target-based.
# However, we can set some project-wide defaults here if needed.

# -----------------------------------------------------------------------------
# External Dependencies (Isolated)
# -----------------------------------------------------------------------------
# add_subdirectory(external SYSTEM) # Future use

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
