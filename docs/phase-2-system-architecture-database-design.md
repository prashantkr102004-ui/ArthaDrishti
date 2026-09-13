# ArthaDrishti: Smart Financial Assistant

## Phase 2: System Architecture & Database Design

Phase 1 defined ArthaDrishti as a trustworthy personal financial analysis and planning assistant. Phase 2 defines the architecture and database design needed to build the MVP without overengineering it.

This document is not an implementation plan for code generation. It intentionally avoids backend code, frontend code, migrations, Docker files, and application scaffolding.

## 1. Overall System Architecture

ArthaDrishti should use a modular monolith for the MVP:

- Next.js frontend for user interaction.
- FastAPI backend for API, business logic, document workflows, deterministic analytics, and controlled future AI tool access.
- PostgreSQL as the primary source of truth.
- Local filesystem storage during development for uploaded PDFs.
- Object storage in production for uploaded PDFs.
- Optional background worker later for heavier document parsing.
- LLM and RAG layers designed as bounded internal services, not direct database clients.

### High-Level Architecture Diagram

```text
                         +-----------------------------+
                         |        Next.js Frontend      |
                         |                             |
                         | Auth UI                     |
                         | Dashboard                   |
                         | Documents                   |
                         | Transactions Review         |
                         | Analytics                   |
                         | Future Assistant            |
                         +--------------+--------------+
                                        |
                                        | HTTPS / REST API
                                        v
                         +--------------+--------------+
                         |       FastAPI Backend        |
                         |   Modular Monolith API       |
                         +--------------+--------------+
                                        |
        +-------------------------------+--------------------------------+
        |                               |                                |
        v                               v                                v
+-------+--------+             +--------+---------+              +--------+--------+
| Auth / Users   |             | Documents Module |              | Analytics       |
| Authorization  |             | Upload Pipeline  |              | Engine          |
+-------+--------+             +--------+---------+              +--------+--------+
        |                               |                                |
        |                               v                                |
        |                    +----------+-----------+                    |
        |                    | Document Processing  |                    |
        |                    | Validation           |                    |
        |                    | Parsing              |                    |
        |                    | Extraction           |                    |
        |                    | Normalization        |                    |
        |                    | Deduplication        |                    |
        |                    | Categorization       |                    |
        |                    +----------+-----------+                    |
        |                               |                                |
        +-------------------------------+--------------------------------+
                                        |
                                        v
                         +--------------+--------------+
                         |          PostgreSQL          |
                         | Users                       |
                         | Financial Accounts          |
                         | Documents                   |
                         | Transactions                |
                         | Categories                  |
                         +--------------+--------------+
                                        |
                    +-------------------+--------------------+
                    |                                        |
                    v                                        v
        +-----------+------------+              +------------+-----------+
        | File/Object Storage    |              | Future Extensions       |
        | Dev: local filesystem  |              | pgvector RAG            |
        | Prod: S3-compatible    |              | ML jobs                 |
        +------------------------+              | Reports                 |
                                                | Assistant tools         |
                                                +------------------------+
```

### Component Responsibilities

### Frontend

The frontend is responsible for user-facing workflows:

- Authentication screens.
- Account management.
- Document upload.
- Processing status display.
- Transaction review and correction.
- Dashboard and analytics visualization.
- Future assistant interface.
- Settings and privacy controls.

The frontend must not calculate authoritative financial numbers. It can format and visualize values returned by the backend, but totals and metrics should come from backend services.

### Backend API

The backend API is responsible for:

- Authentication and authorization.
- Validating requests.
- Enforcing user ownership.
- Managing documents, accounts, transactions, and categories.
- Triggering or running document processing.
- Running deterministic analytics.
- Exposing controlled future AI tools.
- Returning structured responses to the frontend.

### Authentication Layer

The authentication layer verifies user identity and attaches an authenticated user context to every protected request.

For the MVP, a simple email/password authentication flow with secure password hashing is enough. The architecture should still allow replacement with OAuth or managed authentication later.

### Document Upload Flow

The upload flow handles:

- File type validation.
- Size limits.
- PDF validation.
- Secure file naming.
- Storage location creation.
- Document metadata persistence.
- Processing status initialization.
- Processing trigger.

Uploaded documents are untrusted input and must never be executed, trusted blindly, or exposed to other users.

### Document Processing Pipeline

The document processing pipeline handles:

- Parsing text-based PDFs.
- Detecting unsupported scanned PDFs.
- Extracting raw transaction rows.
- Mapping raw rows to normalized transaction fields.
- Assigning extraction confidence.
- Validating required fields.
- Generating deduplication fingerprints.
- Preparing records for user review or direct import depending on confidence and product choice.

### Transaction Processing

The transaction processing layer handles:

- Debit/credit direction normalization.
- Amount parsing.
- Currency assignment.
- Date parsing.
- Account association.
- Source document association.
- Category assignment.
- Duplicate detection.
- User corrections.
- Confirmed transaction storage.

### Database

PostgreSQL is the primary source of truth for users, accounts, documents, transactions, categories, and analytics source data.

The database should store metadata and normalized financial records, not necessarily raw PDF bytes.

### Analytics Engine

The analytics engine computes:

- Income.
- Expenses.
- Savings.
- Savings rate.
- Monthly cash flow.
- Category totals.
- Month-over-month comparisons.
- Top merchants.

For the MVP, analytics should be implemented through SQL queries coordinated by backend service code. Python may shape the response, but SQL should perform aggregation where practical.

### LLM Integration Layer

The future LLM layer should:

- Interpret user intent.
- Choose approved backend tools.
- Explain deterministic results.
- Help with ambiguous categorization where allowed.
- Never freely query the database.
- Never calculate authoritative financial metrics from raw text.

### Future RAG Layer

The future RAG layer should:

- Extract document text.
- Chunk text.
- Generate embeddings.
- Store vectors in pgvector.
- Filter retrieval by user and document ownership.
- Return citations from source document/page metadata.

RAG is for unstructured document questions. Structured financial questions should use deterministic analytics tools.

### Future ML Layer

The future ML layer may support:

- Recurring-payment detection.
- Subscription detection.
- Anomaly detection.
- Forecasting.
- Merchant normalization improvements.

These should be batch or service-layer features built on confirmed transaction data, not replacements for the deterministic transaction ledger.

## 2. Architectural Style

### Decision: Modular Monolith For MVP

ArthaDrishti should use a modular monolith for the MVP.

Reason:

- The product is still proving its core extraction, review, storage, and analytics loop.
- FastAPI can cleanly support module boundaries without service sprawl.
- A single PostgreSQL database keeps transactions, accounts, and analytics consistent.
- Local development and final-year project demonstration are simpler.
- Microservices would add operational complexity before the domain boundaries are stable.

### Why Not Microservices Now

Microservices would require extra work for:

- Inter-service authentication.
- Network calls between services.
- Distributed tracing.
- Independent deployment.
- Message queues.
- Data consistency across services.
- More Docker and infrastructure setup.

That complexity is not justified for the MVP.

### Conditions That Would Justify Splitting Later

Service boundaries may be split later if:

