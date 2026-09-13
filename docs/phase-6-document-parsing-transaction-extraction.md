# ArthaDrishti: Phase 6 Document Parsing & Transaction Extraction

Phase 6 converts supported uploaded PDF statements into a structured intermediate transaction representation. It does not create final transaction tables, categorize transactions, calculate analytics, use RAG, create embeddings, call LLMs, run anomaly detection, or implement OCR.

## Supported Format

Phase 6 originally supported one safe synthetic text-based statement format:

```text
ARTHADRISHTI SYNTHETIC BANK STATEMENT
Date | Value Date | Description | Debit | Credit | Balance
```

The parser registry now also supports a generic text-based bank statement table:

```text
Transaction Details
Date | Description | Debit (INR) | Credit (INR) | Balance (INR)
```

Generic parser detection is content-based. It requires the `Date`, `Description`, `Debit`, `Credit`, and `Balance` header signals plus at least one valid transaction-like row. Filename is not used for parser selection.

The generic parser maps rows into the same intermediate transaction model as the synthetic parser. `OPENING BALANCE` rows are preserved as statement metadata when possible and skipped as normal financial transactions.

The fixture is intentionally synthetic and generated inside automated tests. No personal bank statement is committed to the repository.

Why this choice:

- It is safe for source control and automated testing.
- Exact expected transactions can be asserted field by field.
- The parser architecture can support real bank formats later.
- It avoids pretending the system supports every Indian bank too early.

## Parser Architecture

Phase 6 adds a small parser boundary under `backend/app/parsing`.

Core pieces:

- `StatementParser`: abstract parser interface.
- `ParserMatch`: parser selection result.
- `SyntheticBankStatementParser`: concrete parser for the original synthetic fixture format.
- `GenericBankStatementParser`: concrete parser for generic five-column bank statement tables.
- `select_parser`: tiny registry that picks the best matching parser.
- `extract_pdf_text`: PyMuPDF-based text extraction.
- `parse_user_document`: document-level parsing service and status integration.

This is not a dynamic plugin framework. It is deliberately small: add future parsers by adding classes and registering them explicitly. Unsupported PDFs still fail safely with `unsupported_statement_format` instead of being guessed.

## PDF Extraction Strategy

Selected library:

- PyMuPDF

Reason:

- Fast text extraction for text-based PDFs.
- Can detect encrypted/password-protected PDFs.
- Can generate synthetic PDFs in tests.
- Avoids OCR and heavier table tooling until real statement formats require them.

OCR boundary:

- OCR is not part of the normal Phase 6 path.
- Textless PDFs fail safely with `ocr_required`.
- PDFs with too little text fail safely with `no_extractable_text`.

PDF safety boundary:

- Uploaded PDFs are untrusted input.
- The backend only reads content through PyMuPDF APIs.
- The parser does not execute embedded scripts.
- The parser does not follow embedded external actions.
- The backend does not shell out with untrusted filenames.

## Parsing Pipeline

```text
Document record
  -> resolve private storage key
  -> verify stored file exists
  -> extract PDF text
  -> detect password/textless failures
  -> select parser
  -> extract statement metadata
  -> detect transaction rows
  -> join continuation description lines
  -> parse date, amount, direction, balance
  -> validate rows
  -> run balance consistency checks
  -> return intermediate parse result
  -> update document processing status
```

## Intermediate Transaction Model

`ExtractedTransaction` contains:

- `transaction_date`
- `value_date`
- `raw_description`
- `amount`
- `direction`
- `balance`
- `raw_debit`
- `raw_credit`
- `source_page`
- `source_row`
- `extraction_confidence`
- `warnings`

Deferred:

- category
- merchant normalization
- recurring flags
- anomaly flags
- final transaction IDs
- database persistence

## Money Rules

Money is parsed deterministically using `Decimal`, never `float`.

Supported examples:

- `1,234.56`
- `₹1,234.56`
- `1234.56`
- `1,00,000.00`
- `500`
- blank debit/credit cells when the opposite column is present

Malformed values become parser errors such as `invalid_amount`.

Canonical model:

```text
amount = positive Decimal
direction = debit | credit
```

Reason:

- Bank statements vary in sign conventions.
- A positive amount plus direction is consistent across parsers.
- It avoids mixing signed amounts from one parser with positive amounts from another.

## Date Rules

Phase 6 supports deterministic day-first formats needed by the synthetic fixture:

