# cmake/ProjectOptions.cmake

function(set_project_warnings target)
    # Warning levels: BASE (default), AGGRESSIVE, ERROR
    if(NOT DEFINED WARNING_LEVEL)
        set(WARNING_LEVEL "BASE")
    endif()

    set(CLANG_WARNINGS
        -Wall
        -Wextra # reasonable and standard
        -Wpedantic # warn if non-standard C++ is used
    )

    if(WARNING_LEVEL STREQUAL "AGGRESSIVE" OR WARNING_LEVEL STREQUAL "ERROR")
        list(APPEND CLANG_WARNINGS
            -Wconversion # warn on type conversions that may lose data
            -Wsign-conversion # warn on sign conversions
            -Wshadow # warn the user if a variable declaration shadows one from a parent context
            -Wnon-virtual-dtor # warn if a class with virtual functions has a non-virtual destructor
            -Wold-style-cast # warn for c-style casts
            -Woverloaded-virtual # warn if you overload (not override) a virtual function
            -Wnull-dereference # warn if a null dereference is detected
            -Wdouble-promotion # warn if float is implicit promoted to double
            -Wformat=2 # warn on security issues around functions that format strings
            -Wimplicit-fallthrough # warn on implicit fallthrough in switch statements
        )
    endif()

    if(WARNING_LEVEL STREQUAL "ERROR" OR ENABLE_WERROR)
        list(APPEND CLANG_WARNINGS -Werror)
    endif()

    set(GCC_WARNINGS
        ${CLANG_WARNINGS}
        -Wmisleading-indentation # warn if indentation implies blocks that aren't there
        -Wduplicated-cond # warn if if / else chain has duplicated conditions
        -Wduplicated-branches # warn if if / else branches have duplicated code
        -Wlogical-op # warn about logical operations being used where bitwise were probably wanted
        -Wuseless-cast # warn if you perform a cast to the same type
    )

    set(MSVC_WARNINGS
        /W4 # Baseline reasonable warnings
        /permissive- # standards conformance mode for MSVC compiler.
    )

    if(WARNING_LEVEL STREQUAL "ERROR" OR ENABLE_WERROR)
        list(APPEND MSVC_WARNINGS /WX)
    endif()

    if(MSVC)
        target_compile_options(${target} PRIVATE ${MSVC_WARNINGS})
    elseif(CMAKE_CXX_COMPILER_ID MATCHES ".*Clang")
        target_compile_options(${target} PRIVATE ${CLANG_WARNINGS})
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        target_compile_options(${target} PRIVATE ${GCC_WARNINGS})
    endif()
endfunction()
