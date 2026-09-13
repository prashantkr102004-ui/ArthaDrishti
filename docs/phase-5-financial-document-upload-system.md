# ArthaDrishti: Phase 5 Financial Document Upload System

Phase 5 implements the secure document-ingestion foundation for financial PDFs. It does not parse PDFs into transactions, perform OCR, create transaction tables, categorize spending, calculate analytics, use embeddings, use RAG, call LLMs, or implement financial logic.

## Implementation Summary

Phase 5 adds:

- `documents` table through Alembic.
- SQLAlchemy `Document` model.
- Pydantic document schemas and enums.
- Authenticated document upload/list/detail/delete API.
- PDF-only upload validation.
- Configurable upload size limit.
- SHA-256 file hashing.
- Per-user exact duplicate detection.
- Private local filesystem storage.
- Storage service boundary for later object-storage migration.
- Minimal protected frontend Documents page.
- Backend tests for upload, listing, detail, deletion, security, and user isolation.

## Financial Account Decision

Phase 5 does not create `financial_accounts`.

Reason:

- Phase 2 allowed documents to eventually be associated with accounts, but Phase 5 only needs secure ingestion and user ownership.
- There is no account creation/management workflow yet.
- Accepting `account_id` before account ownership exists would add security checks and UI complexity without helping upload verification.

Better Phase 5 design:

- Documents belong directly to authenticated users through `documents.user_id`.
- `account_id` can be added later when the accounts phase introduces account ownership and account selection.

## Documents Table

Migration:

- `backend/alembic/versions/20260909_0002_create_documents_table.py`

MVP fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Owner, foreign key to `users.id` |
| `document_type` | varchar(32) | `bank_statement` or `credit_card_statement` |
| `original_filename` | varchar(255) | Safe metadata only |
| `storage_backend` | varchar(32) | `local` for Phase 5 |
| `storage_key` | varchar(255) | Server-generated private storage reference |
| `mime_type` | varchar(100) | Accepted MIME type |
| `file_size_bytes` | integer | File size |
| `sha256_hash` | varchar(64) | Integrity and duplicate detection |
| `processing_status` | varchar(32) | Current processing state |
| `processing_error` | text nullable | Safe processing error summary for later phases |
| `uploaded_at` | timestamptz | Upload timestamp |
| `created_at` | timestamptz | Record creation timestamp |
| `updated_at` | timestamptz | Record update timestamp |

Important constraints and indexes:

- foreign key `documents.user_id -> users.id` with cascade delete
- unique `(user_id, sha256_hash)` for per-user duplicate detection
- check constraint for supported document types
- check constraint for supported processing statuses
- check constraint for positive file size
- indexes for user listing, status filtering, type filtering, and newest-first listing

## Status Model

Statuses:

- `ready_for_processing`
- `processing`
- `completed`
- `failed`

Phase 5 sets successful uploads to `ready_for_processing` because parsing does not exist yet. This avoids pretending a document is fully processed while still giving Phase 6 a clear queue-ready state.

Expected transitions:

```text
upload accepted
  -> ready_for_processing
  -> processing
  -> completed

processing failure
  -> failed
```

## Upload Flow For Viva

```text
User
  |
  v
Authenticated Frontend
  |
  v
POST /api/v1/documents
  |
  v
Current User Dependency
  |
  v
File Validation
  |
  v
SHA-256
  |
  v
Duplicate Check
  |
  v
Safe Storage Key
  |
  v
Private File Storage
  |
  v
Document Metadata -> PostgreSQL
  |
  v
Safe Metadata Response
```

Simple explanation:

The frontend sends a PDF and document type. The backend first resolves the authenticated user from the Bearer token, so the client never supplies ownership. The backend validates the file, hashes it, rejects exact duplicates for that user, generates a safe UUID-based storage key, stores the file privately, writes metadata to PostgreSQL, and returns only safe metadata.

