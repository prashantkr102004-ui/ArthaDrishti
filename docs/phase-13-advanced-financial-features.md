# Phase 13: Advanced Financial Features

## Objective

Phase 13 adds explainable financial intelligence on top of canonical transactions, deterministic analytics, the assistant, and RAG.

The implementation covers:

- recurring-payment detection
- subscription detection
- monthly budgets
- financial goals
- affordability calculations
- next-month spending forecasting
- financial anomaly detection
- structured advanced insights
- assistant tools for advanced features
- protected `/insights` frontend page

No autonomous actions, trading, external banking integrations, multi-agent system, deployment hardening, or full security audit were added.

## Core Design Rule

Advanced financial features remain grounded in deterministic and explainable logic:

- SQL queries
- Python services
- `Decimal` arithmetic
- transparent thresholds
- simple robust statistics

The LLM may route a question to an approved tool and explain the returned data, but it does not calculate or predict financial values.

## Persistence Decision

Persisted:

- `budgets`
- `financial_goals`

Calculated dynamically:

- recurring payments
- subscriptions
- forecasts
- anomalies
- insights

Dynamic calculation avoids stale derived records when transactions change because of document deletion, reprocessing, or future correction workflows.

## Recurring Detection Algorithm

Transactions are grouped by:

- canonical merchant when available
- normalized description as fallback
- debit direction

Minimum history:

- at least 3 occurrences

Supported timing thresholds:

- weekly: 5-9 days
- monthly: 25-35 days
- quarterly: 80-100 days
- yearly: 330-400 days

Confidence is an explainable heuristic based on:

- interval consistency, 45%
- amount consistency, 30%
- occurrence count, 25%

This confidence is not a machine-learning probability.

## Subscription Rules

A recurring payment is considered a subscription when:

- its category is `Subscriptions`, or
- its merchant matches known subscription-like merchants such as Netflix or Spotify

Recurring rent and utilities are not treated as subscriptions. They remain recurring payments or recurring bills.

Inactive detection is conservative. If the expected billing interval is missed with tolerance, status becomes `possibly_inactive`; the system does not claim the subscription was cancelled.

## Budget Model

Budgets are monthly and user-owned.

Types:

- overall spending budget
- optional category budget

Progress calculation:

```text
percentage_used = spent_amount / budget_amount * 100
remaining = budget_amount - spent_amount
```

Statuses:

- `<80%`: `on_track`
- `80-100%`: `near_limit`
- `>100%`: `exceeded`

Budget calculations use backend analytics spending semantics, so transfers and investments do not distort consumption budgets.

## Goal Planning

Goals include:

- name
- target amount
- target date
- current saved amount
- status

Calculations:

```text
remaining = target_amount - current_saved_amount
required_monthly_saving = remaining / months_remaining
```

Feasibility labels:

- `likely_on_track`
- `needs_adjustment`
- `currently_unrealistic`
- `completed`

Affordability checks compare required monthly saving with recent historical savings. The result is an estimate based on past behavior, not a guarantee.

## Forecast Method

Forecasting supports next-month spending only.

Minimum history:

- 3 completed months

Method:

- weighted moving average of completed monthly expenses
- more recent months receive higher weight

Uncertainty range:

- projected value plus/minus average absolute deviation from the projection

This is intentionally simple and explainable. LSTM, transformers, and deep learning are not justified for the current data volume or project scope.

## Anomaly Methodology

This is financial anomaly detection, not fraud detection.

Methods:

- merchant average multiple: transaction is at least 3x the merchant's prior typical amount after 3 prior occurrences
- robust global threshold: transaction exceeds a median/MAD-based threshold when enough historical debit transactions exist

Every anomaly includes:

- transaction id
- date
- merchant
- amount
- method
- score
- plain-language reason

## Assistant Integration

New approved tools:

- `get_recurring_payments`
- `get_subscriptions`
- `get_budget_status`
- `get_goal_status`
- `forecast_spending`
- `get_financial_anomalies`

