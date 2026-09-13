# API Reference

All application endpoints are under `/api/v1` unless noted. Authenticated endpoints require `Authorization: Bearer <token>`.

## Health

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | No | Application health. |
| GET | `/health/db` | No | Database readiness check. |
| GET | `/api/v1/` | No | API version health. |

## Authentication And Users

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | No | Create user with email/password. |
| POST | `/api/v1/auth/login` | No | Return Bearer access token. |
| GET | `/api/v1/users/me` | Yes | Return current safe user profile. |

Registration/login never return password hashes. Invalid login responses are intentionally generic.

## Documents

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/documents` | Yes | Upload PDF statement metadata and private file. |
| GET | `/api/v1/documents` | Yes | List current user's documents with pagination/filtering. |
| GET | `/api/v1/documents/{document_id}` | Yes | Get one owned document's metadata. |
| POST | `/api/v1/documents/{document_id}/parse` | Yes | Parse/process an owned document. |
| POST | `/api/v1/documents/{document_id}/index` | Yes | Index owned document text for RAG. |
| DELETE | `/api/v1/documents/{document_id}` | Yes | Delete owned document if no imported transactions exist. |

Upload accepts only `bank_statement` or `credit_card_statement` document types and PDF files.

## Transactions

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/transactions` | Yes | List transactions with date, direction, document, limit, and offset filters. |
| GET | `/api/v1/transactions/{transaction_id}` | Yes | Get one owned transaction. |
| PATCH | `/api/v1/transactions/{transaction_id}/category` | Yes | Recategorize one transaction and optionally future merchant matches. |

Transactions originate from document processing. Manual transaction creation/editing is intentionally deferred.

## Categories

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/categories` | Yes | List system categories and subcategories. |

## Analytics

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/analytics/summary` | Yes | Income, expenses, savings, savings rate, cash flow, investments. |
| GET | `/api/v1/analytics/categories` | Yes | Category-wise spending. |
| GET | `/api/v1/analytics/monthly` | Yes | Monthly income/expense/savings trends. |
| GET | `/api/v1/analytics/merchants` | Yes | Top spending merchants. |
| GET | `/api/v1/analytics/compare` | Yes | Period and category comparison. |

Analytics require explicit date ranges and are calculated by backend SQL/Python.

## Assistant

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/assistant/query` | Yes | Ask a natural-language question over approved financial tools/RAG. |

The assistant response includes answer text, tools used, structured data, evidence, warnings, and document sources where applicable.

## Document Search / RAG

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/document-search` | Yes | Search indexed document chunks with optional document filter and bounded `top_k`. |

RAG is for document text, not structured financial totals.

## Budgets, Goals, Insights

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/budgets` | Yes | Create a monthly overall/category budget. |
| GET | `/api/v1/budgets` | Yes | List budgets. |
| GET | `/api/v1/budgets/progress` | Yes | Budget progress for a date range. |
| PATCH | `/api/v1/budgets/{budget_id}` | Yes | Update owned budget. |
| DELETE | `/api/v1/budgets/{budget_id}` | Yes | Delete owned budget. |
| POST | `/api/v1/goals` | Yes | Create financial goal. |
| GET | `/api/v1/goals` | Yes | List goals. |
| POST | `/api/v1/goals/affordability` | Yes | Calculate goal affordability. |
| PATCH | `/api/v1/goals/{goal_id}` | Yes | Update owned goal. |
| DELETE | `/api/v1/goals/{goal_id}` | Yes | Delete owned goal. |
| GET | `/api/v1/advanced/insights` | Yes | Combined recurring, subscription, budget, forecast, anomaly insights. |
| GET | `/api/v1/advanced/recurring-payments` | Yes | Likely recurring payments. |
| GET | `/api/v1/advanced/subscriptions` | Yes | Likely subscriptions and monthly total. |
| GET | `/api/v1/advanced/forecast` | Yes | Next-month spending forecast. |
| GET | `/api/v1/advanced/anomalies` | Yes | Explainable financial anomalies. |

## OpenAPI

Development docs are available at `/docs` and `/openapi.json` when the backend is running.
