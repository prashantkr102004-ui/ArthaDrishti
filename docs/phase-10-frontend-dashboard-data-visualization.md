# Phase 10: Frontend Dashboard & Data Visualization

## Scope

Phase 10 turns the existing authenticated frontend into a coherent financial dashboard experience.

Implemented:

- reusable authenticated app shell
- shared navigation across Dashboard, Documents, and Transactions
- reusable UI primitives for cards, badges, empty states, error states, links, and loading skeletons
- reusable period selector
- reusable INR/date/file-size formatting helpers
- dashboard KPI cards
- backend-powered comparison indicators
- category spending visualization
- monthly trend visualization
- top merchants section
- recent transactions section
- Documents page polish
- Transactions page polish
- responsive layout improvements

Deferred:

- LLM financial Q&A
- RAG, embeddings, pgvector
- anomaly detection
- forecasting
- budgeting
- recurring-payment detection
- custom date ranges
- third-party chart library integration
- frontend test framework setup

## UI Architecture

The authenticated app now uses a shared `AppShell` component.

The shell provides:

- desktop sidebar navigation
- compact mobile navigation
- top header
- brand identity
- logout action
- shared content spacing

Main navigation:

- Dashboard
- Documents
- Transactions

No future AI/assistant pages were added.

## Dashboard Layout

The dashboard prioritizes:

1. period controls
2. KPI cards
3. supporting KPI cards
4. category spending
5. top merchants
6. monthly trends
7. recent transactions

The first view emphasizes high-signal financial state without crowding every feature into one row.

## Backend Endpoint to Widget Mapping

The dashboard does not calculate financial totals. It consumes backend APIs:

- KPI cards: `GET /api/v1/analytics/summary`
- comparison indicators: `GET /api/v1/analytics/compare`
- category spending: `GET /api/v1/analytics/categories`
- monthly trend: `GET /api/v1/analytics/monthly`
- top merchants: `GET /api/v1/analytics/merchants`
- recent transactions: `GET /api/v1/transactions`

Documents page:

- document list/status: `GET /api/v1/documents`
- upload: `POST /api/v1/documents`
- process: `POST /api/v1/documents/{document_id}/parse`
- delete: `DELETE /api/v1/documents/{document_id}`

Transactions page:

- transaction list/filtering: `GET /api/v1/transactions`
- category data: `GET /api/v1/categories`
- category override: `PATCH /api/v1/transactions/{transaction_id}/category`

## Period Selector

Supported periods:

- This Month
- Last Month
- Last 3 Months
- Last 6 Months

The selected period produces one date range. That range is passed consistently to all compatible dashboard analytics requests.

The previous comparison period is derived from the same range length and sent to the backend comparison endpoint. The frontend does not calculate comparison totals.

## Visualization Decisions

No third-party chart library is currently installed. Instead of adding a dependency only for this phase, the dashboard uses simple CSS bar visualizations with text labels.

Category spending shows:

- category name
- backend amount
- backend percentage
- horizontal bar

Monthly trend shows:

- month label
- transaction count
- income bar
- expense bar
- savings bar

Top merchants shows:

- rank
- merchant name
- backend amount

## Loading, Error, and Empty States

Dashboard:

- skeleton KPI loading state
- full-page error if summary fails
- widget-level warnings if secondary analytics fail
- useful empty state if no transactions exist

Documents:

- loading skeleton
- empty document state
- processing summary after parse/import
- status badges for Ready, Processing, Parsed, and Failed

Transactions:

- loading skeleton
- empty transaction state
- safe error message
- category-save feedback

Authentication failures still clear local auth state and redirect to Login.

## Accessibility Decisions

- form inputs have labels
- mobile and desktop navigation use semantic nav elements
- financial direction uses both text and color
- charts include text labels and numeric summaries
- tables use semantic `table`, `thead`, `tbody`, `th`, and `td`
- colors are not the only way to understand category/status/direction
- layout uses horizontal overflow for dense financial tables on small screens

## Privacy Decisions

The UI does not expose:

- document storage keys
- backend file paths
- file hashes
- access tokens
- database IDs except where route behavior requires internal resource IDs in API calls
- raw full PDF text
- full account numbers

The dashboard displays only derived analytics and transaction metadata already available through authenticated APIs.

## Frontend Financial Logic Boundary

The frontend may:

- format INR values
- format dates
- choose date ranges
- render bars and labels
- scale bar widths for presentation

The frontend must not calculate:

- income
- expenses
- savings
- savings rate
- category totals
- merchant totals
- monthly totals
- comparison totals

Those values come from the Phase 9 backend analytics engine.

## Tests and Verification

Automated frontend test framework:

- not configured in the current project
- intentionally not added in Phase 10 to avoid introducing a broad testing dependency decision without planning

Verification completed:

- backend regression tests pass
- frontend lint passes
- frontend production build passes
- backend health endpoint works
- Dashboard, Documents, and Transactions routes return HTTP 200 in dev mode

Latest checks:

```text
backend: 79 passed
frontend lint: passed
frontend build: passed
runtime route smoke: /dashboard, /documents, /transactions returned 200
```

## Known Limitations

- No browser automation tests yet.
- No custom date range UI yet.
- No chart library yet.
- No dark mode toggle yet.
- App shell currently shows logout everywhere and user email where the page has already loaded it.
- Visual verification was limited to route/build checks in this environment.

## Viva Explanations

### Why does the frontend not calculate financial totals?

Financial totals must be deterministic, consistent, and auditable. The backend applies the official financial rules and returns verified numbers. The frontend only formats and visualizes those numbers.

### How does the dashboard remain consistent when the user changes the date period?

The period selector creates one shared date range. Every compatible dashboard widget uses that same range when calling the backend analytics APIs.

### Why separate backend analytics from frontend visualization?

The backend is responsible for correctness and security. The frontend is responsible for user experience. This separation prevents UI bugs from changing financial results and makes future LLM explanations use verified data.

### How do you handle empty or incomplete financial data?

The dashboard shows onboarding guidance when no transactions exist. Individual widgets show safe empty messages when a specific dataset is missing, such as no merchants or no expense categories.

### How is sensitive financial information protected in the UI?

The UI avoids internal paths, file hashes, tokens, storage keys, raw PDF text, and full account identifiers. It shows only authenticated metadata, transaction summaries, and backend-derived analytics.

## Phase 10 Completion Checklist

- [x] Authenticated app shell exists
- [x] Navigation is consistent
- [x] Dashboard is polished and usable
- [x] Period selector works
- [x] KPI cards use backend analytics
- [x] Currency formatting is consistent
- [x] Date formatting is consistent
- [x] Category spending visualization works
- [x] Monthly trend visualization works
- [x] Top merchants section works
- [x] Recent transactions section works
- [x] Empty state works
- [x] Loading states work
- [x] Error states work
- [x] Responsive layout is improved
- [x] Documents page remains functional
- [x] Transactions page remains functional
- [x] Category editing remains functional
- [x] Sensitive internal data is not exposed
- [x] Frontend contains no duplicate financial calculations
- [x] Frontend lint passes
- [x] Production build passes
- [x] Backend regression tests pass
- [x] README updated
- [x] Phase 10 report completed
- [x] No Phase 11 work started
