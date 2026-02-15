# Patient Report Intelligence

This repository contains the intelligence layer for analyzing patient reports.

## Structure

- `src/`: Source code modules
- `data/`: Data storage (SQLite, etc.)
- `requirements.txt`: Python dependencies

## Running the App

To avoid environment issues, always run the app using the helper script:

```bash
./run_app.sh
```

Or manually:

```bash
# Ensure venv is active
source venv/bin/activate
# Run as module
python -m streamlit run streamlit_app1.py
```
