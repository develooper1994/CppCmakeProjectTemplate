# cmake/Qt.cmake
# Qt5/Qt6 detection and per-target helper functions.
#
# ENABLE_QT=ON  → finds Qt (prefers Qt6, falls back to Qt5)
# ENABLE_QML=ON → also finds Quick/Qml components
#
# Provides:
#   target_link_qt(<target> [QML] [COMPONENTS Core Widgets ...])
#       Links the discovered Qt version to <target>.
#       Sets AUTOMOC/AUTOUIC/AUTORCC on the target automatically.
#       Defines QT_VERSION_MAJOR on the target.
#
# CMake preset / CLI usage:
#   cmake --preset gcc-release-static-x86_64 -DENABLE_QT=ON [-DENABLE_QML=ON]
#   tool build --qt          (passes -DENABLE_QT=ON)
#   tool build --qt --qml    (passes -DENABLE_QT=ON -DENABLE_QML=ON)
#
# Cross-compilation (aarch64 / Raspberry Pi):
#   Set -DQT_HOST_PATH=/usr/lib/qt6 and -DCMAKE_PREFIX_PATH=<sysroot>/usr
#   in your preset or toolchain file. See cmake/toolchains/aarch64-linux-gnu.cmake.
#
# Qt installation hints:
#   Linux:   sudo apt install qt6-base-dev [qt6-declarative-dev]
#            OR install via Qt Maintenance Tool to /opt/Qt
#   macOS:   brew install qt@6
#   Windows: Qt Installer → add to CMAKE_PREFIX_PATH

# Guard: only search for Qt when ENABLE_QT is requested
if(NOT ENABLE_QT)
    # Still define the no-op helper so CMakeLists referencing it always compile
    function(target_link_qt target)
    endfunction()
    return()
endif()

# ---------------------------------------------------------------------------
# Qt version discovery: try Qt6 first, fall back to Qt5
# ---------------------------------------------------------------------------
set(_QT_FOUND FALSE)

# Allow user to force a version: -DQT_VERSION_PREF=5 or 6
if(NOT DEFINED QT_VERSION_PREF)
    set(QT_VERSION_PREF 6)
endif()

# Base components always needed
set(_QT_BASE_COMPONENTS Core)
if(ENABLE_QML)
    list(APPEND _QT_BASE_COMPONENTS Qml Quick QuickControls2)
endif()

# Try preferred version first
if(QT_VERSION_PREF EQUAL 6)
    find_package(Qt6 QUIET COMPONENTS Core Widgets ${_QT_BASE_COMPONENTS})
    if(Qt6_FOUND)
        set(_QT_FOUND TRUE)
        set(_QT_VER 6)
        set(_QT_NS  Qt6)
        message(STATUS "[Qt] Found Qt6 ${Qt6_VERSION}")
    else()
        # Fallback to Qt5
        find_package(Qt5 QUIET COMPONENTS Core Widgets ${_QT_BASE_COMPONENTS})
        if(Qt5_FOUND)
            set(_QT_FOUND TRUE)
            set(_QT_VER 5)
            set(_QT_NS  Qt5)
            message(STATUS "[Qt] Qt6 not found — using Qt5 ${Qt5_VERSION}")
        endif()
    endif()
else()
    find_package(Qt5 QUIET COMPONENTS Core Widgets ${_QT_BASE_COMPONENTS})
    if(Qt5_FOUND)
        set(_QT_FOUND TRUE)
        set(_QT_VER 5)
        set(_QT_NS  Qt5)
        message(STATUS "[Qt] Found Qt5 ${Qt5_VERSION}")
    else()
        find_package(Qt6 QUIET COMPONENTS Core Widgets ${_QT_BASE_COMPONENTS})
        if(Qt6_FOUND)
            set(_QT_FOUND TRUE)
            set(_QT_VER 6)
            set(_QT_NS  Qt6)
            message(STATUS "[Qt] Qt5 not found — using Qt6 ${Qt6_VERSION}")
        endif()
    endif()
endif()

if(NOT _QT_FOUND)
    message(FATAL_ERROR
        "[Qt] ENABLE_QT=ON but neither Qt5 nor Qt6 was found.\n"
        "Install: sudo apt install qt6-base-dev\n"
        "   OR:   brew install qt@6\n"
        "   OR:   set CMAKE_PREFIX_PATH to your Qt installation directory.\n"
        "To skip Qt targets without error: -DENABLE_QT=OFF"
    )
endif()

# Export for use in subdirectories
set(QT_VERSION_MAJOR ${_QT_VER}  CACHE INTERNAL "Detected Qt major version")
set(QT_NAMESPACE     ${_QT_NS}   CACHE INTERNAL "CMake Qt namespace (Qt5 or Qt6)")

# ---------------------------------------------------------------------------
# target_link_qt(<target> [QML] [NETWORK] [MULTIMEDIA] [COMPONENTS <c>...])
#
# Arguments:
#   QML           — add Qml + Quick + QuickControls2
#   NETWORK       — add Network
#   MULTIMEDIA    — add Multimedia
#   COMPONENTS    — additional arbitrary Qt component names
# ---------------------------------------------------------------------------
function(target_link_qt target)
    cmake_parse_arguments(_TLQ "QML;NETWORK;MULTIMEDIA;OPENGL;SVG;TEST" "" "COMPONENTS" ${ARGN})

    # Always required
    set(_components Core Widgets)

    if(_TLQ_QML OR ENABLE_QML)
        list(APPEND _components Qml Quick QuickControls2)
        target_compile_definitions(${target} PRIVATE FEATURE_QML=1)
    endif()
    if(_TLQ_NETWORK)
        list(APPEND _components Network)
    endif()
    if(_TLQ_MULTIMEDIA)
        list(APPEND _components Multimedia)
    endif()
    if(_TLQ_OPENGL)
        list(APPEND _components OpenGL OpenGLWidgets)
    endif()
    if(_TLQ_SVG)
        list(APPEND _components Svg)
    endif()
    if(_TLQ_TEST)
        list(APPEND _components Test)
    endif()
    if(_TLQ_COMPONENTS)
        list(APPEND _components ${_TLQ_COMPONENTS})
    endif()
    list(REMOVE_DUPLICATES _components)

    # Find the components (some may already be found, find_package is idempotent)
    find_package(${QT_NAMESPACE} REQUIRED COMPONENTS ${_components})

    # Enable Qt auto-tools on this target
    set_target_properties(${target} PROPERTIES
        AUTOMOC ON
        AUTOUIC ON
        AUTORCC ON)

    # Link all required components
    foreach(_comp IN LISTS _components)
        if(TARGET ${QT_NAMESPACE}::${_comp})
            target_link_libraries(${target} PRIVATE ${QT_NAMESPACE}::${_comp})
        else()
            message(WARNING "[Qt] Component '${QT_NAMESPACE}::${_comp}' not available — skipping.")
        endif()
    endforeach()

    # Expose Qt version to C++ code
    target_compile_definitions(${target} PRIVATE
        QT_VERSION_MAJOR=${QT_VERSION_MAJOR}
        FEATURE_QT=1)

    message(STATUS "[Qt] Linked Qt${QT_VERSION_MAJOR} [${_components}] → '${target}'")
endfunction()
