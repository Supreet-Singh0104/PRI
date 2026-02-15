#!/bin/bash
# run_app.sh

# Explicitly use the venv python
PYTHON_EXEC="./venv/bin/python"

if [[ ! -f "$PYTHON_EXEC" ]]; then
    echo "⚠️  Virtual environment python not found at $PYTHON_EXEC"
    echo "Using default python: $(which python)"
    PYTHON_EXEC="python"
fi

echo "🚀 Starting Patient Report Intelligence App..."
echo "Using python: $PYTHON_EXEC"

if [[ -f "streamlit_app1.py" ]]; then
    APP_FILE="streamlit_app1.py"
else
    APP_FILE="streamlit_app1.py"
fi

echo "Running $APP_FILE..."
$PYTHON_EXEC -m streamlit run $APP_FILE
