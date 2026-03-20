include(GenerateExportHeader)

add_library(dummy_lib)

target_sources(dummy_lib 
    PRIVATE 
        src/greet.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/dummy_lib/greet.h
)

# Generate export header for Windows/DLL support
# Place it in the binary directory to keep source clean
generate_export_header(dummy_lib
    BASE_NAME DUMMY_LIB
    EXPORT_FILE_NAME "${CMAKE_CURRENT_BINARY_DIR}/generated/dummy_lib/dummy_lib_export.h"
)

target_include_directories(dummy_lib 
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated> # Build tree includes
        $<INSTALL_INTERFACE:include>
)

# Professional visibility settings (Hidden by default)
set_target_properties(dummy_lib PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

if(ENABLE_COVERAGE)
    enable_code_coverage(dummy_lib)
endif()

enable_sanitizers(dummy_lib)

# Apply project-wide warnings
set_project_warnings(dummy_lib)

# Install rules
install(TARGETS dummy_lib
    EXPORT dummy_lib_Targets
    FILE_SET HEADERS
)
