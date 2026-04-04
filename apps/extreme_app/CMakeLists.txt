# apps/extreme_app/CMakeLists.txt

add_executable(extreme_app src/main.cpp)

target_link_libraries(extreme_app
    PRIVATE
        secure_ops
        project_feature_flags)

if(COMMAND project_apply_allocator)
    project_apply_allocator(extreme_app)
endif()

if(COMMAND set_project_warnings)
    set_project_warnings(extreme_app)
endif()

if(COMMAND enable_hardening)
    enable_hardening(extreme_app)
endif()

if(COMMAND enable_sanitizers)
    enable_sanitizers(extreme_app)
endif()

if(COMMAND add_embedded_binary_outputs)
    add_embedded_binary_outputs(extreme_app)
endif()

install(TARGETS extreme_app
    EXPORT extreme_app_Targets)
