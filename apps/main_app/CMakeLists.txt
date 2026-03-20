add_executable(main_app src/main.cpp)

target_link_libraries(main_app 
    PRIVATE 
        dummy_lib 
        project_build_info
)

# Apply project-wide warnings
set_project_warnings(main_app)

# Install rules
install(TARGETS main_app
    EXPORT main_app_Targets
)