- Document processing becomes CPU-heavy or slow enough to require independent scaling.
- OCR or ML workloads need GPU or specialized infrastructure.
- RAG indexing and retrieval become a separate operational concern.
- Multiple product teams work independently on different domains.
- The assistant/agent layer needs separate sandboxing and rate limits.
- Background jobs need separate deployment and monitoring.
- The product grows beyond personal finance into business or enterprise workflows.

Likely future split candidates:

- Document processing worker service.
- AI/RAG service.
- ML/anomaly detection service.
- Reporting service.

## 3. Backend Module Design

The backend should be organized as a modular monolith with clear package boundaries. The exact files should be created in Phase 3, not now.

### auth

Responsible for:

- Login.
- Registration.
- Password hashing.
- Token creation and validation.
- Current-user dependency.

Boundary:

- Auth identifies users but should not own financial records.
- Other modules receive user context from auth and enforce ownership.

### users

Responsible for:

- User profile data.
- User settings that affect the whole account.
- Future deletion/export workflows.

Boundary:

- Does not manage financial accounts or transactions directly.

### accounts

Responsible for:

- Bank account and credit-card account records.
- Account metadata.
- Masked account identifiers.
- Account ownership.

Boundary:

- Does not parse documents.
- Does not calculate analytics except account-level lookup filters.

### documents

Responsible for:

- Upload metadata.
- File validation metadata.
- Document status.
- Source file storage references.
- Statement period metadata.
- Processing errors.

Boundary:

- Does not own final analytics.
- Calls processing services but stores document lifecycle state.

### document_processing

Responsible for:

- PDF extraction.
- Statement layout recognition.
- Table extraction.
- Raw row parsing.
- Normalization candidate creation.
- Extraction confidence.
- Deduplication fingerprint generation.

Boundary:

- Produces transaction candidates or transactions.
- Does not expose public API endpoints directly unless needed through documents.

### transactions

Responsible for:

- Normalized transaction records.
- Review and correction.
- Deduplication checks.
- Transaction CRUD.
- Source document and account relationships.

Boundary:

- Does not implement dashboard analytics beyond transaction retrieval.

### categories

Responsible for:

- Default categories.
- User-visible categories.
- Category assignment.
- Future user customization.

Boundary:

- Does not own transaction calculations.

### analytics

Responsible for:

- SQL-backed financial calculations.
- Period filters.
- Category summaries.
- Monthly comparisons.
- Top merchants.
- Response models for dashboard charts.

Boundary:

- Reads confirmed transactions.
- Does not mutate transaction records except possibly cached analytics in future.
- Does not use LLMs for calculations.

### ai

Responsible for future:

- LLM provider abstraction.
- Prompt construction.
- Tool-calling orchestration.
- Response explanation.
- AI classification utilities where allowed.

Boundary:

- No unrestricted SQL access.
- Calls approved backend services/tools only.
- Does not create authoritative financial numbers.

### rag

Responsible for future:

- Document chunking.
- Embedding jobs.
- Vector storage.
- Retrieval APIs.
- Citation assembly.

Boundary:

- Deferred from MVP.
- Must enforce user/document filters.

### ml

Responsible for future:

- Recurring-transaction detection.
- Subscription detection.
- Anomaly detection.
- Forecasting.

Boundary:

- Deferred from MVP.
- Consumes confirmed transactions.
- Produces suggestions, flags, or insights rather than overwriting financial truth.

### security

Responsible for:

- File safety utilities.
- Redaction helpers.
- Authorization helpers.
- Secret/config validation.
- Security policy constants.

Boundary:

- Provides shared utilities, not business ownership.

### audit

Responsible for future:

- Audit log records.
- User action history.
- Data export/delete evidence.

Boundary:

- Postponed for MVP unless required by deployment/demo needs.

## 4. Frontend Architecture

The frontend should use Next.js with TypeScript and a feature-oriented structure. The MVP UI should prioritize the core workflow over a broad assistant experience.

### Main Frontend Areas

### Authentication

Needed for:

- Sign up.
- Login.
- Logout.
- Basic session handling.

MVP scope: include only if the project is not strictly local-single-user. Since multi-user isolation is a requirement from the beginning, authentication should be included early.

### Dashboard

Needed for:

- Financial summary cards.
- Income, expense, savings, savings rate.
- Monthly cash-flow chart.
- Category spending chart.
- Top merchants.
- Recent imported documents or transactions.

MVP scope: yes.

### Documents

Needed for:

- Upload statements.
- View uploaded documents.
- See processing state.
- See processing errors.
- Start review of extracted transactions.

MVP scope: yes.

### Transactions

Needed for:

- Review extracted transactions.
- Filter by account, date, category, direction.
- Edit category, merchant, description, date, amount if needed.
- Confirm import or mark rows for exclusion.

MVP scope: yes, but keep the UI practical rather than spreadsheet-grade.

### Analytics

Needed for:

- Period filters.
- Category breakdowns.
- Month-over-month comparisons.
- Merchant summaries.

MVP scope: can be part of dashboard first. A separate analytics area can come after the dashboard becomes crowded.

### Assistant

Needed later for:

- Natural-language questions.
- Explanations over deterministic analytics.
- Document-grounded answers with citations.

MVP scope: deferred. A placeholder route is acceptable later, but not necessary in Phase 2 or MVP implementation.

### Settings

Needed for:

- Account profile.
- Category management.
- Privacy/data deletion later.
- LLM usage preferences later.

MVP scope: minimal or deferred except basic account/logout controls.

### Recommended MVP Frontend Scope

- Login/register.
- Dashboard.
- Documents upload/status.
- Transaction review table.
- Transactions list.
- Basic analytics widgets integrated into dashboard.
- Minimal settings/account menu.

## 5. Database Design

PostgreSQL should model the MVP around five core entities:

- users
- financial_accounts
- documents
- categories
- transactions

This is enough to support authentication, multi-user isolation, document traceability, multi-account records, categorization, and deterministic analytics.

### MVP Tables Needed

### users

Needed for authentication and ownership.

### financial_accounts

Needed because transactions must belong to a bank account or credit-card account, and future multi-account analysis depends on this.

### documents

Needed to track uploaded PDFs, processing state, errors, source metadata, and source traceability.

### categories

Needed for category-wise analytics and user correction.

### transactions

Needed as the core financial ledger of normalized transaction records.

### Tables To Postpone

### document_chunks

Postpone until RAG is implemented.

### conversations

Postpone until the assistant interface exists.

### messages

Postpone until conversation persistence is required.

### budgets

Postpone until budgeting becomes a product feature.

### goals

Postpone until financial goal planning is implemented.

### recurring_transactions

Postpone until recurring-payment detection exists. The MVP can avoid `is_recurring` on transactions or add a nullable flag later through a migration.

### anomalies

Postpone until anomaly detection exists. The MVP should not add `is_anomaly` yet.

### audit_logs

Postpone for local MVP unless the deployed version needs compliance-style action history. Keep architecture ready by using service boundaries where audit events can later be emitted.

### extraction_runs

Postpone unless repeated extraction attempts per document become necessary. For MVP, processing status and error fields on `documents` are sufficient.

