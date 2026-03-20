#!/bin/bash
set -e

# Default preset
PRESET="gcc-debug"

# Help message
function show_help {
    echo "Usage: $0 [preset]"
    echo ""
    echo "Presets:"
    echo "  gcc-debug (default)"
    echo "  gcc-release"
    echo "  clang-debug"
    echo "  clang-release"
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

if [ ! -z "$1" ]; then
    PRESET=$1
fi

echo "--> Building with preset: $PRESET"

# Configure
cmake --preset $PRESET

# Build
cmake --build --preset $PRESET

echo "--> Build completed successfully."
