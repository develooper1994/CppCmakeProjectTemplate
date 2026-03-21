# apps/CMakeLists.txt
add_subdirectory(main_app)

if(ENABLE_QT)
    add_subdirectory(gui_app)
endif()
