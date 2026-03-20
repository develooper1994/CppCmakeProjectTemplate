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

def main():
    system = platform.system()
    preset = "gcc-debug" # Default for Linux

    if system == "Windows":
        preset = "msvc-debug"
    elif system == "Darwin": # macOS
        preset = "clang-debug"

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
