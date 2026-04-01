# cmake/EmbeddedUtils.cmake
# Utilities for embedded / bare-metal targets.
#
# Functions:
#   add_embedded_binary_outputs(target)          — .bin, .hex, size report
#   add_embedded_map_file(target)                — linker map file
#   embedded_print_memory_usage(target)          — detailed section sizes
#   target_set_linker_script(target script)      — attach a linker script

# ---------------------------------------------------------------------------
# add_embedded_binary_outputs(<target>)
# Generates .bin and .hex files and prints a post-build size report.
# Only active when CMAKE_SYSTEM_NAME is "Generic" (bare-metal).
# ---------------------------------------------------------------------------
function(add_embedded_binary_outputs target)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        return()
    endif()

    # Require objcopy / size
    if(NOT CMAKE_OBJCOPY)
        message(WARNING "[EmbeddedUtils] CMAKE_OBJCOPY not set — skipping binary outputs for ${target}")
        return()
    endif()

    # .bin
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O binary
            $<TARGET_FILE:${target}>
            $<TARGET_FILE_DIR:${target}>/$<TARGET_FILE_BASE_NAME:${target}>.bin
        COMMENT "[Embedded] Generating .bin: $<TARGET_FILE_BASE_NAME:${target}>.bin"
        VERBATIM
    )

    # .hex (Intel HEX — used by most flash tools: OpenOCD, J-Link, dfu-util)
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O ihex
            $<TARGET_FILE:${target}>
            $<TARGET_FILE_DIR:${target}>/$<TARGET_FILE_BASE_NAME:${target}>.hex
        COMMENT "[Embedded] Generating .hex: $<TARGET_FILE_BASE_NAME:${target}>.hex"
        VERBATIM
    )

    # .srec (Motorola S-Record — used by some automotive / legacy tools)
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O srec
            $<TARGET_FILE:${target}>
            $<TARGET_FILE_DIR:${target}>/$<TARGET_FILE_BASE_NAME:${target}>.srec
        COMMENT "[Embedded] Generating .srec: $<TARGET_FILE_BASE_NAME:${target}>.srec"
        VERBATIM
    )

    # Size report (Berkeley format: text/data/bss sections)
    if(CMAKE_SIZE)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_SIZE} --format=berkeley $<TARGET_FILE:${target}>
            COMMENT "[Embedded] Memory usage report for ${target}:"
            VERBATIM
        )
    endif()
endfunction()

# ---------------------------------------------------------------------------
# add_embedded_map_file(<target>)
# Adds linker flags to produce a .map file alongside the ELF.
# ---------------------------------------------------------------------------
function(add_embedded_map_file target)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        return()
    endif()

    target_link_options(${target} PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:
            -Wl,-Map=$<TARGET_FILE_DIR:${target}>/$<TARGET_FILE_BASE_NAME:${target}>.map
            -Wl,--cref
        >
    )
endfunction()

# ---------------------------------------------------------------------------
# embedded_print_memory_usage(<target>)
# Dumps a detailed section-by-section size summary using objdump.
# ---------------------------------------------------------------------------
function(embedded_print_memory_usage target)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        return()
    endif()

    find_program(_objdump_bin
        NAMES arm-none-eabi-objdump objdump
        DOC "objdump tool for embedded analysis")

    if(_objdump_bin)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${_objdump_bin} -h $<TARGET_FILE:${target}>
            COMMENT "[Embedded] Section headers for ${target}"
            VERBATIM
        )
    endif()
    unset(_objdump_bin CACHE)
endfunction()

# ---------------------------------------------------------------------------
# target_set_linker_script(<target> <script_path>)
# Attaches a linker script (.ld) to a bare-metal target.
# script_path may be relative (to CMAKE_CURRENT_SOURCE_DIR) or absolute.
# ---------------------------------------------------------------------------
function(target_set_linker_script target script_path)
    if(NOT IS_ABSOLUTE "${script_path}")
        set(script_path "${CMAKE_CURRENT_SOURCE_DIR}/${script_path}")
    endif()

    if(NOT EXISTS "${script_path}")
        message(WARNING "[EmbeddedUtils] Linker script not found: ${script_path}")
        return()
    endif()

    target_link_options(${target} PRIVATE
        $<$<CXX_COMPILER_ID:GNU,Clang>:-T${script_path}>
    )

    # Relink when the linker script changes
    set_target_properties(${target} PROPERTIES
        LINK_DEPENDS "${script_path}"
    )
endfunction()