Tool calls are validated. The model cannot pass `user_id`, execute SQL, or bypass ownership.

## Frontend Functionality

The protected `/insights` page shows:

- recurring payments
- likely subscriptions
- budget creation and progress
- goal creation and progress
- next-month spending projection
- unusual transaction alerts

The dashboard remains focused on core analytics.

## Security and Ownership

- budgets belong to the authenticated user
- goals belong to the authenticated user
- recurring patterns use only the current user's transactions
- forecasts use only the current user's transaction history
- anomalies use only the current user's transactions
- the frontend never sends `user_id`
- no autonomous money movement, cancellation, payment, trading, or budget modification is performed

## Tests

Phase 13 tests cover:

- exact monthly subscription recurrence
- variable monthly utility recurrence
- rent recurring but not subscription
- irregular merchant not recurring
- subscription totals
- budget create/progress/ownership/invalid amount
- goal calculations and cross-user protection
- affordability calculation
- insufficient forecast history
- valid forecast output
- anomaly detection with explainable reason
- multi-user isolation
- assistant routing for advanced tools

## Limitations

- recurring detection is heuristic
- forecast is near-term only
- no long-range forecasting
- no Isolation Forest or black-box ML
- anomaly detection is not fraud detection
- no automated subscription cancellation
- no automatic budget creation
- no goal recommendations beyond deterministic calculations

## Viva Preparation

### How does ArthaDrishti detect recurring payments?

It groups a user's debit transactions by canonical merchant or normalized description, checks for at least 3 occurrences, evaluates intervals such as monthly or weekly, and scores consistency of timing, amount, and count.

### What is the difference between a recurring bill and a subscription?

A recurring bill repeats, but it may be rent or electricity. A subscription is a recurring payment for a subscription-like service such as Netflix or Spotify. The system uses category and merchant rules to distinguish them.

### How is a user's monthly budget progress calculated?

The backend sums eligible spending for the selected month, divides it by the configured budget amount, calculates remaining amount, and labels the status as on track, near limit, or exceeded.

### How does the goal-planning system determine required monthly savings?

It subtracts current saved amount from the target amount, calculates months remaining until the target date, and divides remaining amount by months remaining using `Decimal`.

### What forecasting algorithm is used and why?

It uses a weighted moving average of recent completed monthly expenses. It is simple, explainable, and appropriate for small personal-finance histories.

### Why didn't you use an LSTM for forecasting?

An LSTM needs much more data, is harder to explain, and would be overkill for a portfolio MVP with limited personal transactions. A transparent baseline is more trustworthy here.

### How does anomaly detection work?

It flags unusual financial patterns such as a merchant transaction much larger than the user's prior payments to that merchant, or a debit above a robust historical high-spend threshold.

### Is anomaly detection the same as fraud detection?

No. It only highlights unusual financial patterns. It does not claim fraud or make security decisions.

### How are the advanced AI features explainable?

Each feature returns structured facts and reasons from deterministic services. Any LLM explanation must be grounded in those backend outputs.

## Completion Checklist

- [x] Recurring-payment detection implemented.
- [x] Recurrence rules documented.
- [x] Variable recurring payments handled conservatively.
- [x] Subscriptions distinguished from generic recurring bills.
- [x] Subscription totals implemented.
- [x] Budget CRUD implemented.
- [x] Budget progress is deterministic.
- [x] Goal CRUD implemented.
- [x] Required monthly savings calculation implemented.
- [x] Affordability and goal feasibility implemented.
- [x] Spending forecast implemented.
- [x] Minimum history enforced.
- [x] Forecasting method documented.
- [x] Forecasts are not presented as guarantees.
- [x] Anomaly detection implemented.
- [x] Anomaly reasons are explainable.
- [x] Anomalies are not labeled as fraud.
- [x] Assistant tools support advanced features.
- [x] Advanced features enforce user ownership.
- [x] Insights frontend implemented.
- [x] No autonomous financial actions exist.
