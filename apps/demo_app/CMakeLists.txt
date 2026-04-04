# apps/demo_app/CMakeLists.txt

add_executable(demo_app src/main.cpp)

target_link_libraries(demo_app
    PRIVATE
        dummy_lib
        project_feature_flags)

if(COMMAND project_apply_allocator)
    project_apply_allocator(demo_app)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(demo_app)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(demo_app)
endif()

if(COMMAND add_embedded_binary_outputs)
    add_embedded_binary_outputs(demo_app)
endif()

install(TARGETS demo_app
    EXPORT demo_app_Targets)
