# cmake/FeatureFlags.cmake
# Generates include/FeatureFlags.h — a project-wide header that exposes
# every CMake build option as a C++ preprocessor macro.
#
# Call once from root CMakeLists.txt (after ProjectConfigs):
#   include(FeatureFlags)
#   generate_feature_flags()
#
# Then make it available to a target:
#   target_include_directories(<target> PUBLIC
#       $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/generated/project>)

function(generate_feature_flags)
    set(GENERATED_DIR "${CMAKE_BINARY_DIR}/generated/project")
    file(MAKE_DIRECTORY "${GENERATED_DIR}")

    # Map CMake booleans → variables the .h.in template reads
    if(BUILD_SHARED_LIBS)
        set(PROJECT_SHARED_LIBS 1)
        set(PROJECT_FEATURE_LIBRARY_TYPE "Shared")
    else()
        set(PROJECT_SHARED_LIBS 0)
        set(PROJECT_FEATURE_LIBRARY_TYPE "Static")
    endif()

    # Each option maps to FEATURE_<NAME> (1 or 0)
    foreach(_opt
        UNIT_TESTS GTEST CATCH2 BOOST_TEST
        ASAN UBSAN TSAN
        CLANG_TIDY CPPCHECK COVERAGE
        QT QML BOOST DOCS
    )
        if(ENABLE_${_opt})
            set(FEATURE_${_opt} 1)
        else()
            set(FEATURE_${_opt} 0)
        endif()
    endforeach()

    # QTest follows Qt
    if(ENABLE_QT)
        set(FEATURE_QTEST 1)
    else()
        set(FEATURE_QTEST 0)
    endif()

    configure_file(
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/FeatureFlags.h.in"
        "${GENERATED_DIR}/FeatureFlags.h"
    )

    # Export the include path as a global variable so root CMakeLists.txt
    # can forward it to all targets via an INTERFACE library.
    set(FEATURE_FLAGS_INCLUDE_DIR "${GENERATED_DIR}" PARENT_SCOPE)

    message(STATUS "FeatureFlags generated → ${GENERATED_DIR}/FeatureFlags.h")
endfunction()


# Helper: attach FeatureFlags.h to an existing target
function(target_add_feature_flags target)
    target_include_directories(${target} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/generated/project>
        $<INSTALL_INTERFACE:include>
    )
endfunction()