## 6. Table Definitions

These are logical table definitions, not migrations.

### users

Purpose:

- Stores application users and authentication identity.

Fields:

```text
id                 UUID            primary key, default gen_random_uuid()
email              TEXT            not null
password_hash      TEXT            not null
full_name          TEXT            nullable
default_currency   CHAR(3)         not null, default 'INR'
created_at         TIMESTAMPTZ     not null, default now()
updated_at         TIMESTAMPTZ     not null, default now()
```

Primary key:

- `id`

Unique constraints:

- Unique `email`, case-insensitive in application logic or using a functional unique index on `lower(email)`.

Important indexes:

- `users_lower_email_idx` on `lower(email)`.

Notes:

- Password hashes must use a strong password hashing algorithm such as Argon2id or bcrypt.
- Do not store plain-text passwords.

### financial_accounts

Purpose:

- Represents a user's bank accounts and credit-card accounts.

Fields:

```text
id                    UUID          primary key, default gen_random_uuid()
user_id               UUID          not null
account_type          TEXT          not null
display_name          TEXT          not null
institution_name      TEXT          nullable
masked_account_number TEXT          nullable
currency              CHAR(3)       not null, default 'INR'
created_at            TIMESTAMPTZ   not null, default now()
updated_at            TIMESTAMPTZ   not null, default now()
```

Primary key:

- `id`

Foreign keys:

- `user_id` references `users(id)` on delete cascade.

Nullable fields:

- `institution_name`
- `masked_account_number`

Defaults:

- `currency`: `'INR'`
- timestamps: `now()`

Suggested allowed `account_type` values:

- `bank`
- `credit_card`

Unique constraints:

- Optional MVP unique constraint on `(user_id, display_name)`.
- Avoid requiring masked account number uniqueness because many statements only expose partial or inconsistent account identifiers.

Important indexes:

- `financial_accounts_user_id_idx` on `user_id`.
- `financial_accounts_user_type_idx` on `(user_id, account_type)`.

### documents

Purpose:

- Tracks uploaded financial documents and processing lifecycle.

Fields:

```text
id                    UUID          primary key, default gen_random_uuid()
user_id               UUID          not null
account_id            UUID          nullable
document_type         TEXT          not null
original_filename     TEXT          not null
storage_backend       TEXT          not null
storage_key           TEXT          not null
mime_type             TEXT          not null
file_size_bytes       BIGINT        not null
sha256_hash           TEXT          not null
statement_start_date  DATE          nullable
statement_end_date    DATE          nullable
status                TEXT          not null, default 'uploaded'
error_code            TEXT          nullable
error_message         TEXT          nullable
detected_institution  TEXT          nullable
detected_account_ref  TEXT          nullable
uploaded_at           TIMESTAMPTZ   not null, default now()
processing_started_at TIMESTAMPTZ   nullable
processing_finished_at TIMESTAMPTZ  nullable
created_at            TIMESTAMPTZ   not null, default now()
updated_at            TIMESTAMPTZ   not null, default now()
```

Primary key:

- `id`

Foreign keys:

- `user_id` references `users(id)` on delete cascade.
- `account_id` references `financial_accounts(id)` on delete set null.

Nullable fields:

- `account_id`
- `statement_start_date`
- `statement_end_date`
- `error_code`
- `error_message`
- `detected_institution`
- `detected_account_ref`
- processing timestamps except upload/created timestamps

Defaults:

- `status`: `'uploaded'`
- timestamps: `now()`

Suggested allowed `document_type` values:

- `bank_statement`
- `credit_card_statement`

Suggested allowed `storage_backend` values:

- `local`
- `object_storage`

Suggested allowed `status` values:

- `uploaded`
- `queued`
- `processing`
- `needs_review`
- `completed`
- `failed`

Unique constraints:

- Unique `(user_id, sha256_hash)` to prevent exact duplicate document uploads for the same user.

Important indexes:

- `documents_user_id_idx` on `user_id`.
- `documents_user_status_idx` on `(user_id, status)`.
- `documents_user_uploaded_at_idx` on `(user_id, uploaded_at desc)`.
- `documents_user_hash_idx` on `(user_id, sha256_hash)`.
- `documents_account_id_idx` on `account_id`.

Notes:

- `storage_key` should be an internal key, not a public URL.
- `error_message` should be safe for frontend display and should avoid leaking internal stack traces.

### categories

Purpose:

- Stores spending/income categories for classification and analytics.

Fields:

```text
id                  UUID          primary key, default gen_random_uuid()
user_id             UUID          nullable
name                TEXT          not null
type                TEXT          not null
parent_category_id  UUID          nullable
color               TEXT          nullable
icon                TEXT          nullable
is_system           BOOLEAN       not null, default false
created_at          TIMESTAMPTZ   not null, default now()
updated_at          TIMESTAMPTZ   not null, default now()
```

Primary key:

- `id`

Foreign keys:

- `user_id` references `users(id)` on delete cascade.
- `parent_category_id` references `categories(id)` on delete set null.

Nullable fields:

- `user_id`, for global system categories.
- `parent_category_id`
- `color`
- `icon`

Defaults:

- `is_system`: `false`
- timestamps: `now()`

Suggested allowed `type` values:

- `income`
- `expense`
- `transfer`
- `other`

Unique constraints:

- Unique `(user_id, lower(name), type)` for user categories.
- Unique `(lower(name), type)` where `user_id is null` for system categories.

Important indexes:

- `categories_user_id_idx` on `user_id`.
- `categories_type_idx` on `type`.
- `categories_parent_idx` on `parent_category_id`.

Notes:

- This supports default categories now and user-editable categories later.
- The MVP should seed system categories and allow category override on transactions.

### transactions

Purpose:

- Stores normalized financial transaction records derived from documents and user corrections.

Fields:

```text
id                         UUID          primary key, default gen_random_uuid()
user_id                    UUID          not null
account_id                 UUID          not null
document_id                UUID          nullable
transaction_date           DATE          not null
value_date                 DATE          nullable
raw_description            TEXT          not null
normalized_description     TEXT          nullable
merchant                   TEXT          nullable
amount                     NUMERIC(19,4) not null
direction                  TEXT          not null
currency                   CHAR(3)       not null, default 'INR'
balance                    NUMERIC(19,4) nullable
category_id                UUID          nullable
extraction_confidence      NUMERIC(5,4)  nullable
categorization_confidence  NUMERIC(5,4)  nullable
source_page                INTEGER       nullable
raw_row_text               TEXT          nullable
dedupe_fingerprint         TEXT          nullable
review_status              TEXT          not null, default 'needs_review'
created_at                 TIMESTAMPTZ   not null, default now()
updated_at                 TIMESTAMPTZ   not null, default now()
```

Primary key:

- `id`

Foreign keys:

- `user_id` references `users(id)` on delete cascade.
- `account_id` references `financial_accounts(id)` on delete cascade.
- `document_id` references `documents(id)` on delete set null.
- `category_id` references `categories(id)` on delete set null.

Nullable fields:

- `document_id`, to allow future manually entered transactions.
- `value_date`
- `normalized_description`
- `merchant`
- `balance`
- `category_id`
- confidence fields
- `source_page`
- `raw_row_text`
- `dedupe_fingerprint`

Defaults:

- `currency`: `'INR'`
- `review_status`: `'needs_review'`
- timestamps: `now()`

Suggested allowed `direction` values:

- `debit`
- `credit`

Suggested allowed `review_status` values:

- `needs_review`
- `confirmed`
- `excluded`

Unique constraints:

- Unique `(user_id, account_id, dedupe_fingerprint)` where `dedupe_fingerprint is not null`.

Important indexes:

- `transactions_user_date_idx` on `(user_id, transaction_date desc)`.
- `transactions_user_account_date_idx` on `(user_id, account_id, transaction_date desc)`.
- `transactions_user_category_date_idx` on `(user_id, category_id, transaction_date desc)`.
- `transactions_user_direction_date_idx` on `(user_id, direction, transaction_date desc)`.
- `transactions_document_id_idx` on `document_id`.
- `transactions_user_review_status_idx` on `(user_id, review_status)`.
- `transactions_user_merchant_idx` on `(user_id, merchant)`.
- `transactions_user_dedupe_idx` on `(user_id, account_id, dedupe_fingerprint)`.

Notes:

- `amount` should store an absolute positive amount. `direction` determines whether it is money out or money in.
- Analytics should include only `review_status = 'confirmed'` unless explicitly showing draft/unreviewed results.
- Credit-card payments, refunds, interest, and fees need clear classification rules before analytics are trusted.

## 7. Transaction Data Model

The transaction model is the heart of the system. It should be expressive enough for analytics and future AI use, but not bloated with fields that imply features we have not built.

### Include In MVP

- `id`: stable transaction identifier.
- `user_id`: required for ownership and isolation.
- `account_id`: required for account-level analytics.
- `document_id`: required when imported from a statement; nullable for future manual entries.
- `transaction_date`: required for analytics.
- `value_date`: optional because not all statements provide it.
- `raw_description`: required because it preserves source evidence.
- `normalized_description`: optional cleanup for search/display.
- `merchant`: optional because merchant extraction may be uncertain.
- `amount`: required exact decimal value.
- `direction`: required debit/credit classification.
- `currency`: required ISO 4217 code.
- `balance`: optional because many credit-card statements do not provide running balances.
- `category_id`: optional because category may be missing or reviewed later.
- `extraction_confidence`: optional but recommended for review workflow.
- `categorization_confidence`: optional but recommended for category transparency.
- `source_page`: optional traceability.
- `raw_row_text`: optional traceability/debugging.
- `dedupe_fingerprint`: optional but recommended.
- `review_status`: required to separate draft from confirmed records.
- `created_at` and `updated_at`: required for lifecycle tracking.

### Postpone From MVP

- `subcategory`: do not store as a transaction text field. Use `categories.parent_category_id` later if hierarchy is needed.
- `is_recurring`: postpone until recurring detection exists.
- `is_anomaly`: postpone until anomaly detection exists.
- `agent_notes`: postpone until assistant workflows exist.
- `embedding_id`: postpone until RAG/vector search exists.
- `tax_label`: postpone until tax workflows exist.
- `budget_id`: postpone until budgets exist.

### Avoid Redundancy

Avoid storing both signed amount and direction in the MVP. Store `amount` as a positive decimal and `direction` as `debit` or `credit`. This reduces confusion across bank and credit-card formats.

If future analytics need signed values, calculate them in SQL views or query expressions:

```text
signed_amount = case when direction = 'credit' then amount else -amount end
```

## 8. Money Representation

### Options Evaluated

### Float

Reject.

Reason:

- Floating-point values can introduce precision errors.
- Financial systems should not use binary floating point for stored money.

### Integer Minor Units

Viable, but not recommended for this MVP.

Pros:

- Exact.
- Efficient.
- Common in payment systems.

Cons:

- Requires currency exponent handling.
- Some currencies and financial products use more than two decimal places.
- Harder to inspect manually in SQL during a portfolio project.

### PostgreSQL NUMERIC/DECIMAL

Recommended.

Use:

```text
NUMERIC(19,4)
```

Reason:

- Exact decimal storage.
- Clear and readable in SQL.
- Well supported by PostgreSQL and SQLAlchemy.
- Suitable for personal finance analytics.
- Avoids float precision problems.
- Allows up to four decimal places for flexibility while supporting two-decimal display for INR/USD-like currencies.

### Final Decision

Store money as:

- `amount NUMERIC(19,4) not null`
- `balance NUMERIC(19,4) nullable`
- `currency CHAR(3) not null`

Application code should validate that `amount >= 0`. The sign should come from `direction`, not from a negative amount.

## 9. Date/Time Design

### Transaction Dates

Use `DATE`.

Reason:

- Statement transaction dates usually represent calendar dates, not exact instants.
- Time zone conversion should not shift a transaction into a different day.

### Value Dates

Use `DATE`, nullable.

Reason:

- Value date is also a financial calendar date.
- Not all statements provide it.

### Statement Period Dates

Use `DATE`, nullable:

- `statement_start_date`
- `statement_end_date`

### Upload And System Timestamps

Use `TIMESTAMPTZ`:

- `uploaded_at`
- `processing_started_at`
- `processing_finished_at`
- `created_at`
- `updated_at`

Reason:

- These are actual system events.
- They should be stored in UTC and displayed in the user's local timezone.

### Time Zone Policy

- Store system timestamps as UTC `TIMESTAMPTZ`.
- Store transaction dates as date-only values.
- Do not infer transaction timestamps unless the source document provides them.
- Display dates using the user's locale/timezone preferences later.
- For MVP, default UI display can use the user's browser locale while backend date filters remain explicit date ranges.

## 10. Multi-User Isolation

Multi-user isolation must be designed from the beginning, even if the first demo has one user.

### Ownership Model

Every user-owned table must include `user_id`:

- `financial_accounts.user_id`
- `documents.user_id`
- `transactions.user_id`
- `categories.user_id` for custom categories

### Enforcement Layers

Authorization should be enforced in:

- API dependencies: every protected route receives the current authenticated user.
- Service methods: all queries include `user_id` filters.
- Database constraints: foreign keys preserve ownership relationships.
- Tests: cross-user access should be tested before deployment.

### Access Rules

- A user can access only their own accounts.
- A user can access only their own documents.
- A user can access only their own transactions.
- Analytics queries must filter by `user_id`.
- Future RAG retrieval must filter by `user_id`.
- Future assistant tools must accept current-user context from the backend, not from the LLM.

### Important Design Rule

Do not trust IDs from the frontend by themselves. For example, when fetching a transaction by `transaction_id`, the query must include both:

```text
where id = :transaction_id and user_id = :current_user_id
```

## 11. Document Storage Design

### Option A: Store PDF Binary Data In PostgreSQL

Pros:

- Single persistence layer.
- Transactional metadata and file storage.

Cons:

- Database grows quickly.
- Backups become heavier.
- File streaming is less natural.
- Object lifecycle policies are harder.

Recommendation:

- Do not use this for MVP unless deployment constraints force it.