- `DD/MM/YYYY`
- `DD-MM-YYYY`

It does not guess between Indian and US date conventions. Invalid dates become `invalid_date` errors.

## Multi-Line Descriptions

The synthetic parser supports continuation lines after a valid transaction row. A line is appended to the previous row description only when:

- it is not a page/header/footer/metadata line
- it does not start a new transaction row
- a current transaction row exists

This keeps headers, footers, account metadata, and generated-on text out of descriptions.

## Metadata Extraction

The supported parser extracts metadata only when reliable:

- bank name
- masked account number
- statement start date
- statement end date
- opening balance
- closing balance
- currency

The parser does not infer full account numbers. The fixture uses a masked account identifier.

## Result Schema

The top-level parse result contains:

- `parser_name`
- `parser_version`
- `document_id`
- `status`
- `metadata`
- `transactions`
- `warnings`
- `errors`

The API response returns:

- document ID
- document processing status
- parser name/version
- result status
- transaction count
- warning count
- error count
- safe warnings/errors
- first five extracted transactions as a preview

The full result is not persisted in Phase 6. Phase 7 will own final transaction storage.

## Validation Rules

Row-level checks:

- transaction date exists and parses
- description is not empty
- exactly one of debit/credit is present
- amount is positive
- direction is valid
- balance parses if present

Statement-level checks:

- at least one transaction must be extracted
- opening/closing balance parse if present
- running balances are checked when balance semantics are clear

Partial parsing:

- One malformed row does not discard valid rows.
- Documents with valid rows plus row errors return `partial_success`.
- The document status becomes `completed` when useful transactions were extracted.

## Confidence Model

The confidence score is simple and rule-based:

- `1.0` for rows that match the expected pattern with date, amount, direction, description, and balance.
- `0.9` when a row is otherwise valid but balance is missing.

This is not an ML confidence score. Structured warnings/errors remain the primary signal.

## Error Model

Implemented parser error codes include:

- `unsupported_statement_format`
- `pdf_text_extraction_failed`
- `no_extractable_text`
- `ocr_required`
- `password_protected_pdf`
- `no_transactions_found`
- `malformed_transaction_row`
- `invalid_amount`
- `invalid_date`
- `ambiguous_direction`
- `empty_description`
- `missing_document_file`

Errors returned to the frontend are safe messages. Stack traces, internal paths, and raw PDF text are not exposed.

## Processing Status Integration

Phase 5 status model is reused:

```text
ready_for_processing
  -> processing
  -> completed

ready_for_processing
  -> processing
  -> failed
```

Meaning:

- `ready_for_processing`: upload succeeded, not parsed yet.
- `processing`: parser is running in the request.
- `completed`: parser extracted useful intermediate transactions.
- `failed`: parser could not extract transactions safely.

Repeated parsing is allowed. A repeated call reruns parsing from the stored PDF and updates the latest status.

## Parsing Trigger

Phase 6 uses an explicit endpoint:

```text
POST /api/v1/documents/{document_id}/parse
```

Reason:

- Upload remains separate from parsing.
- Parser failures are easier to debug.
- No Redis/Celery/background worker is needed for small text-based PDFs.
- The status model remains compatible with a later worker queue.

## Frontend Integration

The protected `/documents` page now shows:

- current processing status
- `Process` button per document
- safe failed status reason
- parse summary
- transaction count
- first five extracted transactions as a preview

The frontend does not display raw PDF text or full extracted statement content.

## Performance Boundary

Synchronous parsing is acceptable for Phase 6 because:

- upload size is limited
- OCR is not implemented
- only modest text-based PDFs are supported

A background worker becomes justified later when:

- parsing takes multiple seconds regularly
- OCR is added
- retries/progress tracking are needed
- multiple users process files concurrently
- deployment uses multiple backend instances

## Verification Results

