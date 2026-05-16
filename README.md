# LinkedIn Scrapper — Backend

FastAPI API: Apify scrape, LLM job matching, outreach email, scheduled jobs.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # fill in secrets
```

## Run

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Frontend

Runs separately. See **linkedIn-Scrapper-frontend** and set `API_BASE_URL` to this server.
