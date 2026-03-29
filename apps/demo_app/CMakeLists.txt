cmake_minimum_required(VERSION 3.25)
project(demo_app VERSION 1.0.0 LANGUAGES CXX)

add_executable(demo_app src/main.cpp)
target_link_libraries(demo_app PRIVATE dummy_lib)