| Verification | Result |
| --- | --- |
| Existing Phase 5 tests | Passed |
| PostgreSQL healthy | Passed |
| Alembic current | Passed: `20260909_0002 (head)` |
| Backend starts | Passed |
| Supported sample uploaded | Passed |
| Parsing triggered | Passed |
| Correct parser selected | Passed: `synthetic_bank_statement` |
| Exact transaction count | Passed: `7` |
| Debit rows verified | Passed |
| Credit rows verified | Passed |
| Decimal precision verified | Passed |
| Date parsing verified | Passed |
| Description continuation verified | Passed |
| Balance consistency verified | Passed |
| Unsupported valid PDF | Passed: `unsupported_statement_format` |
| Textless/scanned-like PDF | Passed: `ocr_required` |
| Password-protected PDF | Passed in automated tests |
| Second-user ownership isolation | Passed: `404` |
| Parser unit tests | Passed |
| Integration tests | Passed |
| Full backend suite | Passed: `47 passed` |
| Frontend process action | Passed |
| Frontend failure messaging | Passed |
| Frontend lint | Passed |
| Frontend build | Passed |
| Manual synthetic data cleanup | Passed |

## File Summary

| File | New/Modified | Purpose | Important details |
| --- | --- | --- | --- |
| `README.md` | Modified | Main project guide | Updated to Phase 6 parsing support, limits, parse endpoint, and security notes |
| `backend/pyproject.toml` | Modified | Backend dependencies | Adds `PyMuPDF` only |
| `backend/app/parsing/__init__.py` | New | Parser package marker | Keeps parsing separate from document CRUD |
| `backend/app/parsing/base.py` | New | Parser interface | Defines `StatementParser` and `ParserMatch` |
| `backend/app/parsing/dates.py` | New | Date parsing | Day-first deterministic formats only |
| `backend/app/parsing/exceptions.py` | New | Parser errors | Structured safe parser error details |
| `backend/app/parsing/money.py` | New | Money parsing | Uses `Decimal`, rejects malformed/negative values |
| `backend/app/parsing/pdf.py` | New | PDF text extraction | Uses PyMuPDF, detects encrypted/textless PDFs |
| `backend/app/parsing/registry.py` | New | Parser selection | Tiny explicit registry |
| `backend/app/parsing/synthetic_bank.py` | New | First parser | Supports synthetic bank statement rows, metadata, continuations, balance checks |
| `backend/app/schemas/parsing.py` | New | Parse schemas | Intermediate transaction/result/response models |
| `backend/app/schemas/__init__.py` | Modified | Schema exports | Exposes parser schemas |
| `backend/app/services/document_storage.py` | Modified | Storage service | Adds safe read-path resolution for parsing |
| `backend/app/services/document_parsing.py` | New | Parsing service | Owner-scoped parse workflow and status transitions |
| `backend/app/api/v1/routes/documents.py` | Modified | Document routes | Adds `POST /documents/{id}/parse` |
| `backend/tests/fixtures/__init__.py` | New | Fixture package | Synthetic fixtures only |
| `backend/tests/fixtures/statements.py` | New | Synthetic PDFs | Generates supported, unsupported, textless, malformed, password-protected PDFs |
| `backend/tests/test_parser_units.py` | New | Parser unit tests | Exact money/date/parser behavior |
| `backend/tests/test_document_parsing.py` | New | Parse integration tests | Auth, owner isolation, status, unsupported/textless/password/missing-file behavior |
| `frontend/src/lib/api.ts` | Modified | Frontend API client | Adds parse response types and `parseDocument` |
| `frontend/src/app/documents/page.tsx` | Modified | Documents UI | Adds Process action, status labels, safe parse summary and preview |
| `docs/phase-6-document-parsing-transaction-extraction.md` | New | Phase 6 report | Architecture, rules, verification, viva notes, checklist |

## Relevant Project Tree

