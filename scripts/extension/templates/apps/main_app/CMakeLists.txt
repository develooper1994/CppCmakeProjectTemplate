add_executable(main_app src/main.cpp)

# Generate specific build info for the main app
# Inherits project version by default
target_generate_build_info(main_app NAMESPACE main_app_info)

target_link_libraries(main_app 
    PRIVATE 
        dummy_lib 
)

# Apply project-wide warnings
set_project_warnings(main_app)

# Apply sanitizers (ASan/UBSan/TSan) if enabled
enable_sanitizers(main_app)

# Apply embedded tools if applicable
add_embedded_binary_outputs(main_app)

# Install rules
install(TARGETS main_app
    EXPORT main_app_Targets
)
