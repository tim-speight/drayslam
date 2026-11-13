#!/bin/bash

set -e

PROJECT_ROOT="$(pwd)"
VENV_DIR="$HOME/venvs/drayslam"

echo "Creating venv: $VENV_DIR"

mkdir -p "$HOME/venvs"

python3.15 -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade \
    pip \
    setuptools \
    wheel

if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "Installing requirements.txt"
    pip install -r "$PROJECT_ROOT/requirements.txt"
fi

echo
echo "======================================"
echo "VENV READY"
echo "======================================"
echo
echo "Activate with:"
echo
echo "source $VENV_DIR/bin/activate"
echo
python --version
pip --version
