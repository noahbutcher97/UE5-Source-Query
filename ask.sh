#!/bin/bash
# UE5 Source Query - CLI Entry Point (Linux/Mac)

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Please run ./setup.sh or ./launcher.sh first."
    exit 1
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Run query
python3 -m ue5_query.core.hybrid_query "$@"
