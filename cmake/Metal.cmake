# cmake/Metal.cmake
# Apple Metal GPU compute support for CppCmakeProjectTemplate.
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  CAVEAT — build system generated without Metal SDK present               │
# │                                                                          │
# │  This file implements Apple Metal framework conventions but it cannot    │
# │  be compiled or tested without macOS / Xcode with Metal support.         │
# │  The logic will be skipped silently when ENABLE_METAL=OFF (default).     │
# │                                                                          │
# │  To enable, configure on macOS with: -DENABLE_METAL=ON                   │
# │  Requires Xcode command-line tools (xcrun, metal, metallib).             │
# │                                                                          │
# │  Metal is macOS/iOS only — this module is a no-op on other platforms.   │
# │                                                                          │
# │  NOTE: CI will NOT run Metal-specific paths until a macOS runner with    │
# │        Xcode is available.                                                │
# └──────────────────────────────────────────────────────────────────────────┘
#
# Provides:
#   enable_metal_support()                          — verify macOS, find SDK
#   target_add_metal(<target>)                      — link Metal frameworks
#   target_compile_metal_shaders(<target> <files>)  — .metal → .air → .metallib
#
# Global option : -DENABLE_METAL=ON
# CLI           : tool build --metal
#
# Metal shader compilation pipeline:
#   .metal  →  xcrun -sdk macosx metal  →  .air  (intermediate)
#   .air(s) →  xcrun -sdk macosx metallib  →  .metallib  (final GPU binary)
#
# Metal-cpp (C++ wrapper):
#   If metal-cpp headers are available, they will be detected automatically.
#   Download: https://developer.apple.com/metal/cpp/

option(ENABLE_METAL "Enable Apple Metal GPU compute support (requires macOS)" OFF)
set(METAL_SDK "macosx" CACHE STRING
    "Metal SDK to use with xcrun (macosx | iphoneos | iphonesimulator)")

# ---------------------------------------------------------------------------
# _metal_find_sdk — locate xcrun, metal compiler, and metallib linker
# ---------------------------------------------------------------------------
function(_metal_find_sdk)
    # xcrun is the universal tool dispatcher on macOS/Xcode
    find_program(_xcrun xcrun)
    if(NOT _xcrun)
        message(FATAL_ERROR
            "[Metal] ENABLE_METAL=ON but 'xcrun' was not found.\n"
            "Install Xcode command-line tools: xcode-select --install\n"
            "To disable: -DENABLE_METAL=OFF")
    endif()

    # Verify the metal compiler is available via xcrun
    execute_process(
        COMMAND ${_xcrun} -sdk ${METAL_SDK} --find metal
        OUTPUT_VARIABLE _metal_compiler
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
        RESULT_VARIABLE _metal_rc)

    if(NOT _metal_rc EQUAL 0 OR NOT _metal_compiler)
        message(FATAL_ERROR
            "[Metal] 'metal' shader compiler not found via xcrun.\n"
            "Ensure Xcode with Metal support is installed.\n"
            "To disable: -DENABLE_METAL=OFF")
    endif()

    # Locate metallib linker
    execute_process(
        COMMAND ${_xcrun} -sdk ${METAL_SDK} --find metallib
        OUTPUT_VARIABLE _metallib_tool
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
        RESULT_VARIABLE _metallib_rc)

    if(NOT _metallib_rc EQUAL 0 OR NOT _metallib_tool)
        message(FATAL_ERROR
            "[Metal] 'metallib' linker not found via xcrun.\n"
            "Ensure Xcode with Metal support is installed.\n"
            "To disable: -DENABLE_METAL=OFF")
    endif()

    set(_METAL_COMPILER "${_metal_compiler}" CACHE FILEPATH
        "Metal shader compiler path" FORCE)
    set(_METALLIB_TOOL "${_metallib_tool}" CACHE FILEPATH
        "Metal library linker path" FORCE)
    set(_XCRUN "${_xcrun}" CACHE FILEPATH "xcrun path" FORCE)

    message(STATUS "[Metal] Metal compiler: ${_metal_compiler}")
    message(STATUS "[Metal] Metallib tool:  ${_metallib_tool}")
endfunction()

# ---------------------------------------------------------------------------
# _metal_find_cpp_headers — detect metal-cpp (optional C++ wrapper)
# ---------------------------------------------------------------------------
function(_metal_find_cpp_headers)
    find_path(_metal_cpp_include
        NAMES Metal/Metal.hpp
        HINTS
            "$ENV{METAL_CPP_ROOT}"
            "$ENV{HOME}/metal-cpp"
            /usr/local/include
            /opt/homebrew/include
        PATH_SUFFIXES metal-cpp)

    if(_metal_cpp_include)
        set(_METAL_CPP_INCLUDE "${_metal_cpp_include}" CACHE PATH
            "metal-cpp header directory" FORCE)
        message(STATUS "[Metal] metal-cpp headers found: ${_metal_cpp_include}")
    else()
        message(STATUS "[Metal] metal-cpp headers not found (optional). "
                       "Download: https://developer.apple.com/metal/cpp/")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# enable_metal_support()
