# cmake/BuildCache.cmake — Build caching via ccache/sccache
#
# Automatically detects and configures ccache or sccache as the compiler
# launcher when -DENABLE_CCACHE=ON (default: ON if found).
#
# Priority: sccache > ccache (sccache handles more scenarios).
# Override: -DCACHE_PROGRAM=/path/to/ccache

option(ENABLE_CCACHE "Enable compiler caching (ccache/sccache)" ON)

if(ENABLE_CCACHE)
    # Allow explicit override
    if(CACHE_PROGRAM)
        if(EXISTS "${CACHE_PROGRAM}")
            set(_cache_prog "${CACHE_PROGRAM}")
        else()
            message(WARNING "CACHE_PROGRAM specified but not found: ${CACHE_PROGRAM}")
            set(_cache_prog "")
        endif()
    else()
        # Auto-detect: prefer sccache, fall back to ccache
        find_program(_cache_prog sccache)
        if(NOT _cache_prog)
            find_program(_cache_prog ccache)
        endif()
    endif()

    if(_cache_prog)
        message(STATUS "Build cache enabled: ${_cache_prog}")
        set(CMAKE_C_COMPILER_LAUNCHER   "${_cache_prog}" CACHE STRING "" FORCE)
        set(CMAKE_CXX_COMPILER_LAUNCHER "${_cache_prog}" CACHE STRING "" FORCE)
    else()
        message(STATUS "Build cache: no ccache/sccache found (builds will not be cached)")
    endif()
endif()