## API Surface

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/documents` | required | Upload a PDF statement |
| `GET` | `/api/v1/documents` | required | List current user's documents |
| `GET` | `/api/v1/documents/{document_id}` | required | Retrieve owned document metadata |
| `DELETE` | `/api/v1/documents/{document_id}` | required | Delete owned document metadata and file |

The API does not expose download/viewing yet. Secure streaming can be added later if needed.

## Validation Rules

Accepted document types:

- `bank_statement`
- `credit_card_statement`

Accepted file type:

- PDF only

Backend validation:

- extension must be `.pdf`
- declared MIME type must be `application/pdf`
- first bytes must begin with `%PDF-`
- file must be non-empty
- file size must be within `MAX_UPLOAD_SIZE_MB`

Boundary:

- Phase 5 rejects obvious non-PDFs and fake renamed files.
- Deep PDF structural validation waits for Phase 6 parsing.

## Duplicate Policy

Exact duplicates are rejected per user with `409 Conflict`.

Duplicate key:

```text
current_user.id + SHA-256(file bytes)
```

This handles duplicate uploads of the same file without attempting transaction-level deduplication, which belongs in a later transaction extraction phase.

## Storage Design

Development:

- local filesystem under `backend/storage/documents`
- configurable via `DOCUMENT_STORAGE_PATH`
- ignored by Git
- not served by frontend/public

Production later:

- S3-compatible object storage
- keep the same metadata/storage-key model
- replace the storage service implementation without rewriting routes

Atomicity strategy:

- Validate file before writing anything.
- Save file before inserting metadata.
- If metadata insert fails, remove the saved file.
- If delete is requested, delete metadata for the owner and then delete the stored file; a missing physical file is handled safely.

## Security And Logging

Security rules:

- All document endpoints require the Phase 4 current-user dependency.
- The client never sends `user_id`.
- Non-owned documents return `404` to avoid resource enumeration.
- Original filename is metadata only.
- Storage key is generated by the backend.
- Storage service verifies resolved paths stay inside the configured root.
- API responses do not include internal paths, storage roots, or hashes.

Logging policy:

- Allowed: document ID, upload success/failure, processing status, user UUID when useful.
- Avoid: PDF contents, extracted financial text, account numbers, passwords, tokens, storage root paths, secrets.

## Verification Commands

| Step | Directory | Command | Expected success | Common failure / diagnosis |
| --- | --- | --- | --- | --- |
| Existing tests | `backend` | `.\.venv\Scripts\python.exe -m pytest` | all tests pass | PostgreSQL down; run `docker compose ps` |
| PostgreSQL health | repository root | `docker compose ps` | `arthadrishti-postgres` healthy | Docker Desktop stopped; start Docker Desktop |
| Apply migrations | `backend` | `.\.venv\Scripts\python.exe -m alembic upgrade head` | current revision reaches `20260909_0002` | wrong `DATABASE_URL`; check `backend\.env` |
| Verify table | repository root | `docker exec ... psql -c "\d documents"` | documents columns, constraints, and indexes visible | migration not applied |
| Start backend | `backend` | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` | Uvicorn running | port in use or missing env |
| Register/login | any | `Invoke-RestMethod` to auth endpoints | safe user response and Bearer token | duplicate email or invalid password |
| Valid PDF upload | any | `curl.exe -F document_type=bank_statement -F file=@...;type=application/pdf` | `201 Created` metadata response | MIME missing/wrong; use explicit `type=application/pdf` |
| Fake PDF upload | any | upload renamed non-PDF | `415 Unsupported Media Type` | backend validation missing |
| Oversized upload | any | upload above limit | `413 Content Too Large` | `MAX_UPLOAD_SIZE_MB` misconfigured |
| Duplicate upload | any | upload same file twice as same user | `409 Conflict` | duplicate constraint/check missing |
| List documents | any | `GET /api/v1/documents` | current user's documents only | missing auth header |
| Detail metadata | any | `GET /api/v1/documents/{id}` | owned metadata only | wrong user returns `404` |
| Delete document | frontend/API | click Delete or `DELETE /api/v1/documents/{id}` | row and file removed | storage path mismatch |
| Frontend page | browser | open `/documents` after login | upload form and list render | backend/CORS/token issue |
| Frontend lint | `frontend` | `npm run lint` | no warnings/errors | React hook dependency or TS issue |
| Frontend build | `frontend` | `npm run build` | production build succeeds | TypeScript/build error |

