# cmake/ProjectConfigs.cmake
# Centralized configuration for all project-wide CMake defaults

# --- Build Options ---
option(BUILD_SHARED_LIBS "Build libraries as shared" OFF)
option(ENABLE_UNITY_BUILD "Enable unity builds" OFF)
option(ENABLE_WERROR "Treat warnings as errors" ON)
option(ENABLE_UNIT_TESTS "Build unit tests" ON)
option(ENABLE_DOCS "Build documentation" OFF)
option(ENABLE_COVERAGE "Enable code coverage reporting" OFF)

# --- Qt & GUI Options ---
option(ENABLE_QT "Build Qt-based GUI applications" OFF)
option(ENABLE_QML "Build QML support for Qt apps" OFF)

# --- Compiler Defaults ---
set(CMAKE_CXX_STANDARD 17 CACHE STRING "C++ Standard")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- Project Paths ---
set(PROJECT_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated" CACHE PATH "Directory for generated files")
file(MAKE_DIRECTORY ${PROJECT_GENERATED_DIR})
