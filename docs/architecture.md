# ArthaDrishti Architecture

## System Context

ArthaDrishti is a modular-monolith financial assistant. The frontend is a Next.js application, the backend is FastAPI, and PostgreSQL with pgvector stores relational financial data plus document-search vectors.

```text
User Browser
    |
    v
Next.js Frontend
    |
    | REST + Bearer JWT
    v
FastAPI Backend
    |
    +-- Auth / Users
    +-- Documents / Private Storage
    +-- PDF Parser
    +-- Transactions / Categorization
    +-- Analytics Engine
    +-- AI Orchestrator
    +-- RAG Indexing / Retrieval
    +-- Advanced Insights
    |
    v
PostgreSQL + pgvector

External, optional:
    LLM provider       <- assistant explanations
    Embedding provider <- document search vectors
```

## Deployment View

Recommended portfolio deployment:

- Frontend: Vercel, Netlify, or containerized Next.js.
- Backend: Render, Railway, Fly.io, or a small VM/container platform.
- Database: managed PostgreSQL that supports pgvector.
- Document storage: persistent private volume for demo; S3-compatible object storage for production.
- AI providers: configured through environment variables. Mock/local providers remain usable for demos.

## Document Flow

```text
PDF upload
-> authentication
-> MIME/signature/size validation
-> generated storage key
-> private storage
-> document metadata row
-> explicit parse/index actions
```

Documents are never stored in frontend public folders and storage paths are not returned to the client.

## Transaction Processing

```text
Stored PDF
-> PyMuPDF text extraction
-> synthetic statement parser
-> extracted transaction rows
-> Decimal money validation
-> canonical debit/credit model
-> dedupe fingerprint
-> PostgreSQL transactions
-> merchant/category enrichment
```

The parser layer is intentionally scoped to safe, testable formats for this portfolio build: the original synthetic fixture format and a generic text-based five-column bank statement layout. Additional bank parsers can be added behind the existing parser abstraction without weakening unsupported-format protection.

## Analytics

Analytics are deterministic backend operations over canonical transactions. SQL performs filtering, sums, counts, grouping, category totals, merchant totals, and monthly trends. Python composes responses and percentage/comparison semantics.

The frontend never recalculates income, expenses, savings, or category totals.

## AI Tool Calling

```text
Question
-> assistant orchestrator
-> approved tool selection
-> Pydantic argument validation
-> deterministic service
-> structured result
-> grounded explanation
```

The LLM cannot run SQL, access credentials, choose `user_id`, or read arbitrary files.

## RAG

RAG is used only for unstructured document text:

```text
Owned document
-> page text extraction
-> conservative cleaning
-> page-aware chunks
-> embeddings
-> document_chunks table
-> user-filtered vector/keyword retrieval
-> answer with source references
```

Structured questions such as spending totals use analytics, not RAG.

## Advanced Features

Advanced insights are deterministic/explainable:

- recurring payments: interval and amount-consistency heuristics
- subscriptions: recurring payments plus merchant/category rules
- budgets: user-owned monthly limits and deterministic progress
- goals: target amount/date and required monthly savings
- forecasts: weighted moving average over completed months
- anomalies: explainable merchant/global outlier checks

## Security Boundaries

- Passwords use Argon2id.
- JWTs are signed with environment-provided secrets.
- User ownership comes from `get_current_user`.
- Uploaded PDFs are untrusted input.
- Financial math uses `Decimal`/PostgreSQL `NUMERIC`.
- RAG retrieval filters by `user_id` in SQL.
- Retrieved document text is untrusted data, not instructions.
- Production config rejects weak secrets, debug mode, and wildcard CORS.
