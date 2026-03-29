cmake_minimum_required(VERSION 3.25)
project(demo_app VERSION ${PROJECT_BASE_VERSION} LANGUAGES CXX)

add_executable(demo_app src/main.cpp)
target_link_libraries(demo_app PRIVATE dummy_lib)
