#!/bin/bash
# Script to set up and run both Streamlit frontend and FastAPI backend for Vittcott
# Run this from the root directory: ./script.sh

set -e

# --- Streamlit Frontend Setup ---
echo "[1/5] Creating Python virtual environment for Streamlit frontend..."
python3 -m venv venv
source venv/bin/activate

echo "[2/5] Installing requirements for frontend..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/5] Running Streamlit frontend (in background)..."
streamlit run streamlit_app.py &
STREAMLIT_PID=$!
echo "Streamlit running with PID $STREAMLIT_PID"

# --- Backend Setup ---
echo "[4/5] Setting up backend virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

cd src

echo "[5/5] Installing requirements for backend..."
pip install --upgrade pip
pip install -r ../../requirements.txt

echo "Running FastAPI backend..."
python3 main.py

# Cleanup: kill Streamlit when backend exits
kill $STREAMLIT_PID
