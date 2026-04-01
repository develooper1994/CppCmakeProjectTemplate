# apps/gui_app/CMakeLists.txt
# Qt must be explicitly enabled via -DENABLE_QT=ON (or CMakePresets)
# Without the guard, CMake skips this target gracefully.

if(NOT ENABLE_QT)
    message(STATUS "gui_app: Skipping build — ENABLE_QT is OFF (pass -DENABLE_QT=ON to build)")
    return()
endif()

add_executable(gui_app src/main.cpp)

target_generate_build_info(gui_app NAMESPACE gui_app_info)

# Link Qt via the centralised helper (auto-detects Qt5/Qt6, sets AUTOMOC/AUTOUIC/AUTORCC)
if(ENABLE_QML)
    target_link_qt(gui_app QML)
else()
    target_link_qt(gui_app)
endif()

# Also link our own library
target_link_libraries(gui_app PRIVATE dummy_lib)

if(COMMAND project_apply_allocator)
    project_apply_allocator(gui_app)
endif()

# Apply project-wide warnings
set_project_warnings(gui_app)

# Apply sanitizers
enable_sanitizers(gui_app)

# Apply OpenMP if requested
apply_openmp_defaults(gui_app)

# Hide console window on Windows / create macOS bundle for GUI apps
set_target_properties(gui_app PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON)

install(TARGETS gui_app
    EXPORT gui_app_Targets)
