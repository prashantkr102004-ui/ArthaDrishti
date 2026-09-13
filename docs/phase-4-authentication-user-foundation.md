# ArthaDrishti: Phase 4 Authentication & User Foundation

Phase 4 implements the secure user foundation that future financial resources will depend on. It does not implement document upload, transactions, analytics, RAG, LLM features, categorization, or financial logic.

## Implementation Summary

Phase 4 adds:

- `users` table through Alembic.
- SQLAlchemy `User` model.
- Pydantic auth/user schemas.
- Argon2id password hashing.
- JSON registration and login endpoints.
- Bearer JWT access token creation and validation.
- Reusable `get_current_user` FastAPI dependency.
- Protected `/api/v1/users/me` endpoint.
- Backend auth tests with PostgreSQL rollback isolation.
- Minimal frontend register, login, dashboard, and logout flow.

## User Model

MVP fields:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | PostgreSQL UUID | Primary key, default `gen_random_uuid()` in database and `uuid4` in SQLAlchemy |
| `email` | `varchar(320)` | Normalized before storage, unique, indexed |
| `password_hash` | `varchar(255)` | Argon2id hash only; never plaintext |
| `is_active` | boolean | Defaults to true |
| `created_at` | `timestamptz` | Defaults to `now()` |
| `updated_at` | `timestamptz` | Defaults to `now()` |

Deferred profile fields:

- phone
- address
- date of birth
- profile image
- income
- occupation
- financial preferences

These are deferred because Phase 4 only needs identity and ownership. Extra personal fields would increase privacy risk and model churn before the product needs them.

## Email Normalization

Email normalization performs only:

- trim leading/trailing whitespace
- lowercase the full address

It does not remove dots, alter plus addressing, rewrite domains, or perform provider-specific canonicalization. Exotic canonicalization can accidentally merge distinct valid email addresses.

## Password Policy

MVP policy:

- minimum length: 8 characters
- maximum accepted length: 128 characters
- empty passwords rejected

The system does not require uppercase letters, numbers, or symbols. Length-based policies are simpler for users and avoid encouraging predictable substitutions. Password security primarily comes from sufficient length and Argon2id hashing.

## Authentication Strategy

Phase 4 uses Bearer JWT access tokens.

JWT fields:

- `sub`: authenticated user UUID
- `iat`: issued-at timestamp
- `exp`: expiration timestamp

Environment variables:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

The JWT secret is read from environment configuration and is not hardcoded in source files. `backend/.env.example` contains only a placeholder.

Refresh tokens are deferred because the MVP only needs a minimal authenticated session. Token rotation, revocation, and long-lived sessions can be added later.

## Token Storage Decision

The frontend stores the access token in `sessionStorage` for Phase 4 development.

Why this is acceptable for now:

- It is simple for a local development MVP.
- It survives page refresh within the same browser tab/session.
- It is cleared on logout and when the browser session ends.
- It avoids storing the token persistently in `localStorage`.

Risk:

- `sessionStorage` is still readable by JavaScript, so an XSS bug could steal the token.

Before production:

- Prefer HttpOnly, Secure, SameSite cookies or a backend-for-frontend session approach.
- Add CSRF protections if cookie-based auth is used.
- Strengthen Content Security Policy.

## Ownership Rule

Future financial resources must be owned by the authenticated backend user.

Correct pattern:

```text
authenticated request
  -> backend validates token
  -> backend resolves current_user
  -> backend creates/queries resource with current_user.id
```

Incorrect pattern:

```text
frontend sends user_id
  -> backend trusts user_id
  -> resource can be assigned to the wrong user
```

This matters because accounts, documents, transactions, and analytics will contain sensitive financial data. The client must never decide which user owns a resource.

## Migration Created

Migration file:

- `backend/alembic/versions/20260909_0001_create_users_table.py`

It creates:

- PostgreSQL `pgcrypto` extension if missing.
- `users` table.
- UUID primary key with `gen_random_uuid()`.
- unique `email` constraint.
- `ix_users_email` index.
- `password_hash`, `is_active`, `created_at`, and `updated_at`.

Downgrade:

- drops the email index.
- drops the `users` table.

The migration was applied, downgraded to base, then applied again successfully.

## Database Test Isolation

Backend tests use PostgreSQL, not SQLite.

Strategy:

- Create a SQLAlchemy connection per test.
- Open a transaction.
- Override FastAPI's `get_db` dependency to use that session.
- Let endpoints commit normally inside the test.
- Roll back the outer transaction at the end of the test.

This exercises real PostgreSQL behavior while avoiding persistent test users.

## API Error Handling

| Scenario | Status |
| --- | --- |
| Invalid request shape | `422 Unprocessable Entity` |
| Invalid email format | `422 Unprocessable Entity` |
| Weak password | `422 Unprocessable Entity` |
| Duplicate registration | `409 Conflict` |
| Wrong password | `401 Unauthorized` |
| Unknown email | `401 Unauthorized` |
| Inactive account | `403 Forbidden` |
| Missing token | `401 Unauthorized` |
| Malformed token | `401 Unauthorized` |
| Expired token | `401 Unauthorized` |

Unknown email and wrong password share the same message: `Invalid email or password`.

## Authentication Flow Diagrams

### Registration

```text
Frontend register form
  -> POST /api/v1/auth/register
  -> Pydantic validates email/password
  -> email is trimmed and lowercased
  -> service checks for existing user
  -> password is hashed with Argon2id
  -> User row inserted into PostgreSQL
  -> API returns safe UserRead response
```

Simple explanation:

The user submits email and password. The backend validates them, stores only a password hash, and returns public user fields. The password and hash never go back to the browser.

### Login

```text
Frontend login form
  -> POST /api/v1/auth/login
  -> email is trimmed and lowercased
  -> backend loads user by email
  -> password is verified against Argon2id hash
  -> inactive users are rejected
  -> JWT access token is created
  -> client receives Bearer token
```

Simple explanation:

The backend compares the submitted password to the stored hash using Argon2id verification. If valid, it creates a signed token containing the user's ID and expiration time.

### Protected Request

```text
Client request
  -> Authorization: Bearer <token>
  -> FastAPI HTTPBearer dependency
  -> JWT signature and expiry validated
  -> sub claim parsed as user UUID
  -> current user loaded from PostgreSQL
  -> inactive/missing users rejected
  -> protected endpoint receives current_user
```

Simple explanation:

Protected endpoints do not accept a user ID from the browser. They get the user identity from the verified token and database lookup.

## Verification Commands

### 1. Existing Phase 3 Tests Still Pass

Directory: `backend`

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health.py
```

Expected output:

- `3 passed`

Common failures:

- Backend dependencies not installed.
- PostgreSQL not running for `/health/db`.

Diagnosis:

- Run `python -m pip install -e ".[dev]"`.
- Run `docker compose ps` from the repository root.

### 2. PostgreSQL Is Running

Directory: repository root

Command:

```powershell
docker compose ps
```

Expected output:

- `arthadrishti-postgres` is `healthy`.

Common failures:

- Docker Desktop is not running.
- Port `5432` is already in use.

Diagnosis:

- Open Docker Desktop.
- Run `docker compose logs postgres`.

### 3. Run New Alembic Migration

Directory: `backend`

Command:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Expected output:

- `Running upgrade -> 20260909_0001, create users table`

Common failures:

- Wrong `DATABASE_URL`.
- PostgreSQL unavailable.

Diagnosis:

- Check `backend\.env`.
- Check `docker compose ps`.

### 4. Confirm Users Table Exists

Directory: repository root

Command:

```powershell
docker compose exec -T postgres psql -U arthadrishti_dev -d arthadrishti_dev -c "\d users"
```

Expected output:

- `id uuid`
- `email character varying(320)`
- `password_hash character varying(255)`
- unique/indexed email

Common failures:

- Migration not run.
- Wrong database name.

Diagnosis:

- Run `alembic current` from `backend`.

### 5. Start Backend

Directory: `backend`

Command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected output:

- `Uvicorn running on http://127.0.0.1:8000`

