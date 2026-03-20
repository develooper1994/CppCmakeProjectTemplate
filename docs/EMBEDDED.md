# Embedded & Cross-Compilation Guide

This project template is designed to support professional embedded development using custom GNU compilers (e.g., `arm-none-eabi-gcc`, `riscv64-unknown-elf-gcc`).

## 1. Using a Custom Toolchain

The core of cross-compilation in CMake is the **Toolchain File**. You can find an example at `cmake/toolchains/arm-none-eabi.cmake`.

### Scenario A: Using the Template's ARM Toolchain
1.  **Modify**: Open `cmake/toolchains/arm-none-eabi.cmake`.
2.  **Paths**: Update `CMAKE_C_COMPILER` to point to your `arm-none-eabi-gcc` if it's not in your PATH.
3.  **Flags**: Update `CPU_FLAGS` (e.g., `-mcpu=cortex-m7`, `-mfpu=fpv5-d16`) for your specific chip.

### Scenario B: Manufacturer Provided Toolchain (BSP/SDK)
Board vendors (ST, NXP, Nordic, Yocto/PetaLinux) often provide their own toolchain environment.

**Option 1: Using the Vendor's CMake File**
If the SDK provides a `toolchain.cmake` file:
1.  Open `CMakePresets.json`.
2.  Create a new preset pointing to the vendor's file:
    ```json
    {
      "name": "vendor-sdk",
      "inherits": "base",
      "toolchainFile": "/opt/vendor-sdk/sysroots/x86_64/cmake/OEToolchainConfig.cmake",
      "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" }
    }
    ```

**Option 2: Using a Custom GNU Compiler (Proprietary/Forked GCC)**
If you have a special GCC fork (e.g., `tricore-gcc`, `riscv-unknown-elf-gcc`) provided as binaries:
1.  Copy `cmake/toolchains/arm-none-eabi.cmake` to `cmake/toolchains/my-custom-board.cmake`.
2.  Edit the compiler paths explicitly:
    ```cmake
    set(CMAKE_C_COMPILER "/opt/my-board-sdk/bin/custom-mcu-gcc")
    set(CMAKE_CXX_COMPILER "/opt/my-board-sdk/bin/custom-mcu-g++")
    ```
3.  Set the Sysroot (if required by the SDK):
    ```cmake
    set(CMAKE_SYSROOT "/opt/my-board-sdk/sysroot")
    set(CMAKE_FIND_ROOT_PATH "${CMAKE_SYSROOT}")
    ```

## 2. Building via Presets (Recommended)

The template includes a pre-configured preset for ARM development.

### Terminal:
```bash
# Configure for ARM
cmake --preset embedded-arm-none-eabi

# Build
cmake --build --preset embedded-arm-none-eabi
```

### VS Code GUI:
1. Click on the **CMake: [Preset Name]** in the status bar.
2. Select **Embedded: ARM (Cortex-M4)**.
3. Click **Build**.

## 3. Post-Build Artifacts

When `CMAKE_SYSTEM_NAME` is set to `Generic` (standard for bare-metal), the template automatically generates:
-   **`.elf`**: The standard debug image.
-   **`.bin`**: Raw binary image for flashing.
-   **`.hex`**: Intel Hex format.
-   **Size Report**: Automatically prints the Flash/RAM usage after build.

These are handled by the `add_embedded_binary_outputs()` function in `cmake/EmbeddedUtils.cmake`.

## 4. Overriding Compiler Paths manually

If you don't want to modify the toolchain file, you can pass the paths directly during configuration:

```bash
cmake --preset embedded-arm-none-eabi \
      -DCMAKE_C_COMPILER=/path/to/custom-gcc \
      -DCMAKE_CXX_COMPILER=/path/to/custom-g++
```

## 5. Tips for Custom SDKs

-   **Include Directories**: Add your SDK's include paths in the toolchain file using `include_directories()`.
-   **System Libraries**: Use `target_link_libraries(your_app PRIVATE -lnosys)` for bare-metal stubs if using Newlib.
-   **QML/Qt**: By default, Qt and Sanitizers are disabled for `Generic` systems to save space and avoid compatibility issues.
