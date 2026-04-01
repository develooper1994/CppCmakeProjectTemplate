# cmake/PGO.cmake — Profile-Guided Optimization support
#
# Two-phase PGO workflow:
#   Phase 1 (Instrument): cmake -DPGO_MODE=generate ...
#     Builds with instrumentation. Run the binary to produce profile data.
#   Phase 2 (Optimize):   cmake -DPGO_MODE=use -DPGO_PROFILE_DIR=<dir> ...
#     Rebuilds using collected profile data for optimized codegen.
#
# BOLT post-link optimization (Clang/LLVM only):
#   Step 1: Build normally (release), then collect perf data:
#           perf record -e cycles:u -j any,u -o perf.data -- <binary> <workload>
#   Step 2: Convert: perf2bolt -p perf.data -o perf.fdata <binary>
#   Step 3: Optimize: llvm-bolt <binary> -o <binary>.bolt -data=perf.fdata \
#             -reorder-blocks=ext-tsp -reorder-functions=hfsort \
#             -split-functions -split-all-cold -split-eh -dyno-stats
#   CMake: -DENABLE_BOLT=ON  (adds the 'bolt-optimize' custom target)
#
# Per-target: enable_pgo_for_target(my_target)
# Per-target override: -D<TARGET>_ENABLE_PGO=ON/OFF

set(PGO_MODE "" CACHE STRING "PGO mode: generate | use | (empty=off)")
set_property(CACHE PGO_MODE PROPERTY STRINGS "" "generate" "use")
set(PGO_PROFILE_DIR "${CMAKE_BINARY_DIR}/pgo-profiles" CACHE PATH
    "Directory for PGO profile data (input for 'use' mode)")

function(enable_pgo_for_target target)
    # Per-target override
    string(TOUPPER "${target}" _tgt_upper)
    set(_tgt_pgo_var "${_tgt_upper}_ENABLE_PGO")
    if(DEFINED ${_tgt_pgo_var})
        if(NOT ${_tgt_pgo_var})
            return()
        endif()
    elseif(NOT PGO_MODE)
        return()
    endif()

    if(PGO_MODE STREQUAL "generate")
        if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
            target_compile_options(${target} PRIVATE -fprofile-generate="${PGO_PROFILE_DIR}")
            target_link_options(${target} PRIVATE -fprofile-generate="${PGO_PROFILE_DIR}")
        elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
            target_compile_options(${target} PRIVATE -fprofile-instr-generate="${PGO_PROFILE_DIR}/%p.profraw")
            target_link_options(${target} PRIVATE -fprofile-instr-generate)
        elseif(MSVC)
            target_link_options(${target} PRIVATE /GENPROFILE:PGD="${PGO_PROFILE_DIR}/${target}.pgd")
        else()
            message(WARNING "PGO generate: unsupported compiler ${CMAKE_CXX_COMPILER_ID}")
            return()
        endif()
        message(STATUS "PGO (generate) enabled for target: ${target} -> ${PGO_PROFILE_DIR}")

    elseif(PGO_MODE STREQUAL "use")
        if(NOT EXISTS "${PGO_PROFILE_DIR}")
            message(WARNING "PGO profile directory not found: ${PGO_PROFILE_DIR}")
            return()
        endif()
        if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
            target_compile_options(${target} PRIVATE -fprofile-use="${PGO_PROFILE_DIR}" -fprofile-correction)
            target_link_options(${target} PRIVATE -fprofile-use="${PGO_PROFILE_DIR}")
        elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
            # Expect merged profdata file
            set(_profdata "${PGO_PROFILE_DIR}/default.profdata")
            if(NOT EXISTS "${_profdata}")
                message(WARNING "PGO: Expected merged profile at ${_profdata}. "
                        "Run: llvm-profdata merge -output=${_profdata} ${PGO_PROFILE_DIR}/*.profraw")
            endif()
            target_compile_options(${target} PRIVATE "-fprofile-instr-use=${_profdata}")
            target_link_options(${target} PRIVATE "-fprofile-instr-use=${_profdata}")
        elseif(MSVC)
            target_link_options(${target} PRIVATE /USEPROFILE:PGD="${PGO_PROFILE_DIR}/${target}.pgd")
        else()
            message(WARNING "PGO use: unsupported compiler ${CMAKE_CXX_COMPILER_ID}")
            return()
        endif()
        message(STATUS "PGO (use) enabled for target: ${target} <- ${PGO_PROFILE_DIR}")

    else()
        message(WARNING "PGO_MODE must be 'generate' or 'use', got: '${PGO_MODE}'")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# BOLT — Binary Optimization and Layout Tool (LLVM post-link optimizer)
