# cmake/Reproducibility.cmake
# Binary Reproducibility helpers.
#
# When ENABLE_REPRODUCIBLE is ON (set by -DENABLE_REPRODUCIBLE=ON or
# `tool build --reproducible`) this module:
#   1. Rewrites embedded source paths via -ffile-prefix-map so build-host
#      paths never appear in the binary (identical sources → identical object).
#   2. Exports SOURCE_DATE_EPOCH from git commit time so file timestamps
#      embedded by tools are normalised.
#   3. Forces ar(1) into deterministic mode (-D flag) to normalise archive
#      member timestamps on all STATIC library targets.
#
# Usage in CMakeLists.txt (project root):
#   include(Reproducibility)
#   if(ENABLE_REPRODUCIBLE)
#       enable_reproducible_build()
#   endif()
#
# Or, to apply only to specific targets:
#   enable_reproducible_build(TARGET mylib mymain)

option(ENABLE_REPRODUCIBLE "Strip host-specific build paths for binary reproducibility" OFF)

function(enable_reproducible_build)
    cmake_parse_arguments(_rep "" "" "TARGET" ${ARGN})

    # ── 1. Source-path normalisation ─────────────────────────────────────────
    # Replace the absolute build root with a stable placeholder so that
    # binaries compiled on different machines are byte-identical.
    # CMake exposes the source root in CMAKE_SOURCE_DIR.
    set(_prefix_map "-ffile-prefix-map=${CMAKE_SOURCE_DIR}=.")

    # Some older Clang/GCC versions use -fdebug-prefix-map only.
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        if(_rep_TARGET)
            foreach(_t IN LISTS _rep_TARGET)
                target_compile_options(${_t} PRIVATE
                    "${_prefix_map}"
                    "-Wno-builtin-macro-redefined"
                    -D__DATE__=\"redacted\"
                    -D__TIME__=\"redacted\"
                )
            endforeach()
        else()
            add_compile_options(
                "${_prefix_map}"
                "-Wno-builtin-macro-redefined"
                -D__DATE__=\"redacted\"
                -D__TIME__=\"redacted\"
            )
        endif()
        message(STATUS "[Reproducibility] Source-path stripping: ${_prefix_map}")
    else()
        message(WARNING "[Reproducibility] -ffile-prefix-map not supported by ${CMAKE_CXX_COMPILER_ID}; skipping path stripping.")
    endif()

    # ── 2. SOURCE_DATE_EPOCH ─────────────────────────────────────────────────
    # If the variable is already set in the environment, respect it.
    # Otherwise derive it from the last git commit timestamp.
    if(NOT DEFINED ENV{SOURCE_DATE_EPOCH})
        find_program(_git_exe git)
        if(_git_exe)
            execute_process(
                COMMAND ${_git_exe} log -1 --format=%ct
                WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
                OUTPUT_VARIABLE _git_epoch
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
            )
            if(_git_epoch)
                set(ENV{SOURCE_DATE_EPOCH} "${_git_epoch}")
                message(STATUS "[Reproducibility] SOURCE_DATE_EPOCH set to ${_git_epoch} (last commit)")
            else()
                set(ENV{SOURCE_DATE_EPOCH} "0")
                message(STATUS "[Reproducibility] SOURCE_DATE_EPOCH set to 0 (no git history)")
            endif()
        else()
            set(ENV{SOURCE_DATE_EPOCH} "0")
            message(STATUS "[Reproducibility] SOURCE_DATE_EPOCH set to 0 (git not found)")
        endif()
    else()
        message(STATUS "[Reproducibility] SOURCE_DATE_EPOCH already set: $ENV{SOURCE_DATE_EPOCH}")
    endif()

    # ── 3. Deterministic ar(1) for static libraries ──────────────────────────
    # The CMAKE_<LANG>_ARCHIVE_CREATE/APPEND variables control how CMake
    # invokes ar.  We inject the -D flag (deterministic mode: zero uid/gid/
    # mtime in archive headers) so static library members are stable.
    if(CMAKE_AR)
        set(CMAKE_C_ARCHIVE_CREATE   "<CMAKE_AR> qcD <TARGET> <LINK_FLAGS> <OBJECTS>" PARENT_SCOPE)
        set(CMAKE_C_ARCHIVE_APPEND   "<CMAKE_AR> qD  <TARGET> <LINK_FLAGS> <OBJECTS>" PARENT_SCOPE)
        set(CMAKE_CXX_ARCHIVE_CREATE "<CMAKE_AR> qcD <TARGET> <LINK_FLAGS> <OBJECTS>" PARENT_SCOPE)
        set(CMAKE_CXX_ARCHIVE_APPEND "<CMAKE_AR> qD  <TARGET> <LINK_FLAGS> <OBJECTS>" PARENT_SCOPE)
        message(STATUS "[Reproducibility] ar deterministic mode enabled (CMAKE_AR=${CMAKE_AR})")
    endif()

    message(STATUS "[Reproducibility] Reproducible build enabled.")
endfunction()
