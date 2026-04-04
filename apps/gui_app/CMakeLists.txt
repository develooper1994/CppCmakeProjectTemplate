# apps/gui_app/CMakeLists.txt
if(NOT ENABLE_QT)
    message(STATUS "gui_app: Skipping — ENABLE_QT is OFF")
    return()
endif()

add_executable(gui_app src/main.cpp)

if(ENABLE_QML)
    target_link_qt(gui_app QML)
else()
    target_link_qt(gui_app)
endif()

target_link_libraries(gui_app
    PRIVATE
        dummy_lib
        project_feature_flags)

if(COMMAND project_apply_allocator)
    project_apply_allocator(gui_app)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(gui_app)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(gui_app)
endif()

if(COMMAND add_embedded_binary_outputs)
    add_embedded_binary_outputs(gui_app)
endif()

set_target_properties(gui_app PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON)

install(TARGETS gui_app
    EXPORT gui_app_Targets)