### Option B: Local Filesystem

Pros:

- Simple for development.
- Easy to inspect during debugging.
- No external storage dependency.
- Good fit for a local final-year demo.

Cons:

- Not suitable for scaled production.
- Requires careful path handling.
- Harder to deploy across multiple backend instances.

Recommendation:

- Use for development and MVP local demo.

### Option C: Object Storage

Pros:

- Production-ready.
- Scales well.
- Supports lifecycle rules.
- Works across multiple app instances.
- Can support signed URLs and encryption.

Cons:

- More setup.
- Requires credentials and secure configuration.

Recommendation:

- Use for production.

### Final Recommendation

MVP development:

- Store uploaded PDFs on the local filesystem outside public web directories.
- Store only metadata and a private `storage_key` in PostgreSQL.

Production:

- Store uploaded PDFs in S3-compatible object storage.
- Store `storage_backend`, `storage_key`, hash, size, MIME type, and metadata in PostgreSQL.

Security:

- Never store public file paths or public URLs in the database.
- Serve document downloads only through authenticated backend routes.

## 12. Document-Processing Architecture

The document pipeline should be stateful and observable.

### Processing Flow

```text
Upload
  -> validate file size and MIME type
  -> verify PDF structure
  -> compute SHA-256 hash
  -> store file
  -> create document record
  -> set status to queued or processing
  -> parse PDF text/tables
  -> detect scanned/unsupported PDF
  -> extract raw transaction rows
  -> normalize fields
  -> validate dates, amounts, direction, currency
  -> generate dedupe fingerprints
  -> detect duplicates
  -> insert transaction drafts
  -> assign initial categories
  -> set document status to needs_review or completed
```

### Where State Lives

Document-level state should live in `documents.status`.

Transaction-level review state should live in `transactions.review_status`.

Document-level errors should live in:

- `documents.error_code`
- `documents.error_message`

Detailed internal errors should go to logs, with sensitive data redacted.

### Recommended Document States

- `uploaded`: metadata exists, file accepted.
- `queued`: processing has been scheduled.
- `processing`: extraction is running.
- `needs_review`: transaction drafts were created and need user review.
- `completed`: import is complete.
- `failed`: processing failed or document is unsupported.

### Why `needs_review` Matters

Financial extraction is not reliable enough to silently import every row. `needs_review` makes uncertainty visible and supports the Phase 1 requirement that users can correct extracted transactions.

## 13. Transaction Deduplication Strategy

Deduplication should happen at two levels:

### Exact Document Deduplication

Use `documents.sha256_hash`.

Constraint:

- Unique `(user_id, sha256_hash)`.

This prevents importing the exact same PDF twice for one user.

### Transaction-Level Deduplication

Generate a `dedupe_fingerprint` from normalized transaction evidence.

Suggested fingerprint inputs:

- `account_id`
- `transaction_date`
- `amount`
- `direction`
- normalized description text
- `balance` if available

Possible fingerprint format:

```text
sha256(account_id + date + direction + amount + normalized_description + optional_balance)
```

Database constraint:

- Unique `(user_id, account_id, dedupe_fingerprint)` where fingerprint is not null.

### Overlapping Statements

Overlapping statements may include the same transaction with slightly different descriptions. The MVP should:

- Detect exact fingerprint matches automatically.
- Flag near-duplicates for review later.
- Avoid aggressive fuzzy deduplication in the first MVP because false positives can hide real transactions.

Future improvements:

- Fuzzy matching by date window, amount, merchant similarity, and balance continuity.
- User-confirmed duplicate resolution.

## 14. Category Design

### Options Evaluated

### Hard-Coded Enums

Reject as the primary model.

Reason:

- Too rigid.
- Hard to customize.
- Requires code changes for category changes.

### Database Records

Recommended.

Reason:

- Supports default categories.
- Supports future user customization.
- Enables category metadata such as colors and icons.
- Works naturally with analytics queries.

### User-Editable Records

Recommended for later, partially supported by schema now.

The categories table should support:

- Global system categories with `user_id = null`.
- Custom user categories with `user_id = user.id`.

### MVP Recommendation

Seed a small set of system categories. Allow users to assign or override categories on transactions. Full category-management UI can be simple or deferred.

Suggested MVP categories:

- Income
- Food and Dining
- Groceries
- Transport
- Shopping
- Bills and Utilities
- Rent or Housing
- Healthcare
- Entertainment
- Travel
- Education
- Transfers
- Fees and Charges
- Other

## 15. Analytics Architecture

Analytics should be deterministic and backend-owned.

### Recommended MVP Approach

Use SQL aggregations through backend analytics service methods.

Reason:

- PostgreSQL is strong at filtering, grouping, and aggregating transactions.
- SQL keeps calculations close to the source of truth.
- FastAPI/Python can validate filters and shape response DTOs.
- This avoids unnecessary Pandas dependencies for simple dashboard metrics.

### Use SQL For

- Total income.
- Total expenses.
- Savings.
- Savings rate.
- Monthly cash flow.
- Category totals.
- Month-over-month comparisons.
- Top merchants.

### Use Python For

- Request validation.
- Date range normalization.
- Response formatting.
- Combining multiple query results.
- Small derived values if easier and still deterministic.

### Use Pandas Later For

- More complex analysis.
- Forecasting prototypes.
- Offline reports.
- ML feature generation.

### Use Materialized Tables Later For

- Large datasets.
- Expensive repeated analytics.
- Scheduled monthly reports.
- Multi-year reporting at scale.

### MVP Analytics Rule

Analytics should default to:

```text
transactions.review_status = 'confirmed'
```

Draft or unreviewed transactions may be shown separately but should not silently affect trusted totals.

## 16. LLM Boundary

The LLM must sit behind a controlled service boundary.

### Forbidden Design

Do not allow:

```text
LLM -> raw SQL -> database
```

Do not allow:

```text
LLM reads all transactions -> calculates totals in text
```

### Required Design

Use a controlled tool/service approach:

```text
User question
  -> LLM intent interpretation
  -> approved financial tool selection
  -> backend service validates tool arguments
  -> backend service applies current user context
  -> deterministic SQL/Python calculation
  -> structured result returned to LLM
  -> LLM explains result in natural language
```

Example:

User asks:

```text
How much did I spend on food?
```

Correct flow:

```text
LLM identifies intent: category spending
LLM requests tool: get_category_spending(category='Food and Dining', date_range=...)
Backend validates category and date range
Backend filters by authenticated user_id
Backend runs SQL aggregation over confirmed transactions
Backend returns exact total and supporting rows/counts
LLM explains the result without recalculating it
```

### LLM Access Rules

- The LLM receives only the minimum result needed.
- Tool outputs should be structured.
- Tool arguments should be validated against schemas.
- The backend attaches `user_id`; the LLM cannot choose it.
- The LLM should not see secrets, raw database credentials, or unrestricted transaction exports.
- For sensitive queries, return summaries first and fetch detail only when needed.

## 17. RAG Architecture

RAG should be designed for future unstructured document questions, not MVP financial calculations.

### Future RAG Flow

