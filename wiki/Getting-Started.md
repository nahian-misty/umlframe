# Getting Started

## Prerequisites

- Python 3.11+
- Node.js 20+
- Tesseract OCR (`sudo apt install tesseract-ocr` or `brew install tesseract`). Only the image pipelines need it.

## Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```

- API: <http://localhost:8000>, interactive docs at `/docs`.
- Tables (`users`, `projects`) are created on startup. Older SQLite files get missing columns added automatically.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000 (port is fixed)
```

## Configuration

Read from `.env` at the repo root.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | MySQL URL if unset; `.env.example` uses `sqlite:///./umlframe.db` | Any SQLAlchemy URL |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | Set a strong value for anything shared |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend only |

## First run

1. Open <http://localhost:3000> and choose **Get Started Free**.
2. Register (username, email, password of 8+ characters).
3. On the dashboard choose **New Project** and pick a diagram type. The type cannot be changed later.
4. Draw, then use the tabs to generate code or reverse-engineer.

## Demos without the UI

```bash
PYTHONPATH=. python3 scripts/e2e_demo.py            # image → JSON → code
PYTHONPATH=. python3 scripts/e2e_activity_demo.py   # activity image → structured code
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `TesseractNotFoundError` | Install Tesseract and make sure `tesseract` is on `PATH` |
| Login redirects back to `/login` | The token expired; log in again |
| Browser CORS error | Add the frontend origin to `CORS_ORIGINS` |
| Cannot connect to MySQL | `DATABASE_URL` is unset; copy `.env.example` to `.env` |
