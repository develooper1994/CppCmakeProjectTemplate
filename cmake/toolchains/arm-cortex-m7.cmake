# cmake/toolchains/arm-cortex-m7.cmake
# Bare-metal toolchain for ARM Cortex-M7 (ARMv7E-M) with FPv5 double-precision FPU.
# Targets: STM32F7, STM32H7, iMXRT1060/1170, SAME70, Teensy 4.x.
#
# Requirements:
#   sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi
#
# Usage:
#   cmake --preset embedded-cortex-m7  (defined in CMakePresets.json)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR armv7e-m)

if(NOT CMAKE_C_COMPILER)
    set(CMAKE_C_COMPILER arm-none-eabi-gcc)
endif()
if(NOT CMAKE_CXX_COMPILER)
    set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
endif()
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY      arm-none-eabi-objcopy CACHE INTERNAL "")
set(CMAKE_OBJDUMP      arm-none-eabi-objdump CACHE INTERNAL "")
set(CMAKE_SIZE         arm-none-eabi-size    CACHE INTERNAL "")

# Cortex-M7: ARMv7E-M, Thumb-2, double-precision FPv5 (dpfpu)
# Change -mfpu to fpv5-sp-d16 for single-precision variants
set(_CPU_FLAGS "-mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16")
set(_COMMON_FLAGS "${_CPU_FLAGS} -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti -Wall -Wextra")

set(CMAKE_C_FLAGS   "${_COMMON_FLAGS}"         CACHE STRING "C flags")
set(CMAKE_CXX_FLAGS "${_COMMON_FLAGS}"         CACHE STRING "CXX flags")
set(CMAKE_EXE_LINKER_FLAGS
    "--specs=nosys.specs -Wl,--gc-sections -Wl,--print-memory-usage"
    CACHE STRING "Linker flags")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

message(STATUS "[Toolchain] ARM Cortex-M7 (ARMv7E-M + FPv5 bare-metal)")
# Qt is not supported on bare-metal targets (no OS, no display server).
# ENABLE_QT is forced OFF for Generic (bare-metal) builds in CMakeLists.txt.
