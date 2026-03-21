#!/usr/bin/env python3
import os
import sys
import subprocess
import platform

def run_command(command):
    print(f"--> Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        sys.exit(1)

# Available presets (from CMakePresets.json)
LINUX_PRESETS = [
    "gcc-debug-static-x86_64",
    "gcc-debug-dynamic-x86_64",
    "gcc-release-static-x86_64",
    "clang-debug-static-x86_64",
    "clang-release-static-x86_64",
]
WINDOWS_PRESETS = [
    "msvc-debug-static-x64",
    "msvc-debug-dynamic-x64",
    "msvc-release-static-x64",
    "msvc-release-dynamic-x64",
]
MACOS_PRESETS = [
    "clang-debug-static-x86_64",
    "clang-release-static-x86_64",
]

# Default preset per platform
DEFAULT_PRESET = {
    "Linux": "gcc-debug-static-x86_64",
    "Windows": "msvc-debug-static-x64",
    "Darwin": "clang-debug-static-x86_64",
}

def main():
    system = platform.system()
    preset = DEFAULT_PRESET.get(system, "gcc-debug-static-x86_64")

    if len(sys.argv) > 1:
        preset = sys.argv[1]

    print(f"--> Building C++ Project on {system} with preset: {preset}")

    # 1. Configure
    run_command(["cmake", "--preset", preset])

    # 2. Build
    run_command(["cmake", "--build", "--preset", preset])

    print("--> Build completed successfully.")

if __name__ == "__main__":
    main()
