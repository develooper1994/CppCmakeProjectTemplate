# tests/CMakeLists.txt

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
  SYSTEM # Isolation for external code
)
FetchContent_MakeAvailable(googletest)

add_subdirectory(unit)
