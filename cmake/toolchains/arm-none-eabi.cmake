# cmake/toolchains/arm-none-eabi.cmake
# Example toolchain for ARM Cortex-M

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Specify the cross compiler
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)

# Specify target flags
set(OBJECT_GEN_FLAGS "-mthumb -fno-builtin -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=softfp")
set(CMAKE_C_FLAGS "${OBJECT_GEN_FLAGS} ${CMAKE_C_FLAGS}")
set(CMAKE_CXX_FLAGS "${OBJECT_GEN_FLAGS} ${CMAKE_CXX_FLAGS}")

# Inhibit search in default paths
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
