add_library(secure_ops STATIC
  src/secure_ops.cpp
)

target_include_directories(secure_ops PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

option(ENABLE_FUZZING "Enable fuzz targets for this library" OFF)
option(ENABLE_AFL "Enable AFL fuzzing for this library (uses afl-clang-fast++)" OFF)

if(ENABLE_FUZZING)
  # libFuzzer target
  add_executable(fuzz_secure_ops ${CMAKE_SOURCE_DIR}/tests/fuzz/fuzz_secure_ops.cpp)
  target_compile_definitions(fuzz_secure_ops PRIVATE FUZZ_LIBFUZZER=1)
  target_include_directories(fuzz_secure_ops PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
  target_link_libraries(fuzz_secure_ops PRIVATE secure_ops)
  set_target_properties(fuzz_secure_ops PROPERTIES EXCLUDE_FROM_ALL TRUE)

  if(ENABLE_AFL)
    add_executable(fuzz_secure_ops_afl ${CMAKE_SOURCE_DIR}/tests/fuzz/fuzz_secure_ops.cpp)
    target_compile_definitions(fuzz_secure_ops_afl PRIVATE FUZZ_AFL=1)
    target_include_directories(fuzz_secure_ops_afl PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    target_link_libraries(fuzz_secure_ops_afl PRIVATE secure_ops)
    set_target_properties(fuzz_secure_ops_afl PROPERTIES EXCLUDE_FROM_ALL TRUE)
  endif()
endif()
