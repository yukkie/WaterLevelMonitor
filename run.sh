#!/bin/bash

# Get the command from the first argument
CMD=$1

# Define path to venv python
PYTHON="venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python"
fi

case $CMD in
    "streamlit")
        echo "Starting Streamlit..."
        $PYTHON -m streamlit run src/app.py
        ;;
    "test")
        echo "Running tests..."
        $PYTHON -m pytest
        ;;
    *)
        echo "Starting Main..."
        $PYTHON -m src.main
        ;;
esac
