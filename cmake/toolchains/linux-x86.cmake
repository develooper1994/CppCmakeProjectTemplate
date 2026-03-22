# cmake/toolchains/linux-x86.cmake
# 32-bit x86 compilation on x86_64 Linux host.
#
# Requirements (must install before using x86 presets):
#   GCC:   sudo apt install gcc-multilib g++-multilib
#   Clang: sudo apt install libc6-dev-i386 libstdc++-dev:i386
#
# Usage: referenced by CMakePresets.json gcc/clang-*-x86 presets via
#   "toolchainFile": "${sourceDir}/cmake/toolchains/linux-x86.cmake"
#
# Design notes:
#   - We do NOT set CMAKE_SYSTEM_NAME/PROCESSOR to avoid triggering CMake's
#     cross-compilation mode which would break system library discovery.
#   - Only compiler flags are set here; the -m32 flag is passed to the compiler
#     which then handles both compile and link phases via the driver.
#   - We deliberately omit CMAKE_EXE_LINKER_FLAGS_INIT and
#     CMAKE_SHARED_LINKER_FLAGS_INIT to prevent -m32 being passed twice
#     (once via compiler flags and once via linker flags).

# Check multilib availability
execute_process(
    COMMAND ${CMAKE_C_COMPILER} -m32 -x c - -o /dev/null
    INPUT_FILE /dev/null
    RESULT_VARIABLE _multilib_check
    ERROR_QUIET
    OUTPUT_QUIET
)
if(NOT _multilib_check EQUAL 0)
    message(FATAL_ERROR
        "32-bit compilation requires gcc-multilib / g++-multilib.\n"
        "Install with: sudo apt install gcc-multilib g++-multilib\n"
        "(Clang: sudo apt install libc6-dev-i386)"
    )
endif()

set(CMAKE_C_FLAGS_INIT   "-m32")
set(CMAKE_CXX_FLAGS_INIT "-m32")
# Note: -m32 in compiler flags is forwarded to the linker by the GCC driver.
# Explicitly setting CMAKE_EXE_LINKER_FLAGS_INIT would cause duplication.
