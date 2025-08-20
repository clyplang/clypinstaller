#!/bin/sh

# Build script for Linux/macOS using Nuitka compiler

# Check if Nuitka is installed
if ! python -m nuitka --version >/dev/null 2>&1; then
    echo "Nuitka compiler could not be found. Please install it first."
    exit 1
fi

# Compile the project
python -m nuitka install.py
status=$?

if [ $status -eq 0 ]; then
    echo "Build succeeded."
else
    echo "Build failed."
    exit 1
fi
