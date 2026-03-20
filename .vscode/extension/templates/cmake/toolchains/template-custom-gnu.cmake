# cmake/toolchains/template-custom-gnu.cmake
# Template for integrating a Custom GNU Compiler (SDK/BSP/Forked GCC)
# 
# USAGE:
# 1. Copy this file to 'cmake/toolchains/my-board.cmake'
# 2. Update the paths and flags below
# 3. Add a new preset in CMakePresets.json pointing to your new file

# --- 1. System Name & Processor ---
set(CMAKE_SYSTEM_NAME Generic)      # 'Generic' is standard for bare-metal
set(CMAKE_SYSTEM_PROCESSOR unknown) # Update this (e.g., arm, riscv, tricore)

# --- 2. Compiler Paths ---
# If your compiler is in the global PATH, you can just use the binary name.
# Otherwise, provide the absolute path to the SDK binaries.
set(TOOLCHAIN_PREFIX "/opt/my-sdk/bin/custom-arch-") 

set(CMAKE_C_COMPILER   "${TOOLCHAIN_PREFIX}gcc")
set(CMAKE_CXX_COMPILER "${TOOLCHAIN_PREFIX}g++")
set(CMAKE_ASM_COMPILER "${TOOLCHAIN_PREFIX}gcc")

# Optional: Specify other tools if needed for manual commands
set(CMAKE_OBJCOPY      "${TOOLCHAIN_PREFIX}objcopy" CACHE INTERNAL "objcopy tool")
set(CMAKE_SIZE         "${TOOLCHAIN_PREFIX}size"    CACHE INTERNAL "size tool")

# --- 3. Sysroot (Optional) ---
# If your SDK provides a sysroot (libraries, headers), set it here.
# set(CMAKE_SYSROOT "/opt/my-sdk/sysroot")
# set(CMAKE_FIND_ROOT_PATH "${CMAKE_SYSROOT}")

# --- 4. Compiler & Linker Flags ---
# Adjust these based on your hardware (FPU, Endianness, Instruction Set)
set(MCU_FLAGS "-mcpu=cortex-m7 -mfloat-abi=hard -mfpu=fpv5-d16")

set(CMAKE_C_FLAGS   "${MCU_FLAGS} -Wall -Wextra" CACHE STRING "C flags")
set(CMAKE_CXX_FLAGS "${MCU_FLAGS} -Wall -Wextra" CACHE STRING "C++ flags")

# Linker Script and Specs (Vital for embedded)
set(LINKER_SCRIPT "${CMAKE_CURRENT_LIST_DIR}/linker.ld") # Assumes linker.ld is in the same folder
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T ${LINKER_SCRIPT} --specs=nosys.specs -Wl,--gc-sections" CACHE STRING "Linker flags")

# --- 5. Search Behavior (Cross-Compilation Best Practices) ---
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER) # Search for programs on host
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)  # Search for libs in target sysroot
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)  # Search for headers in target sysroot
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
