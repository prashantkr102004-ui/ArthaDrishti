# Security Overview

## Authentication

- Users authenticate with email/password.
- Passwords are hashed with Argon2id.
- Passwords and password hashes are never returned by API schemas.
- Login errors are generic to avoid account enumeration.
- JWT access tokens include subject, issued-at, and expiry claims.
- Production configuration rejects weak/default JWT secrets.

## Authorization

The client never supplies authoritative `user_id`. Ownership is derived from the authenticated user:

```text
Bearer token -> get_current_user -> service filters by current_user.id
```

This pattern protects documents, transactions, analytics, budgets, goals, RAG chunks, and assistant tools from IDOR attacks.

## Document Security

- Only PDF uploads are accepted.
- File size is bounded.
- MIME type and `%PDF-` signature are checked.
- Original filename is metadata only.
- Backend generates storage keys.
- Private storage is outside frontend public routes.
- PDF parsing uses library APIs only and does not execute document content.

## Financial Integrity

- Money uses PostgreSQL `NUMERIC` and Python `Decimal`.
- The frontend formats financial values but does not calculate truth.
- Analytics, forecasts, budgets, and goals are backend-generated.

## LLM And RAG

- LLMs cannot run SQL or access credentials.
- Tool arguments are validated before execution.
- Retrieved document text is untrusted data.
- RAG retrieval filters by `user_id` in SQL.
- Prompt-injection tests cover direct user prompts and indirect PDF content.

## API Security

- CORS origins are environment-configured.
- Wildcard frontend origins are rejected in production.
- Security headers and request IDs are added.
- Sensitive endpoints have lightweight in-memory rate limiting.

## Logging

Logs should include operation names, IDs, statuses, counts, and request IDs. Logs must not include passwords, JWTs, API keys, raw PDFs, full statements, or bulk transaction descriptions.

## Known Production Gaps

- Replace `sessionStorage` bearer tokens with HTTP-only secure cookies or a hardened session design.
- Replace in-memory rate limits with distributed/API-gateway limits.
- Add persistent audit logs.
- Add HTTPS, HSTS, and a tested Content Security Policy.
- Use managed secrets and encrypted object storage.
- Add automated backup/restore validation.
