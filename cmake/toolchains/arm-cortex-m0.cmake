# cmake/toolchains/arm-cortex-m0.cmake
# Bare-metal toolchain for ARM Cortex-M0 / M0+ (ARMv6-M).
# Targets: STM32F0, STM32L0, nRF51, RP2040, Atmel SAMD series.
#
# Requirements:
#   sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi
#   # or download ARM GNU Toolchain from: https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads
#
# Usage:
#   cmake --preset embedded-cortex-m0  (defined in CMakePresets.json)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR armv6-m)

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

# Cortex-M0 flags: ARMv6-M, Thumb only (no Thumb-2), soft-float
set(_CPU_FLAGS "-mcpu=cortex-m0plus -mthumb -mfloat-abi=soft")
set(_COMMON_FLAGS "${_CPU_FLAGS} -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti -Wall -Wextra")

set(CMAKE_C_FLAGS   "${_COMMON_FLAGS}"         CACHE STRING "C flags")
set(CMAKE_CXX_FLAGS "${_COMMON_FLAGS}"         CACHE STRING "CXX flags")
set(CMAKE_EXE_LINKER_FLAGS
    "--specs=nosys.specs -Wl,--gc-sections -Wl,--print-memory-usage"
    CACHE STRING "Linker flags")

# Bare-metal: no host binaries/libraries
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

message(STATUS "[Toolchain] ARM Cortex-M0+ (ARMv6-M bare-metal)")
# Qt is not supported on bare-metal targets (no OS, no display server).
# ENABLE_QT is forced OFF for Generic (bare-metal) builds in CMakeLists.txt.
