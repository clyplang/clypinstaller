# Build script for Windows using Nuitka compiler

# Check if Nuitka is installed
if (-not (python -m nuitka --version 2>$null)) {
    Write-Host "Nuitka compiler could not be found. Please install it first."
    exit 1
}

# Compile the project
python -m nuitka install.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build succeeded."
} else {
    Write-Host "Build failed."
    exit 1
}
