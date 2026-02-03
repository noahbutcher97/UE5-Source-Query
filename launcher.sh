#!/bin/bash
# UE5 Source Query - Launcher (Linux/Mac)

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 not found."
        exit 1
    fi
    # Warn but try anyway
fi

# Bootstrap logic
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source "$VENV_DIR/bin/activate"
fi

# Check for psutil
python3 -c "import psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing missing dependencies..."
    pip install -r requirements.txt
    if [ -f "requirements-gpu.txt" ]; then
         pip install -r requirements-gpu.txt
    fi
fi

# Launch Dashboard
echo "Initializing Dashboard..."
python3 -m ue5_query.management.gui_dashboard "$@"
