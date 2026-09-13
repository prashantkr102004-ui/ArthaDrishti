# Phase 9: Financial Analytics Engine

## Scope

Phase 9 adds deterministic financial analytics over canonical transactions stored in PostgreSQL.

Implemented:

- analytics service layer
- protected analytics API endpoints
- KPI semantics for income, expenses, savings, savings rate, investments, and raw net flow
- category spending aggregation
- monthly trend aggregation
- top merchant aggregation
- period comparison with category deltas
- protected dashboard powered by backend analytics
- backend analytics tests

Deferred:

- LLM financial Q&A
- RAG, embeddings, pgvector
- forecasting
- anomaly detection
- recurring-payment detection
- budgeting and goal planning
- account-level analytics filters

## KPI Definitions

Income:

- credit transactions categorized as `Income`
- own-account transfers are excluded
- uncategorized credits are not automatically treated as income

Expenses:

- debit transactions excluding `Transfers`, `Investments`, and `Income`
- uncategorized debit transactions are treated as expenses unless a later rule proves otherwise

Savings:

```text
Savings = Income - Expenses
```

Savings rate:

```text
Savings Rate = Savings / Income * 100
```

When income is zero, savings rate is returned as `null` instead of infinity or a misleading zero.

Raw net flow:

```text
Raw Net Flow = Total Credits - Total Debits
```

Raw net flow is intentionally separate from savings. It includes transfers and investments because it describes literal account movement, not financial health.

Investments:

- debit transactions categorized as `Investments`
- excluded from normal consumption expenses
- reported separately as `investment_amount`

Transfers:

- excluded from income and expenses
- still included in raw total debits/credits and raw net flow

Refunds and reversals:

- not treated as income in Phase 9
- current handling is conservative because the system does not yet have a dedicated refund/reversal model

## SQL/Python Responsibility Split

SQL handles:

- filtering by authenticated user and transaction date
- `SUM`
- `COUNT`
- `GROUP BY`
- category aggregation
- merchant aggregation
- monthly aggregation

Python handles:

- validating date-range semantics
- composing response schemas
- calculating percentages from exact Decimal values
- period comparison orchestration
- category-delta sorting

The frontend does not calculate financial KPIs. It only formats and renders values returned by the API.

## Endpoint Design

All endpoints require authentication and derive ownership from `get_current_user`.

- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/categories`
- `GET /api/v1/analytics/monthly`
- `GET /api/v1/analytics/merchants`
- `GET /api/v1/analytics/compare`

Every endpoint rejects invalid date ranges where the start date is after the end date.

The service does not accept `user_id` from clients.

## Decimal Handling

Stored transaction amounts use PostgreSQL `NUMERIC(19,4)` and Python `Decimal`.

The analytics service quantizes money outputs to four decimal places and percentage outputs to four decimal places. It does not convert money into floating-point values for backend calculations.

## Comparison Semantics

Period comparison compares period A against period B.

```text
Difference = Period A - Period B
Percentage Change = Difference / Period B * 100
```

When the period B baseline is zero, percentage change is returned as `null`.

Category deltas are calculated with the same expense semantics as category spending. Transfers and investments are excluded.

## Dashboard Functionality

The protected `/dashboard` route now shows:

- income
- expenses
- savings
- savings rate
- investments
- raw net flow
- transaction count
- category spending bars
- monthly trend bars
- top merchants

The dashboard supports:

- This Month
- Last Month
- Last 3 Months
- Last 6 Months

The selected period changes API requests consistently across all widgets.

## Tests

Phase 9 tests verify:

- income calculation
- expense calculation
- transfer exclusion
- investment handling
- savings and savings rate
- raw cash flow
- zero-income handling
- empty-data behavior
- invalid date ranges
- Decimal precision
- category spending totals and percentages
- monthly analytics across multiple months
- top merchant ranking
- period comparison
- category deltas
- authenticated user isolation
- authentication required for analytics endpoints

Latest verification:

```text
backend: 79 passed
frontend lint: passed
frontend build: passed
```

## Known Limitations

- Account-level filters are deferred until financial accounts are implemented.
- Refund/reversal modeling needs a deliberate future design.
- Category hierarchy is not recursively classified for analytics yet.
- No materialized views are used; SQL aggregation is enough for the MVP scale.
- No frontend browser automation tests were added in this phase.
- No LLM/RAG functionality is present in the analytics path.

## Viva Explanations

### Why should an LLM not calculate financial totals?

Financial totals must be exact, repeatable, private, and auditable. SQL and backend logic can be tested against known transactions. An LLM may explain verified outputs later, but it should not invent or calculate the numbers.

### Why are transfers excluded from income and expenses?

Transfers often move the user's own money between accounts. Counting one side as income and the other as expense would inflate both metrics and misrepresent real earning and spending.

### What is the difference between cash flow and savings?

Raw cash flow is literal account movement: credits minus debits. Savings is financially classified: income minus real expenses. A transfer affects cash flow but should not change savings.

### Why are calculations performed in SQL/backend instead of the frontend?

The backend is the trusted calculation boundary. It enforces ownership, uses Decimal-safe values, applies consistent financial semantics, and prevents users or UI bugs from changing financial results.

### How does ArthaDrishti compare spending between two months?

The backend aggregates expenses for each period using the same category-exclusion rules, subtracts period B from period A, calculates percentage change when the baseline is nonzero, and also computes category-level deltas to show what caused the change.

## Phase 9 Completion Checklist

- [x] Financial semantics are explicitly defined
- [x] Income is calculated correctly
- [x] Expenses are calculated correctly
- [x] Transfers do not distort analytics
- [x] Investments are handled deliberately
- [x] Savings is calculated deterministically
- [x] Savings rate is correct
- [x] Raw cash flow is clearly distinguished
- [x] Category spending works
- [x] Monthly trends work
- [x] Top merchants work
- [x] Period comparison works
- [x] Category deltas work
- [x] Date filtering works
- [x] Multi-user isolation works
- [x] Decimal precision is preserved
- [x] Analytics APIs are tested
- [x] Dashboard uses backend analytics
- [x] KPI cards work
- [x] Category visualization works
- [x] Monthly visualization works
- [x] Top merchants display works
- [x] Empty/error/loading states work
- [x] Frontend lint/build passes
- [x] Full backend tests pass
- [x] README updated
- [x] Phase 9 report completed
- [x] No LLM/RAG functionality has started
