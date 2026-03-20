# Embedded & Cross-Compilation Guide

This project template is designed to support professional embedded development using custom GNU compilers (e.g., `arm-none-eabi-gcc`, `riscv64-unknown-elf-gcc`).

## 1. Using a Custom Toolchain

The core of cross-compilation in CMake is the **Toolchain File**. You can find an example at `cmake/toolchains/arm-none-eabi.cmake`.

### Steps to Integrate Your Compiler:
1.  **Create/Modify Toolchain**: Open `cmake/toolchains/arm-none-eabi.cmake` and update the `CMAKE_C_COMPILER` and `CMAKE_CXX_COMPILER` paths to point to your SDK's binaries.
2.  **Define Architecture Flags**: Update `CPU_FLAGS` (e.g., `-mcpu=cortex-m7`, `-mfloat-abi=hard`) to match your target hardware.
3.  **Linker Script**: If your system requires a linker script (`.ld`), uncomment and update the `CMAKE_EXE_LINKER_FLAGS` line.

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
