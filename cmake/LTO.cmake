# cmake/LTO.cmake — Link-Time Optimization support
#
# Usage:
#   include(LTO)
#   enable_lto_for_target(my_target)        # per-target
#   enable_lto_for_target(my_target THIN)   # thin LTO (Clang)
#
# Global option: -DENABLE_LTO=ON enables LTO for all targets that call
# enable_lto_for_target(). Per-target override: -D<TARGET>_ENABLE_LTO=ON/OFF

include(CheckIPOSupported)

function(enable_lto_for_target target)
    # Parse optional THIN argument
    set(_lto_thin FALSE)
    if("THIN" IN_LIST ARGN)
        set(_lto_thin TRUE)
    endif()

    # Per-target override
    string(TOUPPER "${target}" _tgt_upper)
    set(_tgt_lto_var "${_tgt_upper}_ENABLE_LTO")
    if(DEFINED ${_tgt_lto_var})
        if(NOT ${_tgt_lto_var})
            return()
        endif()
    elseif(NOT ENABLE_LTO)
        return()
    endif()

    # Check compiler support
    check_ipo_supported(RESULT _ipo_supported OUTPUT _ipo_output)
    if(NOT _ipo_supported)
        message(WARNING "LTO is not supported by the current compiler: ${_ipo_output}")
        return()
    endif()

    set_target_properties(${target} PROPERTIES INTERPROCEDURAL_OPTIMIZATION TRUE)

    # Thin LTO for Clang
    if(_lto_thin AND CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        target_compile_options(${target} PRIVATE -flto=thin)
        target_link_options(${target} PRIVATE -flto=thin)
        message(STATUS "LTO (thin) enabled for target: ${target}")
    else()
        message(STATUS "LTO enabled for target: ${target}")
    endif()
endfunction()
