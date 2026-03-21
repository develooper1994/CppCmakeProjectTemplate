# cmake/ProjectConfigs.cmake
# Centralized configuration for all project-wide CMake defaults

# --- Build Options ---
option(BUILD_SHARED_LIBS    "Build libraries as shared"          OFF)
option(ENABLE_UNITY_BUILD   "Enable unity builds"                OFF)
option(ENABLE_WERROR        "Treat warnings as errors"           OFF)
option(ENABLE_UNIT_TESTS    "Build unit tests"                   ON)
option(ENABLE_DOCS          "Build documentation"                OFF)
option(ENABLE_COVERAGE      "Enable code coverage reporting"     OFF)

# --- Quality & Security Options ---
option(ENABLE_ASAN          "Enable Address Sanitizer"           OFF)
option(ENABLE_UBSAN         "Enable Undefined Behavior Sanitizer" OFF)
option(ENABLE_TSAN          "Enable Thread Sanitizer"            OFF)
option(ENABLE_CLANG_TIDY    "Enable Clang-Tidy static analysis"  OFF)
option(ENABLE_CPPCHECK      "Enable Cppcheck static analysis"    OFF)
# NOTE: Valgrind support is planned (ENABLE_VALGRIND). Currently not implemented.
# When enabled it would wrap ctest runs with valgrind --leak-check=full.

# --- Test Framework Options ---
# Only one framework should be ON at a time per build.
option(ENABLE_GTEST         "Use GoogleTest as test framework"   ON)
option(ENABLE_CATCH2        "Use Catch2 as test framework"       OFF)
option(ENABLE_BOOST_TEST    "Use Boost.Test as test framework"   OFF)
# QTest is enabled automatically when ENABLE_QT=ON (no separate option needed)

# --- Qt & GUI Options ---
option(ENABLE_QT            "Build Qt-based GUI applications"    OFF)
option(ENABLE_QML           "Build QML support for Qt apps"      OFF)

# --- Boost Options ---
option(ENABLE_BOOST         "Enable Boost libraries"             OFF)
set(BOOST_COMPONENTS "" CACHE STRING
    "Semicolon-separated Boost components to find (e.g. filesystem;system)")

# --- Compiler Defaults ---
set(CMAKE_CXX_STANDARD          17  CACHE STRING "C++ Standard")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS        OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- MSVC Runtime Consistency ---
# Ensures all targets (including FetchContent deps like GTest) use the same CRT.
# /MD  (MultiThreadedDLL)      when BUILD_SHARED_LIBS=ON  or DLL build
# /MT  (MultiThreaded)         when BUILD_SHARED_LIBS=OFF (static build)
# Without this, mixing /MT and /MD causes linker errors (LNK2038).
if(MSVC)
    if(BUILD_SHARED_LIBS)
        set(CMAKE_MSVC_RUNTIME_LIBRARY
            "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL"
            CACHE STRING "MSVC runtime library" FORCE)
    else()
        set(CMAKE_MSVC_RUNTIME_LIBRARY
            "MultiThreaded$<$<CONFIG:Debug>:Debug>"
            CACHE STRING "MSVC runtime library" FORCE)
    endif()
    # GTest must follow the same CRT — set before FetchContent_MakeAvailable
    set(gtest_force_shared_crt ${BUILD_SHARED_LIBS} CACHE BOOL "" FORCE)
endif()

# --- Boost (optional) ---
if(ENABLE_BOOST)
    if(BOOST_COMPONENTS)
        find_package(Boost REQUIRED COMPONENTS ${BOOST_COMPONENTS})
    else()
        find_package(Boost REQUIRED)
    endif()
    if(Boost_FOUND)
        message(STATUS "Found Boost ${Boost_VERSION}")
    endif()
endif()

# --- Project Paths ---
set(PROJECT_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated"
    CACHE PATH "Directory for generated files")
file(MAKE_DIRECTORY ${PROJECT_GENERATED_DIR})