```text
Document processed
  -> extract full document text
  -> split text into chunks
  -> store chunks with user_id, document_id, page range, chunk index
  -> generate embeddings
  -> store embeddings in pgvector
  -> user asks document question
  -> retrieve chunks filtered by user_id/document scope
  -> pass relevant chunks to LLM
  -> generate answer with citations
```

### Future document_chunks Table

Potential fields:

- `id`
- `user_id`
- `document_id`
- `page_start`
- `page_end`
- `chunk_index`
- `content`
- `embedding`
- `created_at`

Postpone this table until RAG work begins.

### Metadata Filtering

Every retrieval query must filter by:

- `user_id`
- optionally `document_id`
- optionally document type or statement period

The LLM must not retrieve across users.

### Structured Queries vs Unstructured Queries

Structured financial queries:

- "How much did I spend on groceries last month?"
- "What was my savings rate in August?"
- "Which merchant did I spend the most on?"

These should use analytics tools over structured transactions.

Unstructured document queries:

- "What does this statement say about late payment fees?"
- "Where is the interest charge explanation?"
- "Which page mentions my reward points?"

These may use RAG over document chunks with citations.

### Citation Requirement

RAG answers should cite:

- source document
- page number
- chunk or text location if available

## 18. Security Architecture

Security must influence the architecture now, even if advanced compliance features wait.

### Authentication

- Use secure email/password authentication for MVP.
- Store only password hashes.
- Use secure session/JWT handling.
- Protect all financial routes.

### Authorization

- Enforce `user_id` ownership on every data access.
- Never trust frontend-provided IDs alone.
- Apply authorization in service layer, not only at route layer.

### Password Hashing

- Use Argon2id if practical.
- bcrypt is acceptable if Argon2id setup is not chosen.
- Never use plain SHA hashes for passwords.

### Secure File Handling

- Validate file extension and MIME type.
- Verify PDF structure.
- Set file-size limits.
- Store files outside public directories.
- Use generated storage keys, not user-provided filenames.
- Do not execute or render uploaded PDFs server-side in unsafe contexts.

### MIME And File Validation

- Accept only PDFs for MVP.
- Reject unexpected MIME types.
- Handle parser failures safely.
- Treat PDFs as untrusted input.

### File-Size Limits

- Set a practical MVP upload limit, for example 10 MB or 20 MB.
- Make the limit configurable.

### User-Data Isolation

- All user-owned database records include `user_id`.
- All file storage keys should be scoped by user or generated with unguessable identifiers.
- Document downloads should go through authorized backend routes.

### Secret Management

- Use environment variables for development.
- Use a secret manager or platform secrets in production.
- Never commit secrets.

### Log Redaction

- Avoid logging raw transaction descriptions, account numbers, full document text, or file contents.
- Log internal IDs and error codes instead.
- Redact sensitive values before logging.

### LLM Data Minimization

- Do not send full documents or full transaction histories unless absolutely necessary.
- Prefer sending deterministic summary results.
- For RAG, send only retrieved chunks filtered by user.

### Prompt-Injection Risk

Uploaded documents are untrusted and may contain malicious text.

Future assistant/RAG design must:

- Treat document text as data, not instructions.
- Keep system/tool instructions separate from retrieved content.
- Prevent retrieved text from changing tool permissions.

### Database Permissions

- Use a least-privilege application database user.
- Do not use superuser credentials in the app.
- Restrict migration credentials separately if possible.

## 19. API Architecture

The API should use REST for the MVP. Keep endpoint groups resource-oriented.

### MVP Endpoint Groups

### /auth

Likely responsibilities:

- Register.
- Login.
- Logout/session handling.
- Current user.

### /users

Likely responsibilities:

- Get profile.
- Update profile basics.
- Future data export/delete.

### /accounts

Likely responsibilities:

- Create account.
- List accounts.
- Update account.
- Archive/delete account if safe.

### /documents

Likely responsibilities:

- Upload PDF.
- List documents.
- Get document detail.
- Get processing status.
- Get processing errors.
- Retry processing later.

### /transactions

Likely responsibilities:

- List transactions.
- List document transaction drafts.
- Update transaction fields.
- Confirm transactions.
- Exclude transactions.
- Filter by date, account, category, direction.

### /categories

Likely responsibilities:

- List categories.
- Create custom category later.
- Update category later.

### /analytics

Likely responsibilities:

- Summary metrics.
- Monthly cash flow.
- Category spending.
- Merchant totals.
- Month-over-month comparisons.

### Future Endpoint Groups

### /assistant

For natural-language questions, tool orchestration, and answer history.

### /search

For RAG/document search.

### /goals

For financial planning goals.

### /reports

For generated monthly reports and exports.

## 20. Background Processing

### Synchronous Processing

Pros:

- Simpler.
- Easier to debug.
- No worker infrastructure.

Cons:

- Upload requests can time out.
- Bad user experience for larger files.
- Harder to retry cleanly.

### Asynchronous Worker/Queue

Pros:

- Better user experience.
- Supports progress/status polling.
- Easier retries.
- Scales document parsing separately later.

Cons:

- More moving parts.
- Requires queue setup.
- Adds deployment complexity.

### MVP Recommendation

Use a staged approach:

1. For early local development, allow simple in-process background processing after the document record is created.
2. Keep the document status model compatible with a real queue.
3. Move to Redis with RQ, Celery, or another worker when parsing becomes slow, unreliable, or needs retries.

Do not block the architecture on Celery from day one unless sample PDFs are already large or OCR is required.

### When Redis/Celery/RQ Becomes Justified

Add a real worker queue when:

- PDF processing frequently exceeds a few seconds.
- OCR is added.
- Multiple users may upload at the same time.
- Retry and failure handling become important.
- Processing progress needs better observability.
- Deployment uses multiple backend instances.

RQ is simpler for MVP-style Python jobs. Celery is more powerful but heavier. Either is acceptable later; choose when requirements are clearer.

## 21. Error And Processing-State Model

### Document States

Recommended states:

- `uploaded`
- `queued`
- `processing`
- `needs_review`
- `completed`
- `failed`

### Optional Later States

- `unsupported`
- `partially_completed`
- `duplicate`
- `cancelled`

For MVP, avoid too many states. Use `failed` with clear `error_code` for unsupported documents if necessary.

### Error Storage

Use:

- `documents.error_code`
- `documents.error_message`

Examples:

- `invalid_file_type`
- `file_too_large`
- `encrypted_pdf`
- `scanned_pdf_unsupported`
- `no_transactions_found`
- `unsupported_statement_layout`
- `parser_error`
- `duplicate_document`

Frontend behavior:

- Show user-safe `error_message`.
- Offer retry only when retry is meaningful.
- Suggest review when extraction is partial or low-confidence.

Internal logs:

- Keep stack traces and debugging detail out of user-facing fields.
- Redact sensitive document and transaction content.

## 22. ER Diagram

