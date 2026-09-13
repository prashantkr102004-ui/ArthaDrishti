# Setup Guide

## Prerequisites

- Git
- Docker Desktop with Linux containers
- Node.js 22 or compatible
- Python 3.12 recommended

The project was developed on Windows, so PowerShell commands are shown.

## Clone And Environment

```powershell
# Directory: wherever you keep code
git clone <your-repo-url> ArthaDrishti
cd ArthaDrishti

# Directory: repository root
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

Edit secrets in `.env` and `backend\.env`. Do not commit local env files.

## Start PostgreSQL

```powershell
# Directory: repository root
docker compose up -d postgres
docker compose ps
```

Expected: `arthadrishti-postgres` is `healthy`.

## Backend Native Setup

```powershell
# Directory: backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
```

## Frontend Native Setup

```powershell
# Directory: frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Full Docker Demo

```powershell
# Directory: repository root
docker compose up -d postgres
docker compose run --rm backend python -m alembic upgrade head
docker compose up --build -d backend frontend
docker compose run --rm backend python -m app.scripts.seed_demo
```

Open:

- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

## Demo Seed

```powershell
# Directory: backend
.\.venv\Scripts\python.exe -m app.scripts.seed_demo
```

This creates a demo user, synthetic financial history, budgets/goals, and two synthetic PDFs under ignored local demo storage. Native PowerShell runs write to the repository's `local_uploads/demo`; containerized runs write to `/app/local_uploads/demo` inside the backend container.

Default demo credentials are development-only:

- email: `demo@arthadrishti.local`
- password: `demo password 123`

Override with:

```powershell
$env:ARTHADRISHTI_DEMO_EMAIL="your-demo@example.com"
$env:ARTHADRISHTI_DEMO_PASSWORD="choose a demo password"
.\.venv\Scripts\python.exe -m app.scripts.seed_demo
```