## Browser Verification Note

The in-app browser file chooser on this Windows workspace displayed the selected filename but exposed an empty `FileList`, so direct file-picker upload could not be completed through that automation surface. The backend upload was verified with explicit multipart HTTP, and the live frontend Documents page was verified to render the uploaded document and delete it through the UI. A normal desktop browser should use the same frontend code path with an actual `FileList`.

## Created/Changed File Summary

| File path | Status | Purpose | Important implementation details |
| --- | --- | --- | --- |
| `README.md` | Modified | Main setup guide | Updated to Phase 5, document upload behavior, storage, security notes, troubleshooting |
| `.gitignore` | Modified | Ignore local/generated files | Excludes `backend/storage/` and test temp output |
| `backend/.env.example` | Modified | Backend env template | Adds document storage path, upload size limit, allowed MIME types |
| `backend/.env` | Modified local ignored file | Local backend config | Adds Phase 5 document settings |
| `backend/pyproject.toml` | Modified | Dependencies and pytest config | Adds `python-multipart`; keeps pytest temp output under project temp |
| `backend/alembic/versions/20260909_0002_create_documents_table.py` | New | Documents migration | Creates reversible `documents` table, constraints, indexes, user FK |
| `backend/app/core/config.py` | Modified | App settings | Adds document upload/storage configuration helpers |
| `backend/app/models/document.py` | New | Document SQLAlchemy model | User-owned metadata, safe storage key, SHA-256 hash, processing status |
| `backend/app/models/__init__.py` | Modified | Model discovery | Exposes `Document` for Alembic metadata |
| `backend/app/schemas/document.py` | New | Document schemas | Document type/status enums and safe response models |
| `backend/app/schemas/__init__.py` | Modified | Schema exports | Exposes document schemas |
| `backend/app/services/document_storage.py` | New | Storage service | Private local save/delete/exists with path traversal protection |
| `backend/app/services/documents.py` | New | Document service logic | Validation, hashing, duplicate check, owner-scoped list/detail/delete |
| `backend/app/api/v1/routes/documents.py` | New | Document API routes | Authenticated multipart upload and metadata endpoints |
| `backend/app/api/v1/router.py` | Modified | API router | Includes document routes under `/api/v1/documents` |
| `backend/tests/conftest.py` | Modified | Test isolation | Uses per-test temporary document storage |
| `backend/tests/test_documents.py` | New | Phase 5 tests | Upload/list/detail/delete/security/user-isolation tests |
| `frontend/src/lib/api.ts` | Modified | Frontend API client | Adds document list/upload/delete functions and types |
| `frontend/src/app/dashboard/page.tsx` | Modified | Protected navigation | Adds Documents link |
| `frontend/src/app/documents/page.tsx` | New | Documents UI | Protected upload form, validation messages, list, delete action |
| `docs/phase-5-financial-document-upload-system.md` | New | Phase 5 report | Design decisions, flow, file table, tree, verification checklist |

## Relevant Phase 5 Project Tree

Generated folders such as `.venv`, `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, `.pytest_tmp`, egg-info, and actual uploaded PDFs are omitted.

Authentication-related files are marked `[auth]`; document-related files are marked `[documents]`.

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
|   |   `-- versions
|   |       |-- 20260909_0001_create_users_table.py [auth]
|   |       `-- 20260909_0002_create_documents_table.py [documents]
|   |-- app
|   |   |-- main.py
|   |   |-- api
|   |   |   |-- deps.py [auth]
|   |   |   `-- v1
|   |   |       |-- router.py
|   |   |       `-- routes
|   |   |           |-- auth.py [auth]
|   |   |           |-- documents.py [documents]
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
|   |   |   |-- document.py [documents]
|   |   |   `-- user.py [auth]
|   |   |-- schemas
|   |   |   |-- __init__.py
|   |   |   |-- auth.py [auth]
|   |   |   |-- document.py [documents]
|   |   |   `-- user.py [auth]
|   |   `-- services
|   |       |-- document_storage.py [documents]
|   |       |-- documents.py [documents]
|   |       `-- users.py [auth]
|   `-- tests
|       |-- conftest.py
|       |-- test_auth.py [auth]
|       |-- test_documents.py [documents]
|       `-- test_health.py
|-- frontend
|   |-- .env.example
|   |-- package.json
|   `-- src
|       |-- app
|       |   |-- page.tsx
|       |   |-- dashboard
|       |   |   `-- page.tsx [auth/documents nav]
|       |   |-- documents
|       |   |   `-- page.tsx [documents]
|       |   |-- login
|       |   |   `-- page.tsx [auth]
|       |   `-- register
|       |       `-- page.tsx [auth]
|       `-- lib
|           |-- api.ts [auth/documents]
|           `-- auth.ts [auth]
`-- docs
    |-- phase-1-project-planning-requirements.md
    |-- phase-2-system-architecture-database-design.md
    |-- phase-3-development-environment-project-setup.md
    |-- phase-4-authentication-user-foundation.md
    `-- phase-5-financial-document-upload-system.md
```