```text
+------------------+       1     *       +----------------------+
| User             |--------------------->| FinancialAccount     |
|------------------|                      |----------------------|
| id PK            |                      | id PK                |
| email            |                      | user_id FK           |
| password_hash    |                      | account_type         |
| default_currency |                      | display_name         |
+--------+---------+                      | currency             |
         |                                +----------+-----------+
         | 1                                         |
         |                                           | 1
         | *                                         | *
         v                                           v
+--------+---------+                      +----------+-----------+
| Document         |                      | Transaction          |
|------------------|                      |----------------------|
| id PK            |      1        *      | id PK                |
| user_id FK       |--------------------->| document_id FK null  |
| account_id FK    |                      | user_id FK           |
| document_type    |                      | account_id FK        |
| storage_key      |                      | category_id FK null  |
| sha256_hash      |                      | transaction_date     |
| status           |                      | amount               |
+------------------+                      | direction            |
                                          | currency             |
                                          | review_status        |
                                          +----------+-----------+
                                                     ^
                                                     | *
                                                     | 1
                                          +----------+-----------+
                                          | Category             |
                                          |----------------------|
                                          | id PK                |
                                          | user_id FK nullable  |
                                          | parent_category_id FK|
                                          | name                 |
                                          | type                 |
                                          | is_system            |
                                          +----------------------+
```

Relationship summary:

- One user has many financial accounts.
- One user has many documents.
- One user has many transactions.
- One financial account has many documents.
- One financial account has many transactions.
- One document has many transactions.
- One category has many transactions.
- Categories may be global system categories or user-owned custom categories.

## Phase 1 Conflict Check

No Phase 1 requirement conflicts with a sound Phase 2 engineering decision.

There are two refinements worth locking:

- Phase 1 listed `category` as an expected transaction field. In the database, `category_id` should be nullable because extraction and categorization can be uncertain, and uncategorized transactions must still be reviewable.
- Phase 1 listed future transaction fields such as `is_recurring` and `is_anomaly`. Phase 2 intentionally postpones them because storing feature flags before those detection systems exist would create misleading data.

## 23. Request/Data-Flow Examples

### A. User Uploads A Statement

```text
Frontend
  -> user selects PDF and account/document type
  -> POST /documents/upload

Backend API
  -> authenticates user
  -> validates file size, MIME type, PDF structure
  -> computes SHA-256 hash
  -> checks duplicate document hash for this user
  -> stores PDF in local filesystem or object storage
  -> creates documents row with status uploaded/queued
  -> starts processing

Processing Pipeline
  -> parses PDF text/tables
  -> extracts transaction rows
  -> normalizes transaction fields
  -> validates required values
  -> generates dedupe fingerprints
  -> creates transaction draft rows with review_status needs_review
  -> updates document status to needs_review, completed, or failed

Frontend
  -> polls or refreshes document status
  -> shows review screen for extracted transactions
```

### B. User Views Monthly Spending Analytics

```text
Frontend
  -> GET /analytics/monthly-spending?month=2026-08

Backend API
  -> authenticates user
  -> validates date range
  -> calls analytics service

Analytics Service
  -> queries PostgreSQL
  -> filters by current user_id
  -> includes review_status = confirmed
  -> groups debit transactions by category/month
  -> calculates totals deterministically

Backend API
  -> returns structured JSON

Frontend
  -> renders charts and summary values
```

### C. Future User Asks: "Why Did I Spend More This Month?"

```text
Frontend Assistant UI
  -> sends question to /assistant

AI Service
  -> interprets intent as month-over-month expense comparison
  -> selects approved tool: compare_monthly_spending
  -> does not query database directly

Analytics Tool
  -> receives validated month parameters
  -> backend attaches current user_id
  -> runs deterministic SQL:
       current month expenses
       previous month expenses
       category deltas
       merchant deltas
  -> returns structured result:
       total change
       top contributing categories
       top contributing merchants
       supporting transaction counts

AI Service
  -> receives deterministic result
  -> writes natural-language explanation
  -> may cite categories/merchants returned by tool
  -> does not invent extra calculations

Frontend
  -> displays answer and links to analytics/transactions
```

This keeps calculation and explanation separate.

## 24. Technology Decisions

The proposed stack is sound for this project. No major changes are recommended.

### Frontend

Use:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

Reason:

- Strong ecosystem.
- Good dashboard support.
- TypeScript improves API contract reliability.
- shadcn/ui and Tailwind support a polished UI without building a design system from scratch.
- Recharts is sufficient for MVP analytics charts.

### Backend

Use:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

Reason:

- Python is strong for PDF extraction, data processing, and future ML.
- FastAPI is suitable for typed APIs and modular monolith design.
- Pydantic provides validation boundaries.
- SQLAlchemy and Alembic are mature for PostgreSQL-backed apps.

### Database

Use:

- PostgreSQL
- pgvector later

Reason:

- PostgreSQL is reliable for relational financial records.
- It supports strong indexing, constraints, exact decimal values, and analytics queries.
- pgvector can be added later without introducing a separate vector database during early phases.

### Document Processing

Use:

- PyMuPDF
- pdfplumber
- Pandas where useful

Reason:

- PyMuPDF is fast and useful for text extraction and document inspection.
- pdfplumber is strong for table extraction from PDFs.
- Pandas can help during parsing experiments and later reporting, but should not be required for simple analytics.

### AI

Use later:

- Provider abstraction.
- LLM API behind controlled backend tools.

Reason:

- Avoid locking the app to one AI provider too early.
- Keep deterministic financial logic separate.

### Testing

Use:

- pytest
- HTTPX
- Playwright later

Reason:

- pytest is the natural backend test choice.
- HTTPX is good for FastAPI endpoint tests.
- Playwright is useful once real frontend workflows exist.

### Infrastructure

Use:

- Docker.
- Docker Compose.

Reason:

- Good for local PostgreSQL and reproducible development.
- Keeps final-year demo setup manageable.

Scope note:

- Do not generate Docker files in Phase 2. This is only a technology decision.

## 25. Architecture Decision Records

### ADR-001: Use PostgreSQL As Primary Database

Decision:

- Use PostgreSQL as the primary database for users, accounts, documents, transactions, categories, and analytics source data.

Reason:

- ArthaDrishti needs relational integrity, exact numeric support, indexing, constraints, and deterministic aggregations.

Alternatives considered:

- SQLite.
- MongoDB.
- Separate analytics database.

Consequences:

- Stronger production path and better financial data modeling.
- Requires PostgreSQL setup in development.
- Enables pgvector later.

### ADR-002: Use Modular Monolith For MVP

Decision:

- Build the MVP as a modular monolith.

Reason:

- The domain boundaries are still stabilizing.
- One backend service is easier to build, test, deploy, and demo.
- Microservices would add premature operational complexity.

Alternatives considered:

- Microservices.
- Serverless-only architecture.

Consequences:

- Faster MVP delivery.
- Modules must still maintain clean boundaries to avoid becoming tangled.
- Future extraction/AI/ML services can be split later.

### ADR-003: Use FastAPI For Backend

Decision:

- Use Python with FastAPI for the backend API.

Reason:

- Python fits document parsing, financial analytics, and future ML.
- FastAPI provides typed request/response boundaries and good developer velocity.

Alternatives considered:

- Django.
- Node.js/Express.
- Java/Spring.

Consequences:

- Need deliberate structure for modularity.
- Works well with SQLAlchemy, Pydantic, pytest, and document-processing libraries.

### ADR-004: Use Next.js With TypeScript For Frontend

Decision:

- Use Next.js, React, and TypeScript for the frontend.

Reason:

- Good fit for dashboards, forms, authenticated pages, and future assistant UI.
- TypeScript reduces API integration mistakes.

Alternatives considered:

- Vite React.
- Plain React SPA.
- Server-rendered templates.

Consequences:

- Slightly more framework complexity than Vite.
- Strong path for polished portfolio presentation.

### ADR-005: Store Money As PostgreSQL NUMERIC

Decision:

- Store monetary values as `NUMERIC(19,4)` with a separate `currency CHAR(3)`.

Reason:

- Financial precision matters.
- Floats are unsafe for money.
- NUMERIC is exact and readable.

Alternatives considered:

- Floating point.
- Integer minor units.

Consequences:

- Slightly less compact than integers.
- Easier SQL inspection and aggregation for this project.

### ADR-006: Store Amount As Positive Value Plus Direction

Decision:

- Store `amount` as a positive decimal and store debit/credit separately in `direction`.

Reason:

- Source statements vary in sign conventions.
- Separating value from direction avoids double-negative mistakes.

Alternatives considered:

- Signed amount only.
- Both signed amount and direction.

Consequences:

- Queries must calculate signed values when needed.
- Model is easier to reason about across banks and credit cards.

### ADR-007: Store PDFs Outside PostgreSQL

Decision:

- Store PDF files in local filesystem for development/MVP demo and object storage in production. Store metadata and storage references in PostgreSQL.

Reason:

- Keeps the database focused on structured data.
- Object storage is better for production file handling.

Alternatives considered:

- Store PDF binary data directly in PostgreSQL.

Consequences:

- Need careful storage key and authorization design.
- Easier backup, lifecycle, and scaling later.

### ADR-008: Use SQL-Backed Deterministic Analytics

Decision:

- Implement MVP analytics using SQL aggregations through backend service methods.

Reason:

- Financial numbers must come from deterministic calculations over confirmed transactions.

Alternatives considered:

- LLM-generated calculations.
- Pandas-only analytics.
- Precomputed materialized tables from day one.

Consequences:

- Backend owns financial truth.
- Materialized analytics can be added later if needed.

### ADR-009: Keep LLM Behind Approved Tools

Decision:

- Future LLM features must call approved backend tools instead of directly querying the database.

Reason:

- Prevents hallucinated calculations, data leaks, and unsafe database access.

Alternatives considered:

- Give LLM raw database access.
- Send full transaction exports to the LLM.

Consequences:

- Requires tool schemas and validation.
- Stronger trust and security model.

### ADR-010: Defer RAG, ML, Forecasting, And Agents From MVP

Decision:

- Do not implement RAG, anomaly detection, recurring detection, forecasting, or multi-agent workflows in the MVP.

Reason:

- These features depend on clean confirmed transaction data.
- Implementing them early would dilute the core proof.

Alternatives considered:

- Build assistant/RAG first.

Consequences:

- MVP stays focused and achievable.
- Architecture still leaves clear future extension points.

## 26. Phase 2 Deliverables

### Final High-Level Architecture

- Modular monolith.
- Next.js frontend.
- FastAPI backend.
- PostgreSQL primary database.
- Local filesystem storage for development.
- Object storage for production.
- SQL-backed analytics service.
- Bounded future AI/RAG/ML layers.

### Final Database Entity List

- User.
- FinancialAccount.
- Document.
- Transaction.
- Category.

### Final MVP Table List

- `users`
- `financial_accounts`
- `documents`
- `transactions`
- `categories`

### Final Technology Stack

Frontend:

- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- shadcn/ui.
- Recharts.

Backend:

- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.

Database:

- PostgreSQL.
- pgvector later.

Document processing:

- PyMuPDF.
- pdfplumber.
- Pandas where useful.

AI:

- Provider abstraction later.
- Controlled LLM tool layer later.

Testing:

- pytest.
- HTTPX.
- Playwright later.

Infrastructure:

- Docker.
- Docker Compose.

### Backend Module Boundaries

- `auth`: identity and sessions.
- `users`: profile and user-level settings.
- `accounts`: financial accounts.
- `documents`: upload metadata and lifecycle.
- `document_processing`: parsing, extraction, normalization, deduplication.
- `transactions`: normalized transaction records and review.
- `categories`: category records and assignment support.
- `analytics`: deterministic SQL-backed metrics.
- `ai`: future LLM provider and tool orchestration.
- `rag`: future document chunking, embeddings, retrieval.
- `ml`: future recurring/anomaly/forecasting logic.
- `security`: shared security utilities.
- `audit`: future action logging.

### Frontend Page/Module List

MVP:

- Authentication.
- Dashboard.
- Documents.
- Transaction review.
- Transactions list.
- Basic analytics widgets.
- Minimal settings/account menu.

Deferred:

- Assistant.
- RAG document search.
- Goals.
- Reports.
- Advanced category management.

### Security Boundaries

- Authenticated access required for financial data.
- User ownership enforced in every API/service/database query.
- Uploaded files treated as untrusted.
- Files stored outside public paths.
- Sensitive logs redacted.
- Secrets managed outside source control.
- Future LLM access limited to approved tools.
- Future RAG retrieval filtered by user and document metadata.

### Deferred Architecture Items

- pgvector and `document_chunks`.
- Conversations and messages.
- Budgeting.
- Financial goals.
- Recurring-transaction model.
- Anomaly model.
- Forecasting pipeline.
- Full audit logs.
- OCR pipeline.
- Dedicated background worker.
- Microservices.
- Multi-agent orchestration.

## 27. Phase 2 Completion Checklist

- [ ] Overall system architecture is documented.
- [ ] ASCII architecture diagram is included.
- [ ] Modular monolith decision is documented.
- [ ] Conditions for future service splitting are documented.
- [ ] Backend module boundaries are defined.
- [ ] Frontend areas/pages are defined.
- [ ] MVP database entities are identified.
- [ ] Deferred database tables are identified.
- [ ] MVP table definitions are documented.
- [ ] Transaction data model is documented in detail.
- [ ] Money representation decision is documented.
- [ ] Date/time design is documented.
- [ ] Multi-user isolation strategy is documented.
- [ ] Document storage strategy is documented for development and production.
- [ ] Document-processing flow is documented.
- [ ] Processing states and error model are documented.
- [ ] Transaction deduplication strategy is documented.
- [ ] Category design is documented.
- [ ] Analytics architecture is documented.
- [ ] LLM boundary is documented.
- [ ] Future RAG architecture is documented.
- [ ] Security architecture is documented.
- [ ] REST API resource groups are documented.
- [ ] Background processing recommendation is documented.
- [ ] MVP ER diagram is included.
- [ ] Request/data-flow examples are included.
- [ ] Technology stack is confirmed or challenged.
- [ ] ADRs are documented.
- [ ] Phase 2 deliverables are summarized.
- [ ] No Phase 3 implementation has started.
