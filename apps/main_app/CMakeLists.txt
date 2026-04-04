# apps/main_app/CMakeLists.txt

add_executable(main_app src/main.cpp)

target_generate_build_info(main_app NAMESPACE main_app_info)

target_link_libraries(main_app
    PRIVATE
        dummy_lib
        project_feature_flags)

if(COMMAND project_apply_allocator)
    project_apply_allocator(main_app)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(main_app)
endif()

if(COMMAND enable_hardening)
    enable_hardening(main_app)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(main_app)
endif()

if(COMMAND add_embedded_binary_outputs)
    add_embedded_binary_outputs(main_app)
endif()

install(TARGETS main_app
    EXPORT main_app_Targets)
