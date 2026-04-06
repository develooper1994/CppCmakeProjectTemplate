# cmake/StaticAnalyzers.cmake

function(enable_static_analysis)
    if(ENABLE_CLANG_TIDY)
        find_program(CLANG_TIDY_PATH clang-tidy)
        if(CLANG_TIDY_PATH)
            message(STATUS "Found clang-tidy: ${CLANG_TIDY_PATH}")
            # Build tidy flags as a list (we keep a strict and a relaxed variant)
            set(_tidy_list ${CLANG_TIDY_PATH})
            list(APPEND _tidy_list "-extra-arg=-Wno-unknown-warning-option")
            # Restrict clang-tidy analysis to project source directories to avoid
            # analyzing bundled third-party code (e.g., deps under build/_deps).
            # Do NOT include generated headers in the header-filter (they are
            # machine-generated and often violate style rules). Instead, add the
            # generated include path so clang-tidy can resolve symbols without
            # analyzing the generated files themselves.
            list(APPEND _tidy_list "-header-filter=^${CMAKE_SOURCE_DIR}/(libs|apps|tests|gui_app|main_app|extension)/")
            list(APPEND _tidy_list "-extra-arg=-I${CMAKE_BINARY_DIR}/generated")

            # Treat warnings as errors if WARNING_LEVEL is ERROR
            set(_tidy_list_strict ${_tidy_list})
            if(WARNING_LEVEL STREQUAL "ERROR" OR ENABLE_WERROR)
                list(APPEND _tidy_list_strict "-warnings-as-errors=*")
            endif()

            # Expose both strict and relaxed variants so callers can choose
            # to run relaxed analyzers on test targets or harnesses while
            # keeping strict mode for production libraries.
            set(PROJECT_CLANG_TIDY "${_tidy_list_strict}" PARENT_SCOPE)
            set(_tidy_list_relaxed ${_tidy_list_strict})
            list(REMOVE_ITEM _tidy_list_relaxed "-warnings-as-errors=*")
            set(PROJECT_CLANG_TIDY_RELAXED "${_tidy_list_relaxed}" PARENT_SCOPE)

            # For backward compatibility with older CMake flows, set the
            # global CMAKE_CXX_CLANG_TIDY to the strict variant when enabled.
            set(CMAKE_CXX_CLANG_TIDY "${PROJECT_CLANG_TIDY}" PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "clang-tidy not found.")
        endif()
    endif()

        # GCC -fanalyzer support
        if(ENABLE_GCC_ANALYZER)
            if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
                # Minimal GCC analyzer flags; keep as a per-target option.
                set(_gcc_analyzer_flags -fanalyzer)
                if(WARNING_LEVEL STREQUAL "ERROR" OR ENABLE_WERROR)
                    list(APPEND _gcc_analyzer_flags -Werror)
                endif()
                set(PROJECT_GCC_ANALYZER_FLAGS "${_gcc_analyzer_flags}" PARENT_SCOPE)
                message(STATUS "[StaticAnalyzers] GCC -fanalyzer enabled")
            else()
                message(AUTHOR_WARNING "ENABLE_GCC_ANALYZER set but compiler is not GNU.")
            endif()
        endif()

        # MSVC /analyze support
        if(ENABLE_MSVC_ANALYZE)
            if(MSVC)
                # Use /analyze as a per-target compile option
                set(_msvc_analyze_flags /analyze)
                set(PROJECT_MSVC_ANALYZE_FLAGS "${_msvc_analyze_flags}" PARENT_SCOPE)
                message(STATUS "[StaticAnalyzers] MSVC /analyze enabled")
            else()
                message(AUTHOR_WARNING "ENABLE_MSVC_ANALYZE set but MSVC is not the active compiler.")
            endif()
        endif()

    if(ENABLE_CPPCHECK)
        find_program(CPPCHECK_PATH cppcheck)
        if(CPPCHECK_PATH)
            message(STATUS "Found cppcheck: ${CPPCHECK_PATH}")
            set(_cppcheck_list ${CPPCHECK_PATH})
            list(APPEND _cppcheck_list "--enable=all" "--inconclusive" "--force" "--inline-suppr" "--suppress=missingIncludeSystem")
            set(_cppcheck_list_strict ${_cppcheck_list})
            if(ENABLE_WERROR)
                list(APPEND _cppcheck_list_strict "--error-exitcode=1")
            endif()
            set(PROJECT_CPPCHECK "${_cppcheck_list_strict}" PARENT_SCOPE)
            set(_cppcheck_list_relaxed ${_cppcheck_list_strict})
            # Remove error-exitcode from the relaxed variant so test targets
            # do not fail the overall build on inconsequential findings.
            list(REMOVE_ITEM _cppcheck_list_relaxed "--error-exitcode=1")
            set(PROJECT_CPPCHECK_RELAXED "${_cppcheck_list_relaxed}" PARENT_SCOPE)
            set(CMAKE_CXX_CPPCHECK "${PROJECT_CPPCHECK}" PARENT_SCOPE)
        else()
            message(AUTHOR_WARNING "cppcheck not found.")
        endif()
    endif()
endfunction()


# Helper: apply strict project analyzers to a target
# Per-target override: -D<TARGET>_ANALYZE_GENERATED=ON includes generated
# headers in the analysis header-filter (off by default to avoid noise).
function(apply_project_analyzers tgt)
    string(TOUPPER "${tgt}" _tgt_upper)
    set(_analyze_gen_var "${_tgt_upper}_ANALYZE_GENERATED")

    if(DEFINED PROJECT_CLANG_TIDY)
        set(_tidy_for_tgt ${PROJECT_CLANG_TIDY})
        if(DEFINED ${_analyze_gen_var} AND ${_analyze_gen_var})
            # Widen header-filter to also include generated headers
            list(FILTER _tidy_for_tgt EXCLUDE REGEX "^-header-filter=")
            list(APPEND _tidy_for_tgt "-header-filter=^${CMAKE_SOURCE_DIR}/(libs|apps|tests|gui_app|main_app|extension)/|^${CMAKE_BINARY_DIR}/generated/")
        endif()
        set_target_properties(${tgt} PROPERTIES CXX_CLANG_TIDY "${_tidy_for_tgt}")
    endif()
    if(DEFINED PROJECT_CPPCHECK)
        set_target_properties(${tgt} PROPERTIES CXX_CPPCHECK "${PROJECT_CPPCHECK}")
    endif()
    # Apply optional compiler-integrated analyzers
    if(DEFINED PROJECT_GCC_ANALYZER_FLAGS)
        target_compile_options(${tgt} PRIVATE ${PROJECT_GCC_ANALYZER_FLAGS})
    endif()
    if(DEFINED PROJECT_MSVC_ANALYZE_FLAGS)
        target_compile_options(${tgt} PRIVATE ${PROJECT_MSVC_ANALYZE_FLAGS})
    endif()
endfunction()

# Helper: apply relaxed analyzers to a target (no warnings-as-errors / no error-exitcode)
function(apply_relaxed_analyzers tgt)
    if(DEFINED PROJECT_CLANG_TIDY_RELAXED)
        set_target_properties(${tgt} PROPERTIES CXX_CLANG_TIDY "${PROJECT_CLANG_TIDY_RELAXED}")
    endif()
    if(DEFINED PROJECT_CPPCHECK_RELAXED)
        set_target_properties(${tgt} PROPERTIES CXX_CPPCHECK "${PROJECT_CPPCHECK_RELAXED}")
    endif()
endfunction()