#
# BOLT operates on the final linked binary, reordering functions and basic
# blocks based on runtime profile data to improve I-cache and branch
# predictor utilization. Typical gains: 5-15% on throughput-bound workloads.
#
# Requirements: llvm-bolt, perf2bolt (part of LLVM ≥ 14)
# Usage: cmake -DENABLE_BOLT=ON ... && cmake --build . --target bolt-optimize
# ---------------------------------------------------------------------------
option(ENABLE_BOLT "Enable LLVM BOLT post-link optimization targets" OFF)

# Cache path to llvm-bolt so users can override (e.g. /usr/lib/llvm-16/bin/llvm-bolt)
find_program(LLVM_BOLT_EXECUTABLE llvm-bolt DOC "Path to llvm-bolt")
find_program(PERF2BOLT_EXECUTABLE perf2bolt DOC "Path to perf2bolt (llvm-bolt)")

function(add_bolt_target target)
    if(NOT ENABLE_BOLT)
        return()
    endif()

    if(NOT LLVM_BOLT_EXECUTABLE)
        message(WARNING "BOLT: llvm-bolt not found. Install llvm-bolt (part of llvm-dev >= 14).")
        return()
    endif()

    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        message(WARNING "BOLT: Best results with Clang. Current compiler: ${CMAKE_CXX_COMPILER_ID}")
    endif()

    # Instrumented binary path
    get_target_property(_bin_dir ${target} RUNTIME_OUTPUT_DIRECTORY)
    if(NOT _bin_dir)
        set(_bin_dir "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
    endif()
    if(NOT _bin_dir)
        set(_bin_dir "${CMAKE_BINARY_DIR}/bin")
    endif()

    set(_bolt_dir "${CMAKE_BINARY_DIR}/bolt-profiles")
    set(_orig_bin "${_bin_dir}/${target}")
    set(_bolt_bin "${_bin_dir}/${target}.bolt")
    set(_fdata    "${_bolt_dir}/${target}.fdata")

    # BOLT instrumentation: llvm-bolt --instrument produces an instrumented binary
    add_custom_target(bolt-instrument-${target}
        COMMENT "BOLT: instrumenting ${target} for profile collection"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${_bolt_dir}"
        COMMAND ${LLVM_BOLT_EXECUTABLE}
                "${_orig_bin}"
                -instrument
                -instrumentation-file="${_fdata}"
                -o "${_orig_bin}.instrumented"
        DEPENDS ${target}
        VERBATIM
    )

    # BOLT optimize: apply collected fdata profile
    add_custom_target(bolt-optimize-${target}
        COMMENT "BOLT: optimizing ${target} using ${_fdata}"
        COMMAND ${LLVM_BOLT_EXECUTABLE}
                "${_orig_bin}"
                -o "${_bolt_bin}"
                -data="${_fdata}"
                -reorder-blocks=ext-tsp
                -reorder-functions=hfsort
                -split-functions
                -split-all-cold
                -split-eh
                -dyno-stats
        DEPENDS ${target}
        VERBATIM
    )

    message(STATUS "BOLT targets added: bolt-instrument-${target}, bolt-optimize-${target}")
    message(STATUS "  Workflow:")
    message(STATUS "    1. cmake --build . --target bolt-instrument-${target}")
    message(STATUS "    2. Run: ${_orig_bin}.instrumented <workload>")
    message(STATUS "    3. cmake --build . --target bolt-optimize-${target}")
    message(STATUS "    4. Optimized binary: ${_bolt_bin}")
    message(STATUS "  OR use perf record:")
    message(STATUS "    perf record -e cycles:u -j any,u -o perf.data -- ${_orig_bin} <workload>")
    if(PERF2BOLT_EXECUTABLE)
        message(STATUS "    ${PERF2BOLT_EXECUTABLE} -p perf.data -o ${_fdata} ${_orig_bin}")
    endif()
endfunction()
