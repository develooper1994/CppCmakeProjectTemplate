# cmake/EmbeddedUtils.cmake

function(add_embedded_binary_outputs target)
    if(CMAKE_SYSTEM_NAME STREQUAL "Generic")
        # Generate .bin file
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${target}> $<TARGET_FILE:${target}>.bin
            COMMENT "Generating binary: $<TARGET_FILE_NAME:${target}>.bin"
        )

        # Generate .hex file
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${target}> $<TARGET_FILE:${target}>.hex
            COMMENT "Generating hex: $<TARGET_FILE_NAME:${target}>.hex"
        )

        # Print size information
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_SIZE} --format=berkeley $<TARGET_FILE:${target}>
            COMMENT "Architecture size report:"
        )
    endif()
endfunction()
