# Phase 14: Security, Testing & Reliability

## Objective

Phase 14 hardens ArthaDrishti before deployment work begins. It does not add major user-facing features. The focus is authentication, authorization, privacy, document safety, API limits, LLM/RAG boundaries, error handling, testing, dependency checks, and production-readiness gaps.

## Architecture Review

Reviewed areas:

- authentication, password hashing, JWT creation and validation
- current-user dependency and ownership rules
- documents, private storage, PDF validation, parsing, deletion
- transaction persistence, deduplication, Decimal/NUMERIC money handling
- categories, merchant overrides, analytics, advanced insights
- assistant orchestration, approved tools, tool argument validation
- RAG indexing, embeddings, vector retrieval, source citations
- frontend auth flow, dashboard, documents, transactions, assistant, insights
- environment configuration, CORS, migrations, logging, and tests

## Concise Risk Inventory

| Area | Risk | Current Status |
| --- | --- | --- |
| Authentication | Brute-force login attempts | Lightweight in-memory rate limiting added; production distributed limiting remains required. |
| Authentication | Email enumeration | Login now returns generic invalid-credential errors for wrong, unknown, and inactive accounts. |
| JWT | Weak production secret | Production config validation rejects default/short JWT secrets. |
| Frontend auth | Bearer token theft through XSS | `sessionStorage` limits persistence but remains XSS-readable; HTTP-only cookies are a production hardening item. |
| IDOR | Cross-user UUID access | Major resource services filter by authenticated user; tests exist across documents, transactions, analytics, RAG, budgets, and goals. |
| Documents | Malicious filenames/path traversal | Original filename stored only as metadata; generated storage keys and resolved-path checks prevent traversal. |
| PDFs | Malformed, textless, or protected PDFs | PyMuPDF errors are converted into safe parser/indexing failures. OCR/password entry are deferred. |
| SQL injection | User strings reaching SQL | ORM is used broadly; RAG raw SQL uses bound parameters and internally generated fragments only. |
| Financial integrity | Float precision errors | Backend money uses `Decimal` and PostgreSQL `NUMERIC`; frontend formats values only. |
| LLM | Hallucinated financial numbers | Orchestrator grounds answers in tool output and replaces ungrounded numeric answers in tests. |
| RAG | Cross-user vector retrieval | Retrieval filters by `user_id` in SQL before returning chunks. |
| Prompt injection | Uploaded text instructs model | Retrieved chunks are treated as untrusted data; direct and indirect injection tests exist. |
| Logging | Sensitive financial content in logs | Existing logs use IDs/status/counts; full documents, tokens, and passwords are not logged. |
| Backups | No production backup system | Documented as Phase 15/deployment responsibility. |

## Fixed In Phase 14

