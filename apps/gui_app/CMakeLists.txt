# apps/gui_app/CMakeLists.txt
# Qt must be explicitly enabled via -DENABLE_QT=ON (or CMakePresets)
# Without the guard, CMake fails at link time when Qt is not installed.

if(NOT ENABLE_QT)
    message(STATUS "gui_app: Skipping build — ENABLE_QT is OFF")
    return()
endif()

add_executable(gui_app src/main.cpp)

target_generate_build_info(gui_app NAMESPACE gui_app_info)

target_link_libraries(gui_app
    PRIVATE
        dummy_lib
        ${QT_LIBRARIES})

if(ENABLE_QML)
    target_compile_definitions(gui_app PRIVATE ENABLE_QML_SUPPORT)
endif()

# Apply project-wide warnings
set_project_warnings(gui_app)

# Apply sanitizers
enable_sanitizers(gui_app)

# Hide console window on Windows for GUI app
set_target_properties(gui_app PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON)

install(TARGETS gui_app
    EXPORT gui_app_Targets)
