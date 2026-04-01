# cmake/Allocators.cmake
# Optional allocator backend wiring for executables/benchmarks.
#
# Discovery order (per backend):
#   1. find_package (CONFIG) — works with vcpkg, Conan, system installs
#   2. find_library           — bare system .so / .a
#   3. FetchContent            — auto-download from upstream GitHub (opt-in)
#
# Set ALLOCATOR_FETCHCONTENT=ON to enable the FetchContent fallback.

include(FetchContent)

if(NOT DEFINED CACHE{ENABLE_ALLOCATOR})
    set(ENABLE_ALLOCATOR "default" CACHE STRING
        "Allocator backend (default|mimalloc|jemalloc|tcmalloc)")
endif()
set_property(CACHE ENABLE_ALLOCATOR PROPERTY STRINGS default mimalloc jemalloc tcmalloc)

option(ENABLE_ALLOCATOR_OVERRIDE_ALL
    "Apply selected allocator backend to all executables/benchmarks"
    OFF)

option(ALLOCATOR_FETCHCONTENT
    "Allow FetchContent download of allocator libraries when not found locally"
    OFF)

function(_allocator_find_library out_var)
    set(candidates ${ARGN})
    set(found "")
    foreach(name IN LISTS candidates)
        find_library(_alloc_lib NAMES ${name})
        if(_alloc_lib)
            set(found "${_alloc_lib}")
            break()
        endif()
    endforeach()
    set(${out_var} "${found}" PARENT_SCOPE)
endfunction()

function(target_use_allocator target allocator)
    if(NOT TARGET ${target})
        message(FATAL_ERROR "target_use_allocator: target '${target}' does not exist")
    endif()

    if(allocator STREQUAL "" OR allocator STREQUAL "default")
        return()
    endif()

    string(TOLOWER "${allocator}" _allocator)
    set(_allocator_allowed mimalloc jemalloc tcmalloc)
    if(NOT _allocator IN_LIST _allocator_allowed)
        message(FATAL_ERROR
            "Unsupported allocator backend: ${allocator}. "
            "Allowed values: default, mimalloc, jemalloc, tcmalloc")
    endif()

    if(_allocator STREQUAL "mimalloc")
        find_package(mimalloc CONFIG QUIET)
        if(TARGET mimalloc-static)
            target_link_libraries(${target} PRIVATE mimalloc-static)
        elseif(TARGET mimalloc)
            target_link_libraries(${target} PRIVATE mimalloc)
        else()
            _allocator_find_library(_mimalloc_lib mimalloc mimalloc-static)
            if(_mimalloc_lib)
                target_link_libraries(${target} PRIVATE ${_mimalloc_lib})
            elseif(ALLOCATOR_FETCHCONTENT)
                FetchContent_Declare(mimalloc
                    GIT_REPOSITORY https://github.com/microsoft/mimalloc.git
                    GIT_TAG        v2.1.7
                    GIT_SHALLOW    TRUE)
                set(MI_BUILD_TESTS OFF CACHE BOOL "" FORCE)
                set(MI_BUILD_SHARED OFF CACHE BOOL "" FORCE)
                FetchContent_MakeAvailable(mimalloc)
                target_link_libraries(${target} PRIVATE mimalloc-static)
            else()
                message(FATAL_ERROR
                    "ENABLE_ALLOCATOR=mimalloc was requested but mimalloc was not found. "
                    "Install it (system/conan/vcpkg), enable ALLOCATOR_FETCHCONTENT=ON, "
                    "or use --allocator default.")
            endif()
        endif()
        target_compile_definitions(${target} PRIVATE PROJECT_ALLOCATOR_MIMALLOC=1)
        return()
    endif()

    if(_allocator STREQUAL "jemalloc")
        find_package(jemalloc CONFIG QUIET)
        if(TARGET jemalloc::jemalloc)
            target_link_libraries(${target} PRIVATE jemalloc::jemalloc)
        else()
            _allocator_find_library(_jemalloc_lib jemalloc_pic jemalloc)
            if(NOT _jemalloc_lib)
                message(FATAL_ERROR
                    "ENABLE_ALLOCATOR=jemalloc was requested but jemalloc was not found. "
                    "Install it via system package manager, Conan (-o allocator=jemalloc), "
                    "or vcpkg (--overlay-triplets with jemalloc feature).")
            endif()
            target_link_libraries(${target} PRIVATE ${_jemalloc_lib})
        endif()
        target_compile_definitions(${target} PRIVATE PROJECT_ALLOCATOR_JEMALLOC=1)
        return()
    endif()

    if(_allocator STREQUAL "tcmalloc")
        find_package(gperftools CONFIG QUIET)
        if(TARGET gperftools::tcmalloc_minimal)
            target_link_libraries(${target} PRIVATE gperftools::tcmalloc_minimal)
        else()
            _allocator_find_library(_tcmalloc_lib tcmalloc_minimal tcmalloc)
            if(NOT _tcmalloc_lib)
                message(FATAL_ERROR
                    "ENABLE_ALLOCATOR=tcmalloc was requested but tcmalloc was not found. "
                    "Install it via system package manager, Conan (-o allocator=tcmalloc), "
                    "or vcpkg.")
            endif()
            target_link_libraries(${target} PRIVATE ${_tcmalloc_lib})
        endif()
        target_compile_definitions(${target} PRIVATE PROJECT_ALLOCATOR_TCMALLOC=1)
        return()
    endif()

endfunction()

function(project_apply_allocator target)
    if(ENABLE_ALLOCATOR_OVERRIDE_ALL AND NOT ENABLE_ALLOCATOR STREQUAL "default")
        target_use_allocator(${target} "${ENABLE_ALLOCATOR}")
    endif()
endfunction()
