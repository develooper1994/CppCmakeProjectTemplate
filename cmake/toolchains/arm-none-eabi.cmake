# cmake/toolchains/arm-none-eabi.cmake
# Standard Toolchain for ARM Cortex-M (Bare Metal)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# 1. Setup paths to your local GNU ARM Toolchain
# You can override these from the command line: -DCMAKE_C_COMPILER=...
if(NOT CMAKE_C_COMPILER)
    set(CMAKE_C_COMPILER arm-none-eabi-gcc)
endif()
if(NOT CMAKE_CXX_COMPILER)
    set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
endif()

set(CMAKE_OBJCOPY arm-none-eabi-objcopy CACHE INTERNAL "objcopy tool")
set(CMAKE_SIZE    arm-none-eabi-size    CACHE INTERNAL "size tool")

# 2. Architecture specific flags (Example: Cortex-M4)
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(COMMON_FLAGS "${CPU_FLAGS} -ffunction-sections -fdata-sections -Wall")

set(CMAKE_C_FLAGS   "${COMMON_FLAGS}" CACHE STRING "C flags")
set(CMAKE_CXX_FLAGS "${COMMON_FLAGS}" CACHE STRING "C++ flags")

# 3. Linker flags (Note: Linker script is usually required for bare metal)
# set(CMAKE_EXE_LINKER_FLAGS "--specs=nosys.specs -Wl,--gc-sections -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld" CACHE STRING "Linker flags")

# 4. Search policy
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
# Qt is not supported on bare-metal targets (no OS, no display server).
# ENABLE_QT is forced OFF for Generic (bare-metal) builds in CMakeLists.txt.