- Added request/correlation IDs on API responses through `X-Request-ID`.
- Added backend security headers:
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `X-Frame-Options: DENY`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- Added equivalent non-breaking security headers to Next.js responses.
- Added in-memory rate limiting for:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/register`
  - `POST /api/v1/assistant/query`
  - `POST /api/v1/document-search`
  - `POST /api/v1/documents...`
- Changed inactive-account login failure to the same generic `Invalid email or password` response used for wrong passwords and unknown emails.
- Added production configuration validation:
  - `DEBUG=false` is required in production.
  - Default/weak JWT secrets are rejected in production.
  - wildcard frontend origins are rejected in production.
- Added focused tests for security headers, request IDs, rate limiting, and production config validation.

## Threat Model

| Asset | Threat | Current Mitigation | Residual Risk |
| --- | --- | --- | --- |
| User account | Credential stuffing | Argon2id, generic errors, in-memory rate limiting | Needs distributed limiter and monitoring in production. |
| JWT token | Token theft | Short-lived tokens, env secret, no token logging | Frontend `sessionStorage` is still XSS-readable. |
| User financial data | IDOR by UUID guessing | Current-user dependency and `user_id` filters | Requires continuous tests for every new resource. |
| Uploaded PDFs | Path traversal | Generated storage key, path resolution containment | Object storage policy needed in production. |
| Uploaded PDFs | Malicious PDF internals | Library APIs only, no shell execution, safe parse errors | Deep PDF sandboxing/OCR hardening deferred. |
| Transactions | SQL injection | SQLAlchemy and parameterized raw SQL | Review any future raw SQL carefully. |
| Analytics | Incorrect financial totals | Backend SQL/Decimal calculations only | Semantics must stay documented as features grow. |
| RAG chunks | Cross-user retrieval | SQL-level `user_id` filtering | Test all future retrieval paths. |
| Assistant | Direct prompt injection | System prompt and approved tool boundary | Live provider behavior should be monitored. |
| Assistant | Indirect prompt injection from documents | Retrieved text is untrusted data, not instructions | Stronger eval suite recommended before production. |
| API keys | Secret leakage | Env-only provider config; no frontend exposure | Use managed secrets in deployment. |
| Service reliability | Provider outage | AI failures are isolated from deterministic app features | Add provider timeouts/retries per real SDK. |
| Logs | Sensitive content exposure | Log IDs/counts/status, not documents/tokens/passwords | Central log redaction policy needed in production. |

## Authentication Findings

- Password hashing uses Argon2id through `argon2-cffi`.
- Registration password length is bounded to 8-128 characters.
- Login password input is bounded to 1-128 characters.
- Password hashes are not included in response schemas.
- Login now avoids inactive-account enumeration.
- JWT secret comes from environment.
- JWTs include `sub`, `iat`, and `exp`; expiry is validated.
- Refresh tokens, MFA, OAuth, password reset, and email verification remain out of scope.

## Authorization Findings

Ownership is derived from the authenticated user, not from frontend-supplied `user_id`.

Reviewed resources:

- documents
- transactions
- analytics
- categories and merchant overrides
- budgets
- goals
- assistant tools
- RAG document chunks/search
- advanced insights

The main pattern is:

```text
Bearer token
-> get_current_user
-> service filters by current_user.id
-> 404/unauthorized response for foreign resource
```

## Document Security

Documents are stored privately in backend-controlled storage, not in the frontend public directory. The original filename is kept only as metadata. Storage uses generated keys and path containment checks.

Upload validation checks:

- `.pdf` extension
- configured MIME type
- server-side size limit
- `%PDF-` signature
- duplicate SHA-256 per user

Parsing/indexing boundary:

- PDFs are treated as untrusted input.
- No document contents are executed.
- No shell commands are built from filenames or PDF text.
- Password-protected, textless, unsupported, and malformed PDFs fail safely.

## Financial Integrity

- Amounts are stored in PostgreSQL `NUMERIC` columns and handled as Python `Decimal`.
- Transaction amount must be positive; direction is `debit` or `credit`.
- Frontend formats money but does not calculate financial truth.
- Analytics and advanced features use deterministic backend services.
- Forecasts are labeled as estimates and require minimum history.
- Anomalies are financial anomalies, not confirmed fraud.

## AI/LLM Security

The assistant has no direct database credentials, SQL executor, filesystem access, or arbitrary HTTP access.

It can only call approved tools:

- analytics tools
- transaction listing with strict limits
- document search/RAG
- recurring/subscription/budget/goal/forecast/anomaly tools

Tool arguments are validated by Pydantic/service logic. The model cannot provide `user_id`; authenticated ownership is injected by the backend.

## RAG Security

RAG is for unstructured document text only. Structured financial totals continue to use deterministic analytics.

Security properties:

- indexing requires document ownership
- retrieval filters by authenticated `user_id` in SQL
- `top_k` is bounded
- document filters are ownership-validated
- sources expose document name/page/chunk metadata, not embeddings or storage paths
- deleted documents cascade/delete chunks

## Frontend Security

Reviewed:

- no `dangerouslySetInnerHTML`
- token storage is centralized
- error display uses safe API messages
- internal storage keys and backend paths are not shown
- account numbers are not displayed
- document/RAG sources do not expose private file paths

Current limitation:

- Bearer tokens live in `sessionStorage`. This is better than persistent `localStorage`, but it is still readable by injected JavaScript. Move to HTTP-only secure cookies or a backend session design before high-risk production use.

## API, CORS, Headers

- CORS origins are configured through `FRONTEND_ORIGIN`.
- Wildcard frontend origins are rejected in production config.
- Backend and frontend security headers are configured.
- HTTPS/HSTS are deployment-layer requirements for Phase 15.
- Strict CSP is recommended for production after testing Next.js script requirements.

## Rate Limiting

Implemented MVP in-memory rate limiting for sensitive endpoints. Default limits are intentionally conservative for a local modular-monolith development environment: 120 requests per minute per client/method/protected path prefix. This reduces accidental abuse and basic local brute-force attempts without breaking automated integration tests.

Accepted MVP limitation:

- In-memory limits reset on process restart and do not coordinate across multiple backend instances.

Must fix before public production:

- Move rate limiting to Redis, an API gateway, WAF, or reverse proxy.
- Add separate user/IP/device-aware policies.
- Add monitoring and alerting for repeated auth failures.

## Error Handling

Current behavior:

- authentication errors are safe and generic where needed
- validation errors are handled by FastAPI/Pydantic
- document/parser/RAG/provider failures return safe details
- request IDs allow correlating user-safe errors with server logs

Production improvement:

- Add centralized exception handlers that include request IDs in JSON error payloads while preserving FastAPI validation detail.

## Logging And Audit

Current logging avoids passwords, tokens, full PDF text, full statements, and API keys. Logs prefer IDs, counts, statuses, and operation names.

Persistent audit logging is not implemented in Phase 14. Recommended events:

- login success/failure
- document upload/delete/parse/index
- transaction import
- category override
- budget create/update/delete
- goal create/update/delete
- assistant query tool names and success/failure

## Test Strategy

Existing tests cover:

- authentication and JWT behavior
- document upload security and ownership
- parser failures
- transaction persistence/deduplication
- categorization and overrides
- analytics semantics and ownership
- assistant tool grounding and prompt injection
- RAG indexing/search/isolation
- advanced features and ownership

Phase 14 added:

- security headers and request ID test
- sensitive endpoint rate-limit test
- production config validation test

Critical paths to keep green:

```text
register -> login -> upload -> parse -> import -> categorize -> analytics
index document -> search -> grounded RAG answer
transactions -> recurring/subscription -> budgets/goals -> forecast/anomaly
```

## Dependency Audit

Node:

- `npm audit --audit-level=moderate`
- Result: `found 0 vulnerabilities`

Python:

- `pip-audit --cache-dir .pip-audit-cache`
- First run found advisories only for the local virtualenv `pip` package.
- Local virtualenv `pip` was upgraded to `26.2.1`.
- Rerun result: no known vulnerabilities found.
- `arthadrishti-backend` is skipped because it is a local package, not a PyPI-published dependency.

## Database Reliability

Migrations are versioned through Alembic:

- users
- documents
- transactions
- categories/merchant rules/overrides
- document chunks/pgvector
- budgets/goals

Production recommendations:

- Verify full migration replay from an empty PostgreSQL database in CI.
- Test recent downgrade/upgrade paths only on disposable databases.
- Add backup and restore testing before deployment.

## Backup Recommendations

PostgreSQL:

- automated encrypted backups
- point-in-time recovery if using managed Postgres
- regular restore drills
- retention policy aligned with project/privacy requirements

Documents:

- private object storage
- server-side encryption
- versioning where appropriate
- lifecycle/retention rules
- deletion process that removes related chunks/embeddings

## Privacy Considerations

Data kept local in development:

- uploaded PDFs
- parsed transactions
- document chunks
- deterministic analytics
- budgets and goals

Data that may be sent to external AI providers when configured:

- user question
- approved tool results
- aggregated financial values
- limited transaction excerpts when needed
- retrieved document chunks for RAG answers

Data not sent intentionally:

- raw full PDFs
- storage paths
- database credentials
- JWTs
- API keys
- unrestricted transaction exports

## Remaining Known Risks

Accepted MVP limitations:

- `sessionStorage` token storage is XSS-readable.
- rate limiting is in-memory.
- persistent audit logs are not implemented.
- strict CSP is deferred.
- Python dependency audit tool is missing locally.
- database-backed verification currently requires PostgreSQL availability.

Must fix before public production:

- HTTP-only cookie/session design or equivalent token hardening
- production-grade rate limiting
- HTTPS/HSTS and deployment security headers
- managed secrets
- backup/restore automation
- centralized audit logs
- CI migration replay and security tests
- dependency vulnerability scanning
- monitoring/alerting

## Verification Notes

Completed in this Phase 14 run:

- backend compile check passed
- Phase 14 hardening tests passed
- existing Phase 13 tests passed
- full backend suite passed: 111 tests
- PostgreSQL was healthy after Docker Desktop recovered
- Alembic `upgrade head` completed successfully
- frontend lint passed
- frontend build passed after Next.js header change
- Node audit passed with zero vulnerabilities
- Python audit passed after upgrading local virtualenv `pip`
- secret-like scan found only placeholders/docs/test references
- no committed PDF/image/spreadsheet financial fixtures were found outside ignored/generated locations

Earlier in this run, PostgreSQL was temporarily unavailable because Docker Desktop/WSL was not responding. Verification resumed after `arthadrishti-postgres` became healthy.

## Viva Preparation

### How are passwords protected?

Passwords are never stored directly. They are hashed with Argon2id, a modern password-hashing algorithm designed to resist brute force. Only the hash is stored, and password fields are never returned by API response schemas.

### How do you prevent one user from accessing another user's financial records?

The backend derives ownership from the authenticated JWT through `get_current_user`. Services filter documents, transactions, budgets, goals, analytics, RAG chunks, and assistant tools by that user. The frontend never gets to choose `user_id`.

### How do you protect uploaded documents?

Only PDFs are accepted, size is limited, MIME/signature are checked, filenames are not trusted as paths, storage keys are generated by the backend, and files are kept outside public frontend directories.

### Why is Decimal important for financial systems?

Floating-point numbers can introduce rounding artifacts. Financial systems need exact decimal arithmetic, so ArthaDrishti uses Python `Decimal` and PostgreSQL `NUMERIC`.

### How do you protect against SQL injection?

Most database access uses SQLAlchemy query construction. Where raw SQL is necessary for pgvector/RAG, user values are passed as bound parameters rather than interpolated into SQL strings.

### How do you prevent LLM prompt injection?

The LLM cannot access the database directly or create new permissions. It can only call approved backend tools with validated arguments. Retrieved document text is treated as untrusted data, not instructions.

### Can the LLM directly access the database?

No. It can request approved tools, and the backend executes deterministic services using the authenticated user context.

### How is RAG isolated between users?

Document chunks store `user_id`, and retrieval filters by `user_id` in SQL. If a document ID is provided, ownership is checked before retrieval.

### How do you prevent API keys from leaking?

Provider keys are environment variables, not frontend values. They are not returned by APIs and should be managed by a production secret manager.

### What happens if the AI provider goes down?

AI features return controlled errors. Documents, transactions, dashboard analytics, budgets, goals, and other deterministic features continue to work.

### What are the main remaining production risks?

The main risks are token storage hardening, distributed rate limiting, persistent audit logs, production backup/restore, strict CSP, dependency scanning in CI, and deployment-layer HTTPS/HSTS.

## Phase 14 Checklist

- [x] Authentication reviewed.
- [x] JWT configuration reviewed.
- [x] Password handling reviewed.
- [x] Login inactive-account enumeration fixed.
- [x] Ownership/IDOR patterns reviewed across major services.
- [x] Upload validation reviewed.
- [x] Path traversal protection reviewed.
- [x] PDF failure boundary reviewed.
- [x] Decimal integrity reviewed.
- [x] SQL injection risk reviewed.
- [x] Frontend XSS risk reviewed.
- [x] LLM tool permission boundary reviewed.
- [x] Direct and indirect prompt-injection tests identified in suite.
- [x] RAG user isolation reviewed.
- [x] Query/upload/tool limits reviewed.
- [x] Request IDs added.
- [x] Security headers added.
- [x] Lightweight rate limiting added.
- [x] Node dependency audit completed.
- [x] Python dependency audit completed.
- [x] Secret-like string scan completed.
- [x] Backup/recovery recommendations documented.
- [x] Privacy boundaries documented.
- [x] Threat model documented.
- [x] Phase 14 report created.
- [x] Full backend suite passed in current run.
- [x] PostgreSQL healthy in current run.
- [x] Alembic upgrade verified in current run.
- [x] Frontend lint/build rerun after all Phase 14 frontend changes.