Common failures:

- Port already in use.
- Missing JWT secret in `backend\.env`.

Diagnosis:

- Try `--port 8001`.
- Check `backend\.env`.

### 6. Register A User

Directory: any PowerShell window

Command:

```powershell
$body = @{ email = "phase4.manual@example.com"; password = "correct horse battery staple" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -Body $body -ContentType 'application/json'
```

Expected output:

- user `id`
- normalized `email`
- `is_active`
- `created_at`
- no password fields

Common failures:

- `409` if the email already exists.
- `422` for invalid email or password.

Diagnosis:

- Use a fresh email.
- Ensure password length is at least 8.

### 7. Confirm Returned Payload Contains No Password Hash

Directory: any PowerShell window

Command:

```powershell
$registered.PSObject.Properties.Name -contains "password_hash"
```

Expected output:

- `False`

Common failures:

- Response schema accidentally exposes internal model fields.

Diagnosis:

- Check `UserRead`.

### 8. Inspect Database And Confirm Password Is Hashed

Directory: repository root

Command:

```powershell
docker compose exec -T postgres psql -U arthadrishti_dev -d arthadrishti_dev -c "SELECT left(password_hash, 10), password_hash = 'correct horse battery staple' AS is_plaintext FROM users ORDER BY created_at DESC LIMIT 1;"
```

Expected output:

- hash prefix starts with `$argon2id$`
- `is_plaintext` is false

Common failures:

- Wrong hashing configuration.
- Querying the wrong database.

Diagnosis:

- Check `backend/app/core/security.py`.
- Check `DATABASE_URL`.

### 9. Attempt Duplicate Registration

Directory: any PowerShell window

Command:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -Body $body -ContentType 'application/json'
```

Expected output:

- `409 Conflict`

Common failures:

- Duplicate check missing.

Diagnosis:

- Check `get_user_by_email` and unique email constraint.

### 10. Login With Correct Credentials

Directory: any PowerShell window

Command:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -Body $body -ContentType 'application/json'
$login.token_type
$login.access_token.Split(".").Count
```

Expected output:

- `bearer`
- `3`

Common failures:

- Password verification failure.
- Wrong email normalization.

Diagnosis:

- Check the stored email and password hash.

### 11. Login With Incorrect Credentials

Directory: any PowerShell window

Command:

```powershell
$badBody = @{ email = "phase4.manual@example.com"; password = "wrong password" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -Body $badBody -ContentType 'application/json'
```

Expected output:

- `401 Unauthorized`
- safe error message

Common failures:

- Overly specific error messages.

Diagnosis:

- Check login route error handling.

### 12. Call `/users/me` Without Authentication

Directory: any PowerShell window

Command:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/users/me
```

Expected output:

- `401 Unauthorized`

Common failures:

- Missing auth dependency on `/users/me`.

Diagnosis:

- Check `backend/app/api/v1/routes/users.py`.

### 13. Call `/users/me` With Valid Authentication

Directory: any PowerShell window

Command:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/users/me -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

Expected output:

- safe current user response
- no `password_hash`

Common failures:

- Wrong `JWT_SECRET_KEY`.
- Expired or malformed token.

Diagnosis:

- Re-login and retry.

### 14. Run Authentication Backend Tests

Directory: `backend`

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_auth.py
```

Expected output:

- `13 passed`

Common failures:

- Migration not applied.
- PostgreSQL not running.

Diagnosis:

- Run `alembic upgrade head`.

### 15. Start Frontend

Directory: `frontend`

Command:

```powershell
npm run dev
```

Expected output:

- Next.js running on `http://localhost:3000`

Common failures:

- Dependencies missing.

Diagnosis:

- Run `npm install`.

### 16. Register Using Frontend

Directory: browser

Command:

```text
Open http://localhost:3000/register
```

Expected output:

- registration form
- success message after valid submit

Common failures:

- Backend unavailable.
- CORS misconfigured.

Diagnosis:

- Check `NEXT_PUBLIC_API_BASE_URL`.
- Check `FRONTEND_ORIGIN`.

### 17. Login Using Frontend

Directory: browser

Command:

```text
Open http://localhost:3000/login
```

Expected output:

- valid credentials redirect to `/dashboard`

Common failures:

- Token not stored.
- Wrong credentials.

Diagnosis:

- Check browser console and backend logs.

### 18. Visit Protected Dashboard

Directory: browser

Command:

```text
Open http://localhost:3000/dashboard
```

Expected output:

- `Welcome to ArthaDrishti`
- logged-in email

Common failures:

- `/users/me` request fails.

Diagnosis:

- Check `Authorization` header and backend `/api/v1/users/me`.

### 19. Refresh Protected Dashboard

Directory: browser

Command:

```text
Refresh http://localhost:3000/dashboard
```

Expected output:

- dashboard remains visible while browser session token exists

Common failures:

- Token storage cleared.

Diagnosis:

- Re-login.

### 20. Logout

Directory: browser

Command:

```text
Click Logout
```

Expected output:

- redirected to login page

Common failures:

- Token not cleared.

Diagnosis:

- Check `frontend/src/lib/auth.ts`.

### 21. Verify Protected Page Is No Longer Accessible

Directory: browser

Command:

```text
Open http://localhost:3000/dashboard
```

Expected output:

- redirected to `/login`

Common failures:

- Missing client-side auth check.

Diagnosis:

- Check `frontend/src/app/dashboard/page.tsx`.

### 22. Run Frontend Lint/Build

Directory: `frontend`

Command:

```powershell
npm run lint
npm run build
```

Expected output:

- lint passes
- production build passes

Common failures:

- TypeScript errors.
- React hook lint errors.

Diagnosis:

- Fix reported file and line.

### 23. Run Complete Backend Test Suite Again

Directory: `backend`

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected output:

- all tests pass

Common failures:

- PostgreSQL not running.
- Migration not applied.

Diagnosis:

- Run `docker compose ps`.
- Run `alembic current`.

## Created/Changed File Summary

