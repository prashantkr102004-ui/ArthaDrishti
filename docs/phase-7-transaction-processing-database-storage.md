# Phase 7: Transaction Processing & Database Storage

## Scope

Phase 7 converts validated Phase 6 parser output into canonical transaction records stored in PostgreSQL.

Implemented:

- canonical `transactions` table
- parser-output normalization service
- deterministic deduplication fingerprint
- parse-and-import workflow
- read-only transaction list/detail APIs
- protected frontend Transactions page
- end-to-end PDF to database tests

Deferred:

- categorization
- merchant inference
- analytics
- transaction editing/corrections
- budgets, goals, anomalies, forecasting
- RAG, embeddings, LLM financial Q&A

## Canonical Transaction Model

Stored transaction records include:

- `id`
- `user_id`
- `document_id`
- `transaction_date`
- `value_date`
- `raw_description`
- `normalized_description`
- `amount`
- `direction`
- `balance`
- `currency`
- `source_page`
- `source_row`
- `extraction_confidence`
- `dedupe_fingerprint`
- `created_at`
- `updated_at`

Fields intentionally deferred:

- `category_id`
- `subcategory`
- semantic merchant normalization
- recurring/anomaly fields
- prediction/correction metadata

## Money Decision

Money is represented with Python `Decimal` and PostgreSQL `NUMERIC(19,4)`.

Reason:

- avoids binary floating-point precision errors
- supports exact round trips for financial values
- leaves room for high-value statements and future currency support
- four decimal places are enough for banking precision while keeping analytics predictable

The backend rejects canonical transaction amounts that are zero or negative.

## Direction Model

The canonical rule is:

- `amount` is always positive
- `direction` is either `debit` or `credit`

This avoids mixing signed amounts from different statement formats. Analytics can later decide whether debit means expense/outflow and credit means income/inflow.

## Currency Model

Every transaction stores a three-letter uppercase currency code. Phase 7 supports `INR` only, but the column prevents hardcoding currency assumptions into future logic.

No exchange-rate conversion is implemented.

## Normalization Rules

Phase 7 performs deterministic cleanup only:

- trim descriptions
- collapse repeated whitespace and line breaks
- uppercase currency
- quantize money to four decimal places
- preserve the raw parser description

It does not infer merchants, categories, subscriptions, or anomalies.

## Deduplication Fingerprint

Each canonical transaction receives a SHA-256 fingerprint built from:

- fingerprint version
- user id
- account context, currently `none`
- transaction date
- value date
- amount quantized to four decimals
- direction
- currency
- normalized description, casefolded
- balance when available

The database enforces uniqueness on:

```text
user_id + dedupe_fingerprint
```

Policy:

- exact deterministic duplicates are skipped
- existing records are never overwritten
- import responses report duplicate counts
- transaction-level deduplication is intentionally conservative

Known limitation:

- two legitimate same-day transactions with identical date, amount, direction, description, and missing balance may be treated as duplicates. The fingerprint includes balance where available to reduce this risk.

## Idempotency

Processing the same document twice is safe:

- first run inserts transactions
- second run skips exact duplicates
- total stored transaction count remains unchanged

This is mandatory because users may retry processing after a page refresh or unclear UI state.

## Provenance Decision

Phase 7 uses direct transaction provenance:

```text
transactions.document_id -> documents.id
```

The record also stores `source_page`, `source_row`, and `raw_description`.

A separate `transaction_sources` table was considered but deferred. It would be useful when the same transaction is proven by multiple overlapping statements. For the MVP, direct provenance is simpler and enough to support traceability.

## Document Deletion Behavior

Deleting a document after importing transactions returns `409 Conflict`.

Reason:

- prevents accidental loss of source traceability
- avoids complicated cascade behavior with overlapping statements
- keeps correction/deletion workflows explicit for a later phase

Documents without imported transactions can still be deleted normally.

## Processing Workflow

Phase 7 keeps parsing and persistence separated internally:

```text
Document
-> PDF text extraction
-> parser output
-> canonical transaction normalization
-> duplicate detection
-> PostgreSQL insert
-> import summary
```

The existing parse endpoint now performs parse plus import:

```text
POST /api/v1/documents/{document_id}/parse
```

This keeps the user-facing workflow simple while preserving service boundaries in code.

## API Endpoints

Documents:

- `POST /api/v1/documents/{document_id}/parse`

Transactions:

- `GET /api/v1/transactions`
- `GET /api/v1/transactions/{transaction_id}`

List filters:

- `start_date`
- `end_date`
- `direction`
- `document_id`
- `limit`
- `offset`

Sorting:

- `transaction_date desc`
- `created_at desc`
- `id desc`

## Indexes

Implemented indexes:

- `user_id + transaction_date desc + created_at desc`
- `user_id + direction + transaction_date desc`
- `document_id`
- `user_id + document_id`
- unique `user_id + dedupe_fingerprint`

These support owner-scoped listing, date-range queries, direction filters, document-specific queries, and deduplication.

## Security Boundaries

- Clients never submit `user_id` for transactions.
- Ownership is derived from the authenticated user's document.
- Transaction list/detail APIs always filter by current user.
- Cross-user access returns empty lists or `404`.
- Filters are typed and validated by FastAPI/Pydantic.
- Raw SQL is not built from frontend input.
- Logs should not include raw statement text, bulk transaction history, account numbers, passwords, or tokens.

## Test Results

Verified automated backend coverage:

- auth tests still pass
- upload tests still pass
- parser tests still pass
- transaction persistence tests pass
- transaction ownership tests pass
- deduplication/idempotency tests pass
- filter and pagination tests pass
- document deletion behavior is tested
- database constraints are tested

Latest backend run:

```text
61 passed
```

Latest frontend checks:

```text
npm run lint: passed
npm run build: passed
```

## Known Limitations

- no transaction editing or correction workflow
- no category or merchant inference
- no financial analytics
- no multi-account linking yet
- no transaction source linking table yet
- only the Phase 6 synthetic statement format is fully supported

## Phase 7 Checklist

- [x] Transaction schema exists via Alembic
- [x] Canonical transaction model is implemented
- [x] Decimal/NUMERIC used for money
- [x] Debit/credit direction is consistent
- [x] Currency is stored explicitly
- [x] Transactions are tied to authenticated users
- [x] Transactions are traceable to source documents
- [x] Parser output is normalized deterministically
- [x] Deduplication works
- [x] Same document processing is idempotent
- [x] Overlapping duplicates are handled conservatively
- [x] Transaction list API works
- [x] Transaction detail API works
- [x] Ownership isolation works
- [x] Pagination works
- [x] Key filters work
- [x] Document deletion behavior is explicit and tested
- [x] End-to-end PDF to database test passes
- [x] Existing tests remain passing
- [x] Frontend Transactions page works
- [x] Frontend lint/build passes
- [x] README updated
- [x] No categorization or analytics has started