## Final Verification Results

| Verification | Result |
| --- | --- |
| PostgreSQL healthy | Passed |
| Alembic current | Passed: `20260909_0002 (head)` |
| Documents table exists | Passed |
| Alembic downgrade/upgrade | Passed during implementation |
| Valid PDF upload | Passed: `201 Created` |
| Safe response | Passed: no internal path or hash |
| Fake PDF upload | Passed: rejected |
| Oversized upload | Passed: rejected |
| Duplicate upload | Passed: rejected |
| List documents | Passed |
| Detail metadata | Passed |
| Second-user isolation | Passed |
| Frontend registration | Passed |
| Frontend login | Passed |
| Protected Documents page | Passed |
| Frontend no-file validation | Passed |
| Frontend document list | Passed |
| Frontend delete | Passed |
| Deleted row removed from DB | Passed |
| Deleted file removed from private storage | Passed |
| No real user financial file deleted | Passed: only synthetic test document existed and was deleted |
| Backend tests | Passed |
| Frontend lint | Passed |
| Frontend build | Passed |

## Phase 5 Completion Checklist

- [x] Existing Phase 4 architecture reviewed.
- [x] Existing authentication preserved.
- [x] Financial account decision documented.
- [x] No unnecessary account workflow added.
- [x] Documents table exists via Alembic.
- [x] Documents belong to authenticated users.
- [x] User ownership is derived from `get_current_user`.
- [x] `user_id` is not accepted from clients.
- [x] Supported document types are controlled.
- [x] Only `bank_statement` and `credit_card_statement` are accepted.
- [x] PDF-only upload validation implemented.
- [x] Fake renamed PDFs are rejected.
- [x] Oversized uploads are rejected.
- [x] File-size limit is configurable.
- [x] Original filename is metadata only.
- [x] Safe server-generated storage key is used.
- [x] Uploaded files are stored privately.
- [x] Upload storage directory is ignored by Git.
- [x] SHA-256 file hash is calculated.
- [x] Duplicate-file policy works.
- [x] Upload API works.
- [x] Atomic cleanup for metadata insert failure is implemented.
- [x] Response schemas expose metadata only.
- [x] List documents API works.
- [x] Single document metadata API works.
- [x] Delete document API works.
- [x] Physical file cleanup works.
- [x] Missing physical file delete is handled safely.
- [x] Non-owner document access returns `404`.
- [x] Internal storage path is not exposed.
- [x] Frontend Documents page is protected.
- [x] Frontend upload form is present.
- [x] Frontend no-file validation works.
- [x] Frontend document list works.
- [x] Frontend delete works.
- [x] Existing authentication still works.
- [x] Backend tests pass.
- [x] Frontend lint passes.
- [x] Frontend build passes.
- [x] README updated.
- [x] Phase 5 report completed.
- [x] No real user financial file was deleted.
- [x] No transaction parsing has been started.
- [x] No OCR has been added.
- [x] No categorization has been added.
- [x] No analytics has been added.
- [x] No RAG, embeddings, pgvector, or LLM integration has been added.
- [x] Phase 6 not started.