| File path | Status | Purpose | Important implementation details |
| --- | --- | --- | --- |
| `README.md` | Modified | Main setup guide | Updated current phase and auth endpoints |
| `backend/.env.example` | Modified | Backend env template | Adds JWT env vars with placeholder secret |
| `backend/.env` | Modified local ignored file | Local backend config | Adds generated local JWT secret |
| `backend/pyproject.toml` | Modified | Backend dependencies | Adds `argon2-cffi`, `PyJWT`, `email-validator` |
| `backend/alembic/env.py` | Modified | Alembic model discovery | Imports `app.models` so metadata sees models |
| `backend/alembic/versions/20260909_0001_create_users_table.py` | New | Users migration | Creates reversible `users` table |
| `backend/app/core/config.py` | Modified | App settings | Adds JWT settings |
| `backend/app/core/security.py` | New | Security utilities | Argon2id hashing and JWT create/decode |
| `backend/app/models/user.py` | New | User SQLAlchemy model | UUID PK, normalized unique email, hash, active flag, timestamps |
| `backend/app/models/__init__.py` | Modified | Model exports | Exposes `User` |
| `backend/app/schemas/user.py` | New | User schemas | `UserCreate`, `UserRead`, email normalization |
| `backend/app/schemas/auth.py` | New | Auth schemas | `LoginRequest`, `TokenResponse` |
| `backend/app/schemas/__init__.py` | Modified | Schema exports | Exposes auth/user schemas |
| `backend/app/services/users.py` | New | User service logic | User lookup, creation, authentication |
| `backend/app/api/deps.py` | New | API dependencies | Bearer auth and reusable `get_current_user` |
| `backend/app/api/v1/routes/__init__.py` | New | Route package marker | Holds v1 route modules |
| `backend/app/api/v1/routes/auth.py` | New | Auth routes | Register/login endpoints |
| `backend/app/api/v1/routes/users.py` | New | User routes | Protected `/users/me` endpoint |
| `backend/app/api/v1/router.py` | Modified | API router | Includes auth and users route modules |
| `backend/tests/conftest.py` | New | Test fixtures | PostgreSQL transaction rollback and DB override |
| `backend/tests/test_auth.py` | New | Auth behavior tests | Registration, login, token, current-user behavior |
| `backend/tests/test_health.py` | Modified | Health tests | Uses local TestClient context |
| `frontend/src/lib/auth.ts` | New | Client token helpers | Uses `sessionStorage` for Phase 4 token |
| `frontend/src/lib/api.ts` | New | API client helpers | Register, login, current-user calls |
| `frontend/src/app/page.tsx` | Modified | Home page | Adds register/login links |
| `frontend/src/app/register/page.tsx` | New | Register page | Email/password form, loading, success/error state |
| `frontend/src/app/login/page.tsx` | New | Login page | Email/password form, token storage, redirect |
| `frontend/src/app/dashboard/page.tsx` | New | Protected page | Verifies `/users/me`, shows email, logout |
| `frontend/tsconfig.json` | Modified | TS config | Adds `@/*` path alias |
| `docs/phase-4-authentication-user-foundation.md` | New | Phase 4 report | Auth design, commands, flow diagrams, checklist |

## Relevant Phase 4 Project Tree

Generated folders such as `.venv`, `node_modules`, `.next`, `__pycache__`, and caches are omitted.

Authentication-related files are marked with `[auth]`.

```text
.
|-- README.md
|-- docker-compose.yml
|-- backend
|   |-- .env.example
|   |-- alembic.ini
|   |-- pyproject.toml
|   |-- alembic
|   |   |-- env.py
|   |   |-- script.py.mako
|   |   `-- versions
|   |       `-- 20260909_0001_create_users_table.py [auth]
|   |-- app
|   |   |-- main.py
|   |   |-- api
|   |   |   |-- deps.py [auth]
|   |   |   `-- v1
|   |   |       |-- router.py
|   |   |       `-- routes
|   |   |           |-- __init__.py
|   |   |           |-- auth.py [auth]
|   |   |           `-- users.py [auth]
|   |   |-- core
|   |   |   |-- config.py
|   |   |   `-- security.py [auth]
|   |   |-- db
|   |   |   |-- base.py
|   |   |   |-- health.py
|   |   |   `-- session.py
|   |   |-- models
|   |   |   |-- __init__.py
|   |   |   `-- user.py [auth]
|   |   |-- schemas
|   |   |   |-- __init__.py
|   |   |   |-- auth.py [auth]
|   |   |   `-- user.py [auth]
|   |   `-- services
|   |       |-- __init__.py
|   |       `-- users.py [auth]
|   `-- tests
|       |-- conftest.py
|       |-- test_auth.py [auth]
|       `-- test_health.py
|-- frontend
|   |-- .env.example
|   |-- package.json
|   |-- tsconfig.json
|   `-- src
|       |-- app
|       |   |-- page.tsx
|       |   |-- register
|       |   |   `-- page.tsx [auth]
|       |   |-- login
|       |   |   `-- page.tsx [auth]
|       |   `-- dashboard
|       |       `-- page.tsx [auth]
|       `-- lib
|           |-- api.ts [auth]
|           `-- auth.ts [auth]
`-- docs
    |-- phase-1-project-planning-requirements.md
    |-- phase-2-system-architecture-database-design.md
    |-- phase-3-development-environment-project-setup.md
    `-- phase-4-authentication-user-foundation.md
```

