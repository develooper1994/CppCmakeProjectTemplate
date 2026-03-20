#!/bin/bash

echo "--> Cleaning build artifacts..."

# Remove build directory
if [ -d "build" ]; then
    rm -rf build
    echo "    Removed 'build/'"
fi

# Remove generated compile_commands.json if linked
if [ -f "compile_commands.json" ]; then
    rm compile_commands.json
    echo "    Removed 'compile_commands.json'"
fi

echo "--> Clean completed."
