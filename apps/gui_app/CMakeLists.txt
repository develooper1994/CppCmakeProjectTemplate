# apps/gui_app/CMakeLists.txt

add_executable(gui_app src/main.cpp)

target_link_libraries(gui_app 
    PRIVATE 
        dummy_lib 
        project_build_info
        ${QT_LIBRARIES}
)

# Apply project-wide warnings
set_project_warnings(gui_app)

# Hide console window on Windows for GUI app
set_target_properties(gui_app PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON
)