# Call once in CMakeLists.txt (guard below handles this automatically).
# Verifies macOS, finds Metal SDK, locates metal-cpp headers.
# ---------------------------------------------------------------------------
function(enable_metal_support)
    if(NOT ENABLE_METAL)
        return()
    endif()

    # Metal is macOS/iOS only
    if(NOT APPLE)
        message(WARNING
            "[Metal] ENABLE_METAL=ON but platform is not Apple — skipping.\n"
            "Metal is only available on macOS and iOS.")
        set(ENABLE_METAL OFF CACHE BOOL "Metal disabled (non-Apple)" FORCE)
        return()
    endif()

    _metal_find_sdk()
    _metal_find_cpp_headers()

    # Expose to FeatureFlags.cmake
    set(FEATURE_METAL ON PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# target_add_metal(<target>)
# Links Metal, MetalKit, and Foundation frameworks.
# Optionally adds metal-cpp include path if available.
# ---------------------------------------------------------------------------
function(target_add_metal target)
    if(NOT ENABLE_METAL)
        message(WARNING "[Metal] target_add_metal(${target}): ENABLE_METAL=OFF — skipping.")
        return()
    endif()

    # Link Apple frameworks
    find_library(_metal_framework Metal)
    find_library(_metalkit_framework MetalKit)
    find_library(_foundation_framework Foundation)

    if(_metal_framework)
        target_link_libraries(${target} PRIVATE ${_metal_framework})
    else()
        message(WARNING "[Metal] Metal.framework not found for '${target}'.")
    endif()

    if(_metalkit_framework)
        target_link_libraries(${target} PRIVATE ${_metalkit_framework})
    endif()

    if(_foundation_framework)
        target_link_libraries(${target} PRIVATE ${_foundation_framework})
    endif()

    target_compile_definitions(${target} PRIVATE FEATURE_METAL=1)

    # Add metal-cpp include path if available
    if(_METAL_CPP_INCLUDE)
        target_include_directories(${target} PRIVATE ${_METAL_CPP_INCLUDE})
    endif()

    message(STATUS "[Metal] Configured '${target}': Metal + MetalKit + Foundation")
endfunction()

# ---------------------------------------------------------------------------
# target_compile_metal_shaders(<target> <shader1.metal> [shader2.metal ...])
# Compiles .metal shader files to .air (intermediate) then links into
# a single .metallib GPU binary placed alongside the target output.
#
# Usage:
#   target_compile_metal_shaders(my_app
#       shaders/compute.metal
#       shaders/render.metal)
# ---------------------------------------------------------------------------
function(target_compile_metal_shaders target)
    if(NOT ENABLE_METAL)
        return()
    endif()

    set(_shader_files ${ARGN})
    if(NOT _shader_files)
        message(WARNING "[Metal] target_compile_metal_shaders(${target}): no .metal files provided.")
        return()
    endif()

    set(_air_files "")
    foreach(_shader IN LISTS _shader_files)
        get_filename_component(_shader_name "${_shader}" NAME_WE)
        get_filename_component(_shader_abs "${_shader}" ABSOLUTE)
        set(_air_file "${CMAKE_CURRENT_BINARY_DIR}/${_shader_name}.air")

        add_custom_command(
            OUTPUT "${_air_file}"
            COMMAND ${_XCRUN} -sdk ${METAL_SDK} metal
                    -c "${_shader_abs}"
                    -o "${_air_file}"
            DEPENDS "${_shader_abs}"
            COMMENT "[Metal] Compiling ${_shader} → ${_shader_name}.air"
            VERBATIM)

        list(APPEND _air_files "${_air_file}")
    endforeach()

    # Link all .air files into a single .metallib
    set(_metallib_file "${CMAKE_CURRENT_BINARY_DIR}/${target}.metallib")

    add_custom_command(
        OUTPUT "${_metallib_file}"
        COMMAND ${_XCRUN} -sdk ${METAL_SDK} metallib
                ${_air_files}
                -o "${_metallib_file}"
        DEPENDS ${_air_files}
        COMMENT "[Metal] Linking ${target}.metallib"
        VERBATIM)

    # Create a custom target for shader compilation
    add_custom_target(${target}_metal_shaders ALL
        DEPENDS "${_metallib_file}")

    # Make the main target depend on shader compilation
    add_dependencies(${target} ${target}_metal_shaders)

    # Copy .metallib next to the built binary
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${_metallib_file}"
                "$<TARGET_FILE_DIR:${target}>/${target}.metallib"
        COMMENT "[Metal] Installing ${target}.metallib → output directory"
        VERBATIM)

    message(STATUS "[Metal] Shader pipeline for '${target}': "
                   "${_shader_files} → ${target}.metallib")
endfunction()

# ---------------------------------------------------------------------------
# Module-level: auto-run enable_metal_support() when ENABLE_METAL=ON
# (Called once via include(Metal) in CMakeLists.txt)
# ---------------------------------------------------------------------------
if(ENABLE_METAL)
    enable_metal_support()
endif()
