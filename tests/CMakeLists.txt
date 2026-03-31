# tests/CMakeLists.txt
# Supports: GoogleTest (default), Catch2, Boost.Test, QTest (when ENABLE_QT=ON)

include(FetchContent)

# ── GoogleTest ───────────────────────────────────────────────────────────────
if(ENABLE_GTEST)
    FetchContent_Declare(googletest
        URL      https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
        URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        SYSTEM)
    # gtest_force_shared_crt is already set in ProjectConfigs.cmake for MSVC
    FetchContent_MakeAvailable(googletest)
    message(STATUS "Test framework: GoogleTest")
    # Disable static analyzers for googletest targets added via FetchContent
    # They are third-party sources and should not be checked by the project's
    # clang-tidy/cppcheck configuration which treats warnings as errors.
    foreach(_gtest_target IN ITEMS gmock gmock_main gtest gtest_main)
        if(TARGET ${_gtest_target})
            set_target_properties(${_gtest_target} PROPERTIES CXX_CLANG_TIDY "")
            # Per-target CXX_CPPCHECK is supported on newer CMake versions; clear if present.
            set_target_properties(${_gtest_target} PROPERTIES CXX_CPPCHECK "")
        endif()
    endforeach()
endif()

# ── Catch2 ───────────────────────────────────────────────────────────────────
if(ENABLE_CATCH2)
    FetchContent_Declare(Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG        v3.5.3
        SYSTEM)
    FetchContent_MakeAvailable(Catch2)
    list(APPEND CMAKE_MODULE_PATH ${catch2_SOURCE_DIR}/extras)
    message(STATUS "Test framework: Catch2")
endif()

# ── Boost.Test ───────────────────────────────────────────────────────────────
if(ENABLE_BOOST_TEST)
    if(NOT ENABLE_BOOST)
        message(FATAL_ERROR "ENABLE_BOOST_TEST requires ENABLE_BOOST=ON")
    endif()
    find_package(Boost REQUIRED COMPONENTS unit_test_framework)
    message(STATUS "Test framework: Boost.Test")
endif()

# ── QTest (automatic when Qt is ON) ─────────────────────────────────────────
if(ENABLE_QT AND Qt6_FOUND)
    message(STATUS "Test framework: QTest (Qt6)")
elseif(ENABLE_QT AND Qt5_FOUND)
    message(STATUS "Test framework: QTest (Qt5)")
endif()

add_subdirectory(unit)

if(ENABLE_FUZZING)
    add_subdirectory(fuzz)
endif()
