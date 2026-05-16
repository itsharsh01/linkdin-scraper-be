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

From the **backend** directory (`main.py` at project root; packages `api/`, `core/`, `db/`, etc. — no `src/` folder):

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python main.py
```

API docs: http://127.0.0.1:8000/docs

## Frontend

Runs separately. See **linkedIn-Scrapper-frontend** and set `API_BASE_URL` to this server.
