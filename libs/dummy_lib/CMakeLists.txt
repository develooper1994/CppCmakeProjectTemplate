add_library(dummy_lib)

target_sources(dummy_lib 
    PRIVATE 
        src/greet.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS include
        FILES include/dummy_lib/greet.h
)

target_include_directories(dummy_lib 
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Apply project-wide warnings
set_project_warnings(dummy_lib)

# Install rules
install(TARGETS dummy_lib
    EXPORT dummy_lib_Targets
    FILE_SET HEADERS
)
