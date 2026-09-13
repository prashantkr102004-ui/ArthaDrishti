# Testing Guide

## Backend Tests

```powershell
# Directory: repository root
docker compose up -d postgres

# Directory: backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -q
```

Current final run: `111 passed, 2 warnings`.

## Focused Backend Checks

```powershell
# Directory: backend
.\.venv\Scripts\python.exe -m pytest tests\test_auth.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_documents.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_transactions.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_rag.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py -q
```

## Frontend

```powershell
# Directory: frontend
npm run lint
npm run build
```

No dedicated frontend unit-test runner is currently configured. Frontend validation is lint/build plus manual demo flows.

## Dependency Audits

```powershell
# Directory: frontend
npm audit --audit-level=moderate

# Directory: backend
.\.venv\Scripts\python.exe -m pip install pip-audit
.\.venv\Scripts\python.exe -m pip_audit --cache-dir .pip-audit-cache
```

Final audit results:

- Node: `found 0 vulnerabilities`.
- Python: no known vulnerabilities after upgrading local virtualenv `pip`; local package skipped because it is not published on PyPI.

## Security Scans

Recommended source scan:

```powershell
# Directory: repository root
rg -n --hidden --glob '!frontend/node_modules/**' --glob '!backend/.venv/**' --glob '!frontend/.next/**' --glob '!local_uploads/**' "sk-[A-Za-z0-9]|AKIA|PRIVATE KEY|JWT_SECRET_KEY="
```

Review matches manually. Placeholders in `.env.example` are expected.
