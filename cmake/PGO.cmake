# cmake/PGO.cmake — Profile-Guided Optimization support
#
# Two-phase workflow:
#   Phase 1 (Instrument): cmake -DPGO_MODE=generate ...
#     Builds with instrumentation. Run the binary to produce profile data.
#   Phase 2 (Optimize):   cmake -DPGO_MODE=use -DPGO_PROFILE_DIR=<dir> ...
#     Rebuilds using collected profile data for optimized codegen.
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
