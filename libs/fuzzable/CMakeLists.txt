# libs/fuzzable/CMakeLists.txt

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project(Fuzzable LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Fuzzing OPTIONAL)
endif()

add_library(fuzzable)

target_sources(fuzzable
    PRIVATE
        src/fuzzable.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/fuzzable/fuzzable.h
)

target_include_directories(fuzzable
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated>
        $<INSTALL_INTERFACE:include>
)

if(COMMAND enable_sanitizers)
    enable_sanitizers(fuzzable)
endif()

if(COMMAND enable_hardening)
    enable_hardening(fuzzable)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(fuzzable)
endif()

if(ENABLE_COVERAGE)
    enable_code_coverage(fuzzable)
endif()

install(TARGETS fuzzable
    EXPORT fuzzable_Targets
    FILE_SET HEADERS)

# Exempt the fuzzable test helper from strict static analysis to avoid
# failing hardened builds while iterating on fuzz harnesses. Production
# libraries remain covered by analyzers.
set_target_properties(fuzzable PROPERTIES CXX_CLANG_TIDY "" CXX_CPPCHECK "")
