
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
