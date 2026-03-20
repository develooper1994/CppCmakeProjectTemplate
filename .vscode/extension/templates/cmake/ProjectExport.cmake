# cmake/ProjectExport.cmake

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)

function(install_project_library target export_name)
    # 1. Install rules
    install(TARGETS ${target}
        EXPORT ${export_name}Targets
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    )

    # 2. Generate Config files
    configure_package_config_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/cmake/${export_name}Config.cmake.in"
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}Config.cmake"
        INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )

    write_basic_package_version_file(
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}ConfigVersion.cmake"
        VERSION ${PROJECT_VERSION}
        COMPATIBILITY SameMajorVersion
    )

    install(EXPORT ${export_name}Targets
        FILE ${export_name}Targets.cmake
        NAMESPACE ${export_name}::
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )

    install(FILES
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}Config.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}ConfigVersion.cmake"
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )
endfunction()
