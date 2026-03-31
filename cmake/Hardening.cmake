# cmake/Hardening.cmake

function(enable_hardening target)
    # Check for target-specific override (e.g., -DDUMMY_LIB_ENABLE_HARDENING=ON)
    string(TOUPPER ${target} _tgt_upper)
    set(_tgt_hardening_var "${_tgt_upper}_ENABLE_HARDENING")

    if(DEFINED ${_tgt_hardening_var})
        if(NOT ${${_tgt_hardening_var}})
            return() # Explicitly disabled for this target
        endif()
        message(STATUS "Target-specific Hardening forced ON for: ${target}")
    elseif(NOT ENABLE_HARDENING AND NOT HARDENING_LEVEL)
        return() # Globally disabled and no target override
    endif()

    if(NOT HARDENING_LEVEL)
        set(HARDENING_LEVEL "STANDARD")
    endif()

    if(MSVC)
        # MSVC Hardening flags
        target_compile_options(${target} PRIVATE
            /GS                     # Buffer security check
            /ControlFlowGuard       # Control Flow Guard
            /guard:cf               # Control Flow Guard (link)
            /sdl                    # SDL checks
        )
        if(HARDENING_LEVEL STREQUAL "EXTREME")
            target_compile_options(${target} PRIVATE /Qspectre)
        endif()
        target_link_options(${target} PRIVATE /DYNAMICBASE /NXCOMPAT)
    else()
        # GCC/Clang Hardening flags (STANDARD)
        # Set _FORTIFY_SOURCE=2 for STANDARD, 3 for EXTREME
        if(HARDENING_LEVEL STREQUAL "EXTREME")
            target_compile_definitions(${target} PRIVATE _FORTIFY_SOURCE=3)
        else()
            target_compile_definitions(${target} PRIVATE _FORTIFY_SOURCE=2)
        endif()

        target_compile_options(${target} PRIVATE
            -fstack-protector-strong
            -fstack-clash-protection
            -fcf-protection
            -fPIE
            -fstrict-aliasing
        )
        target_link_options(${target} PRIVATE -pie)

        if(HARDENING_LEVEL STREQUAL "EXTREME")
            target_compile_options(${target} PRIVATE
                -ftrivial-auto-var-init=pattern
                -fno-plt
                -fno-exceptions
                -fno-rtti
                # Policy violations (Fail fast for unsafe C++ constructs)
                -Werror=vla             # Disallow Variable Length Arrays
                -Werror=format-security # Disallow unsafe printf usage
            )
            # Linker flags for EXTREME
            target_link_options(${target} PRIVATE
                -Wl,-z,relro            # Read-only relocation
                -Wl,-z,now              # Immediate binding
                -Wl,-z,noexecstack      # Non-executable stack
            )
        endif()
    endif()
    
    message(STATUS "Security Hardening (${HARDENING_LEVEL}) enabled for target: ${target}")
endfunction()