Generated folders such as `.venv`, `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, `.pytest_tmp`, egg-info, private storage files, and actual uploaded PDFs are omitted.

```text
.
|-- README.md
|-- docker-compose.yml
|-- backend
|   |-- .env.example
|   |-- alembic.ini
|   |-- pyproject.toml
|   |-- alembic
|   |   `-- versions
|   |       |-- 20260909_0001_create_users_table.py
|   |       `-- 20260909_0002_create_documents_table.py
|   |-- app
|   |   |-- api
|   |   |   |-- deps.py
|   |   |   `-- v1
|   |   |       |-- router.py
|   |   |       `-- routes
|   |   |           |-- auth.py
|   |   |           |-- documents.py
|   |   |           `-- users.py
|   |   |-- core
|   |   |   |-- config.py
|   |   |   `-- security.py
|   |   |-- db
|   |   |   |-- base.py
|   |   |   |-- health.py
|   |   |   `-- session.py
|   |   |-- models
|   |   |   |-- document.py
|   |   |   `-- user.py
|   |   |-- parsing
|   |   |   |-- __init__.py
|   |   |   |-- base.py
|   |   |   |-- dates.py
|   |   |   |-- exceptions.py
|   |   |   |-- money.py
|   |   |   |-- pdf.py
|   |   |   |-- registry.py
|   |   |   `-- synthetic_bank.py
|   |   |-- schemas
|   |   |   |-- auth.py
|   |   |   |-- document.py
|   |   |   |-- parsing.py
|   |   |   `-- user.py
|   |   `-- services
|   |       |-- document_parsing.py
|   |       |-- document_storage.py
|   |       |-- documents.py
|   |       `-- users.py
|   `-- tests
|       |-- conftest.py
|       |-- fixtures
|       |   |-- __init__.py
|       |   `-- statements.py
|       |-- test_auth.py
|       |-- test_document_parsing.py
|       |-- test_documents.py
|       |-- test_health.py
|       `-- test_parser_units.py
|-- frontend
|   |-- package.json
|   `-- src
|       |-- app
|       |   |-- dashboard
|       |   |   `-- page.tsx
|       |   |-- documents
|       |   |   `-- page.tsx
|       |   |-- login
|       |   |   `-- page.tsx
|       |   `-- register
|       |       `-- page.tsx
|       `-- lib
|           |-- api.ts
|           `-- auth.ts
`-- docs
    |-- phase-1-project-planning-requirements.md
    |-- phase-2-system-architecture-database-design.md
    |-- phase-3-development-environment-project-setup.md
    |-- phase-4-authentication-user-foundation.md
    |-- phase-5-financial-document-upload-system.md
    `-- phase-6-document-parsing-transaction-extraction.md
```

## Viva Explanation

### Why don't we send the whole bank statement directly to an LLM?

We do not send the whole bank statement directly to an LLM because financial extraction must be deterministic, private, testable, and numerically correct. An LLM may misread a row, skip a line, invent a value, or calculate totals inconsistently. It also increases cost and privacy exposure because bank statements contain sensitive personal financial data. A deterministic parser lets us write exact tests for dates, amounts, debit/credit direction, balances, and errors. Later, an LLM can explain verified results, but it should not be the source of truth for financial numbers.

### How does the parser convert different layouts into one common transaction format?

Each statement parser understands one source layout. It reads that layout's columns or markers, then maps them into a shared intermediate model. For example, one bank may have separate Debit and Credit columns, another may use signed amounts, and another may use DR/CR labels. The parser-specific logic converts those differences into the common rule: `amount` is always a positive `Decimal`, and `direction` says whether the transaction is debit or credit. Future parsers can differ internally while producing the same `ExtractedTransaction` shape.

## Deferred To Phase 7

- final transaction database table
- source-document-to-transaction persistence
- transaction-level deduplication
- review/import workflow
- categorization
- merchant normalization
- analytics
- financial dashboard metrics

## Phase 6 Completion Checklist

- [x] Existing Phase 5 implementation reviewed.
- [x] Parser abstraction exists.
- [x] At least one statement format is reliably supported.
- [x] Supported format is synthetic and safe for tests.
- [x] Text extraction works.
- [x] PyMuPDF selected and documented.
- [x] OCR is not implemented.
- [x] Textless/scanned PDFs fail safely.
- [x] Password-protected PDFs fail safely.
- [x] Dates parse deterministically.
- [x] Amounts use `Decimal`.
- [x] Debit/credit normalize consistently.
- [x] Transaction rows are extracted correctly.
- [x] Multi-line descriptions are handled for the supported format.
- [x] Header/footer noise is excluded.
- [x] Statement metadata is extracted where reliable.
- [x] Parser errors are structured.
- [x] Unsupported layouts fail safely.
- [x] Processing status integrates with documents.
- [x] Explicit parse endpoint exists.
- [x] Full parse-result persistence is deferred.
- [x] Authenticated ownership is enforced.
- [x] Exact extraction tests exist.
- [x] Parser unit tests pass.
- [x] Integration tests pass.
- [x] Existing auth/upload tests still pass.
- [x] Frontend can trigger processing.
- [x] Frontend displays status/errors safely.
- [x] README updated.
- [x] Phase 6 report created.
- [x] No final transaction storage has been added.
- [x] No categorization has been started.
- [x] No analytics has been started.
- [x] No RAG, embeddings, pgvector, or LLM integration has been added.
- [x] Phase 7 not started.
