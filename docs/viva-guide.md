# Viva Guide

## 60-Second Project Explanation

ArthaDrishti is a smart personal financial assistant. It solves the problem of scattered financial statements by letting a user upload bank or credit-card PDFs, extract transactions, store them in PostgreSQL, categorize merchants, calculate analytics, and ask natural-language questions. The key design decision is that the LLM is not the source of financial truth. All totals, comparisons, budgets, forecasts, and anomalies are calculated deterministically by backend services using SQL and Decimal. The LLM only interprets questions, calls approved tools, and explains verified results. RAG is used separately for unstructured document text such as fees or terms. The system includes authentication, private document storage, user isolation, prompt-injection defenses, and a responsive dashboard for demonstration.

## 3-Minute Explanation

ArthaDrishti is built as a modular-monolith financial assistant with a Next.js frontend, FastAPI backend, PostgreSQL database, and pgvector for document search. A user registers, uploads a supported PDF statement, and the backend validates and stores it privately. The parser extracts transaction rows into a common format: date, description, amount, debit/credit direction, balance, and source traceability. Transactions are stored canonically in PostgreSQL with Decimal-safe money handling and deterministic deduplication.

After storage, merchant normalization and categorization convert raw descriptions like `UPI SWIGGY BANGALORE` into canonical merchants and categories. Analytics are calculated by backend SQL/Python services, not by the frontend or an LLM. The dashboard visualizes income, expenses, savings, savings rate, spending by category, monthly trends, top merchants, and recent transactions.

For natural-language Q&A, the assistant uses tool calling. It interprets a question, selects an approved backend tool, validates arguments, runs deterministic services, and explains the verified result. RAG is used only for document-text questions, such as "What late fee is mentioned?" It retrieves owned document chunks from pgvector and cites source pages.

Advanced features include recurring-payment detection, subscription detection, budgets, financial goals, spending forecasts, and anomaly detection. These are explainable heuristics/statistics, not autonomous financial actions. Security includes Argon2id passwords, JWT authentication, user ownership enforcement, private file storage, SQL parameterization, RAG isolation, prompt-injection tests, rate limiting, and production config validation.

## Project

### What problem does ArthaDrishti solve?

It helps individuals turn static financial statements into searchable, analyzable, structured financial data.

### What makes it different from a chatbot?

It does not ask an LLM to guess totals. It uses deterministic backend services for numbers and uses AI only for language and explanation.

### What is the main architecture?

Next.js frontend, FastAPI backend, PostgreSQL with pgvector, private document storage, parser/categorization/analytics services, and a bounded AI orchestrator.

## Backend

### Why FastAPI?

FastAPI provides typed request/response schemas, automatic OpenAPI docs, dependency injection, and strong Python ecosystem compatibility.

### Why modular monolith?

It keeps deployment and development simple for a student project while preserving clean module boundaries.

### Why PostgreSQL?

It supports reliable relational data, transactions, constraints, indexes, `NUMERIC` money storage, and pgvector for RAG.

## Money

### Why Decimal?

Financial systems need exact decimal arithmetic. Floats can produce rounding artifacts such as `0.1 + 0.2`.

### Why not float?

Float is binary approximation, not exact decimal money representation.

## Documents

### How are bank statements parsed?

Text-based PDFs are extracted with PyMuPDF, matched to a parser, and transaction rows are converted into structured fields.

### Why not use an LLM to parse everything?

LLMs may hallucinate, misread numbers, cost more, expose more private data, and are harder to test deterministically.

## Transactions

### How does deduplication work?

The backend creates deterministic fingerprints from user/document context, date, amount, direction, normalized description, and balance where useful.

### How are overlapping statements handled?

Exact deterministic duplicates are skipped so reprocessing or overlapping imports do not double-count transactions.

## Categorization

### How are merchants normalized?

Rules and database-backed aliases clean raw descriptions and map them to canonical merchants.

### Why rule-based categorization?

It is explainable, testable, cheap, and appropriate before collecting enough data for supervised learning.

## Analytics

### How are income and expenses calculated?

Backend services filter transactions by date/category/direction and aggregate them in SQL.

### Why aren't transfers counted as income or expense?

Transfers move money between accounts and should not inflate income or spending.

## LLM

### What is tool calling?

The model requests a predefined backend function with structured arguments; the backend validates and executes it.

### Why can't the LLM access PostgreSQL directly?

Direct SQL generation risks data leakage, injection-like behavior, incorrect queries, and cross-user access.

### How do you reduce hallucinations?

Answers are grounded in deterministic tool results and tested so unsupported numbers are not silently returned.

## RAG

### What is RAG?

Retrieval-Augmented Generation retrieves relevant document chunks and gives only that context to the model.

### What are embeddings?

Embeddings are vectors that represent text meaning for semantic similarity search.

### Why pgvector?

It keeps vector search inside PostgreSQL, near user/document metadata and ownership filters.

### SQL vs RAG?

SQL answers structured financial totals. RAG answers unstructured document-text questions.

## Advanced Features

### How do recurring payments work?

Transactions are grouped by merchant/description, then interval and amount consistency are scored.

### How does forecasting work?

It uses a weighted moving average over completed monthly expenses and labels the result as an estimate.

### How does anomaly detection work?

It flags unusually high transactions compared with merchant history or robust global thresholds and explains why.

## Security

### How are passwords stored?

Only Argon2id password hashes are stored.

### How do you prevent IDOR?

Every user-owned query filters by the authenticated user's ID from the JWT, not client-supplied IDs.

### How do you prevent prompt injection?

Document text and transaction descriptions are treated as untrusted data; they cannot create tools or override system rules.

### How do you isolate RAG results?

Chunks store `user_id`, and retrieval filters by `user_id` in SQL.

## Deployment

### How is ArthaDrishti deployed?

Frontend can deploy to Vercel/Netlify/container hosting, backend to a container platform, database to managed PostgreSQL with pgvector, and documents to private persistent storage or object storage.

### How are secrets managed?

Through environment variables locally and managed platform secrets in production.

### How do migrations run?

Alembic applies schema changes with `alembic upgrade head` before the backend serves traffic.
