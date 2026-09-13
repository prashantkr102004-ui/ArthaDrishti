# ArthaDrishti

ArthaDrishti is a smart personal finance assistant built as a serious final-year and portfolio project. It helps a user upload financial PDFs, extract statement transactions, categorize spending, view deterministic analytics, search document text, and ask grounded financial questions.

The important design rule is simple: financial numbers are calculated by the backend and PostgreSQL, not guessed by an LLM. AI is used only around the edges for language understanding, safe tool routing, and explanation of verified results.

## What Works Now

- User registration and login with Argon2id password hashing and Bearer JWT auth
- Private PDF upload for bank and credit-card statements
- Text-based PDF parsing for supported synthetic/generic statement layouts
- Canonical transaction storage in PostgreSQL with Decimal/NUMERIC money handling
- Deterministic merchant normalization and category assignment
- User category overrides
- Financial analytics APIs for summary, categories, monthly trends, merchants, and comparisons
- Responsive dashboard, documents, transactions, assistant, and insights pages
- Natural-language Q&A through approved backend tools
- RAG document search over indexed financial PDFs with source references
- Recurring payment, subscription, budget, goal, forecast, and anomaly foundations
- Security hardening basics such as request IDs, safe errors, CORS config, upload validation, and rate limiting

This is not a production banking app yet. It does not connect to real banks, move money, trade investments, or give regulated investment advice.

## Tech Stack

Backend:

- Python 3.12+
- FastAPI
- Pydantic Settings
- SQLAlchemy
- Alembic
- PostgreSQL 16 with pgvector
- PyMuPDF for text-based PDF extraction
- pytest and HTTPX

Frontend:

- Next.js
- React
- TypeScript
- Tailwind CSS

Infrastructure:

- Docker
- Docker Compose

## Project Structure

```text
backend/            FastAPI app, database models, services, tests, migrations
frontend/           Next.js app
docs/               Architecture, phase reports, testing, security, viva notes
docker-compose.yml  Local full-stack development setup
.env.example        Root environment template for Docker Compose
```

Generated folders such as `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, `.venv`, and local uploaded files are intentionally not committed.

## Quick Start With Docker

From the project root:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec backend python -m alembic upgrade head
```

Open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

To seed demo data:

```powershell
docker compose exec backend python -m app.scripts.seed_demo
```

The default demo values are in `.env.example`. For real local use, change passwords and secrets in your private `.env`.

## Local Development Without Full Docker

PostgreSQL can still run in Docker:

```powershell
docker compose up -d postgres
```

Backend:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Testing

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

If `node_modules` was removed during cleanup, run `npm install` before frontend lint or build.

## Supported Documents

The current parser supports text-based PDF statements for the project's synthetic/generic layouts. A supported transaction table contains fields like:

- Date
- Description
- Debit
- Credit
- Balance

OCR is not part of the normal pipeline yet. Scanned/image-only PDFs should fail safely instead of pretending that transactions were extracted.

Uploaded financial files are stored privately. They are not served from `frontend/public` and should never be committed to Git.

## AI Boundary

ArthaDrishti has two different question-answer paths:

- Structured financial questions use backend analytics tools over PostgreSQL transactions.
- Document-text questions use RAG over indexed PDF text chunks.

The LLM does not receive database credentials, does not run SQL, and does not decide which user owns data. The authenticated backend user is always the ownership source.

Examples:

- "How much did I spend on food last month?" uses analytics.
- "What late-payment fee is mentioned in this statement?" uses document search.
- "Why were my expenses higher this month?" uses backend period comparison and category deltas.

## Security Notes

- `.env` files are ignored and must not be committed.
- JWT secrets and AI provider keys must come from environment variables.
- Passwords are hashed with Argon2id.
- Financial amounts use Decimal in Python and NUMERIC in PostgreSQL.
- Uploaded PDFs are treated as untrusted input.
- RAG retrieval is filtered by authenticated user at the database layer.
- The assistant should explain verified facts, not invent numbers.

Before public deployment, the project still needs production secret management, HTTPS, stronger rate limiting, backup/restore testing, and a full deployment review.

## Useful Docs

- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Database Schema](docs/database-schema.md)
- [AI Architecture](docs/ai-architecture.md)
- [Security Overview](docs/security.md)
- [Setup Guide](docs/setup-guide.md)
- [Testing Guide](docs/testing.md)
- [Demo Script](docs/demo-script.md)
- [Viva Guide](docs/viva-guide.md)
- [Project Summary](docs/project-summary.md)

## Known Limitations

- No real bank integration
- No OCR for scanned statements
- No autonomous financial actions
- No investment trading or regulated advisory workflow
- Parser coverage is intentionally limited to safe test/demo formats
- External AI behavior is bounded by tools, but production use still needs provider, privacy, and cost controls

