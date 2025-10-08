# Vittcott (local demo)

This repository contains a FastAPI backend and a Streamlit frontend for the Vittcott AI demo.

Important: do NOT commit any `.env` files or secrets. The repository already includes a `.gitignore` entry to ignore `.env` and the backend virtual environment.

Quick start (Windows / PowerShell)

1. Open PowerShell and change to the repository root:

```powershell
cd E:\Vittcott_AI\Vitcott-AI
```

2. Ensure you have a `.env` file with the required keys under `backend/` (example keys: `GEMINI_API_KEY`, any other keys used by your app). Do not commit this file.

3. Create and activate the backend virtual environment and install dependencies (one-time):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

4. Run the demo wrapper (starts backend and Streamlit, opens browser):

```powershell
.\scripts\demo_start.ps1
```

5. Tail logs (two separate PowerShell windows recommended):

```powershell
Get-Content -Path .\logs\backend.log -Wait -Tail 50
Get-Content -Path .\logs\streamlit.log -Wait -Tail 50
```

Quick start (Linux/macOS)

1. From the repo root:

```bash
cd /path/to/Vitcott-AI/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..
# Start uvicorn and streamlit in separate terminals
./scripts/start.sh     # if provided on the project; otherwise run manually
# Example manual commands:
# backend/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
# backend/.venv/bin/python -m streamlit run streamlit_app.py --server.port 8501
```

What I added

- `scripts/demo_start.ps1` — Windows demo wrapper (creates venv if needed, installs, runs supervised start and opens browser).
- `scripts/start_all.ps1` — supervised Windows starter (launches backend and Streamlit and writes logs to `logs/`).
- `backend/scripts/smoke_test.py` — non-destructive smoke test (POST to `/ai/ask`, GET `/api/finance/quote`).
- Small change in `backend/src/config/settings.py` to make `.env` loading tolerant to placement.
- Updated `.gitignore` to ignore `backend/.venv`, `backend/.env`, `backend/src/.env`, and `logs/`.

If `.env` was accidentally committed

If you find a `.env` in the remote repository, do NOT push new commits until you remove the sensitive file from the history. A safe sequence to remove `.env` from the index (local) is:

```bash
git rm --cached path/to/.env
git commit -m "chore: remove .env from repo"
git push origin main
```

If `.env` is already in earlier commits and pushed, you'll need to rewrite history (for example with `git filter-branch` or `git filter-repo`) and then force-push — only do this if you're comfortable rewriting the remote history.

Questions / Next steps

- Want me to push these changes to your GitHub remote now? I will attempt to push, but that may require your git credentials (the push will fail if the environment doesn't have auth). If you'd like, I can prepare the exact git commands for you to run locally or help configure a GitHub PAT for pushing from this environment.

How to demo (PowerShell) — quick coordinated tail and demo

1. Open two PowerShell windows side-by-side.

2. In the first window, start the demo wrapper (this creates the venv if necessary, starts backend + frontend and opens the browser):

```powershell
cd E:\Vittcott_AI\Vitcott-AI
.\scripts\demo_start.ps1
```

3. In the second window, tail both logs concurrently (split the view or use two tabs):

```powershell
Get-Content -Path .\logs\backend.log -Wait -Tail 200
Get-Content -Path .\logs\streamlit.log -Wait -Tail 200
```

This lets you show the app UI while monitoring startup logs for the backend (Gemini initialization) and Streamlit.

# Vittcott

Vittcott is a full-stack experimental investing assistant platform, designed to help beginners learn about stocks, mutual funds, and personal finance with the help of AI.

## Features

- **AI Investing Assistant**: Ask finance questions and get beginner-friendly, actionable advice powered by Google Gemini.
- **Stock & Mutual Fund Data**: Real-time and historical data via FinanceHub API and yfinance fallback.
- **Modern Frontend**: Responsive web UI for interacting with the AI and exploring financial data.
- **Extensible Backend**: Built with FastAPI (Python) and Node.js for future integrations.

## Project Structure

```
backend/    # FastAPI backend (Python) + Node.js entrypoint
frontend/   # Frontend web app (HTML/CSS/JS)
docs/       # Documentation (API, design, usage)
scripts/    # Setup, deployment, and utility scripts
data/       # (Optional) Data files or datasets
```

## Getting Started

### Backend

1. **Install Python dependencies:**
	```sh
	cd backend
	pip install -r requirements.txt
	```

2. **Run the backend server:**
	```sh
	python src/main.py
	```
	- The backend uses FastAPI and serves endpoints for AI and finance data.
	- Configure API keys in environment variables as needed.

### Frontend

1. **Open `frontend/public/index.html` in your browser** (or set up a static server for development).

2. **Customize frontend assets** in `frontend/src/assets/` and pages in `frontend/src/pages/`.

### API Reference

- See `docs/API_REFERENCE.md` for available endpoints and usage examples.

### Design Notes

- See `docs/DESIGN_NOTES.md` for architecture and design decisions.

## Technologies Used

- **Backend**: FastAPI, Uvicorn, yfinance, httpx, google-generativeai
- **Frontend**: HTML, CSS, JavaScript
- **Other**: Node.js (for future backend expansion)

## Contributing

Pull requests and suggestions are welcome! Please see the `docs/` folder for more details.


## Running the App with script.sh

You can run both the Streamlit frontend and FastAPI backend automatically using the provided `script.sh`.

**Steps:**

1. Open a terminal and navigate to the root of the project.
2. Make the script executable (only needed once):
	```sh
	chmod +x script.sh
	```
3. Run the script:
	```sh
	./script.sh
	```
4. **Wait for the script to finish executing.** It will:
	- Set up virtual environments for both frontend and backend
	- Install all required dependencies
	- Start the Streamlit frontend and FastAPI backend automatically

Once both are running, you can access the Streamlit app in your browser (usually at http://localhost:8501).
cd backend && source venv/bin/activate && cd src && python3 main.py