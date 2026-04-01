add_executable(extreme_app
  src/main.cpp
)

target_include_directories(extreme_app PRIVATE
  ${CMAKE_SOURCE_DIR}/libs/secure_ops/include
)

target_link_libraries(extreme_app PRIVATE secure_ops)

# Ensure extreme-app is built with project hardening in CI; it should be
# written to avoid exceptions/RTTI so it passes `extreme` profile.
set_target_properties(extreme_app PROPERTIES EXCLUDE_FROM_ALL FALSE)