## Security Checks

| Check | Result |
| --- | --- |
| Plaintext passwords are never stored | Passed |
| Password hashes use Argon2id | Passed |
| Password hashes are never returned through API | Passed |
| JWT secret is not in committed example files | Passed |
| `.env` remains ignored | Passed |
| Wrong password and unknown email use same login error | Passed |
| Protected endpoint rejects anonymous users | Passed |
| Expired tokens fail | Passed |
| Malformed tokens fail | Passed |
| Inactive users cannot authenticate | Passed |
| Logs do not print passwords or tokens | Passed |

## Final Verification Results

| Verification | Result |
| --- | --- |
| Existing Phase 3 tests | Passed: 3 tests |
| PostgreSQL running | Passed: container healthy |
| Alembic upgrade | Passed |
| Users table exists | Passed |
| Alembic downgrade | Passed |
| Alembic upgrade again | Passed |
| Backend starts | Passed |
| Register API | Passed |
| Safe registration response | Passed |
| DB password hash inspection | Passed: `$argon2id$`, not plaintext |
| Duplicate registration | Passed: `409` |
| Correct login | Passed |
| Incorrect login | Passed: `401` |
| `/users/me` without auth | Passed: `401` |
| `/users/me` with auth | Passed |
| OpenAPI auth docs | Passed: routes and `HTTPBearer` present |
| Full backend tests | Passed: 16 tests |
| Frontend register | Passed |
| Frontend login | Passed |
| Protected dashboard | Passed |
| Dashboard refresh | Passed |
| Logout | Passed |
| Protected page after logout | Passed: redirected to login |
| Frontend lint | Passed |
| Frontend build | Passed |

## Phase 4 Completion Checklist

- [x] Existing Phase 3 foundation reviewed.
- [x] Existing backend structure preserved.
- [x] Existing frontend structure preserved.
- [x] PostgreSQL connection confirmed.
- [x] FastAPI API prefix confirmed as `/api/v1`.
- [x] Users table exists through Alembic.
- [x] Alembic migration upgrade works.
- [x] Alembic migration downgrade works.
- [x] Alembic migration upgrade works again.
- [x] User SQLAlchemy model created.
- [x] Email is normalized before storage.
- [x] Email is unique and indexed.
- [x] Passwords are securely hashed with Argon2id.
- [x] Plaintext passwords are not stored.
- [x] Password hash is not returned through API.
- [x] Password policy is implemented.
- [x] Registration endpoint works.
- [x] Duplicate registration is handled.
- [x] Login endpoint works.
- [x] Wrong password is rejected safely.
- [x] Unknown email is rejected safely.
- [x] Inactive user login is rejected.
- [x] JWT access token works.
- [x] JWT secret is environment-based.
- [x] Missing token is rejected.
- [x] Malformed token is rejected.
- [x] Expired token is rejected.
- [x] Current-user dependency works.
- [x] Protected backend route works.
- [x] `/api/v1/users/me` works with authentication.
- [x] `/api/v1/users/me` rejects anonymous users.
- [x] Ownership rule is documented for future resources.
- [x] Pydantic request and response schemas are separated from SQLAlchemy models.
- [x] Backend tests pass.
- [x] Previous tests still pass.
- [x] Tests use PostgreSQL with rollback isolation.
- [x] Authentication endpoints appear in OpenAPI docs.
- [x] Frontend registration page works.
- [x] Frontend login page works.
- [x] Protected frontend dashboard works.
- [x] Dashboard refresh behavior verified.
- [x] Logout works.
- [x] Protected page is inaccessible after logout.
- [x] Frontend lint passes.
- [x] Frontend build passes.
- [x] No document upload implemented.
- [x] No transaction extraction implemented.
- [x] No analytics implemented.
- [x] No categorization implemented.
- [x] No RAG implemented.
- [x] No LLM features implemented.
- [x] No financial logic implemented.
- [x] Phase 5 not started.
