# cmake/ProjectExport.cmake
# Function install_project_library(target export_name):
# - Generate install rules (libraries, headers, binaries)
# - Generate CMake package config files (for find_package)
# - Write the export set

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
        FILE_SET HEADERS DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    )

    # 2. Locate the Config.cmake.in template
    # Prefer a library-specific template, otherwise fall back to the global template.
    set(_config_in "${CMAKE_CURRENT_SOURCE_DIR}/cmake/${export_name}Config.cmake.in")
    if(NOT EXISTS "${_config_in}")
        set(_config_in "${PROJECT_SOURCE_DIR}/cmake/LibraryConfig.cmake.in")
    endif()

    if(NOT EXISTS "${_config_in}")
        message(FATAL_ERROR
            "install_project_library: Config template not found.\n"
            "Expected: ${CMAKE_CURRENT_SOURCE_DIR}/cmake/${export_name}Config.cmake.in\n"
            "Fallback : ${PROJECT_SOURCE_DIR}/cmake/LibraryConfig.cmake.in"
        )
    endif()

    # 3. Generate config files
    configure_package_config_file(
        "${_config_in}"
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}Config.cmake"
        INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )

    write_basic_package_version_file(
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}ConfigVersion.cmake"
        VERSION ${PROJECT_VERSION}
        COMPATIBILITY SameMajorVersion
    )

    # 4. Write the export set
    install(EXPORT ${export_name}Targets
        FILE ${export_name}Targets.cmake
        NAMESPACE ${export_name}::
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )

    # 5. Install the config files
    install(FILES
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}Config.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/${export_name}ConfigVersion.cmake"
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${export_name}"
    )
endfunction()
