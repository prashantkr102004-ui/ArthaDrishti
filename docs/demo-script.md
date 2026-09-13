# Demo Script

Target length: 5-10 minutes.

## Before The Demo

1. Start PostgreSQL and backend.
2. Run migrations.
3. Run `python -m app.scripts.seed_demo`.
4. Start frontend.
5. Use only synthetic data.

## Step 1: Login

Click: Login page.

Say: "ArthaDrishti starts with user authentication. Every financial resource is scoped to the authenticated user, not a frontend-supplied user ID."

## Step 2: Upload Statement

Click: Documents -> upload `local_uploads/demo/arthadrishti-demo-statement.pdf`.

Say: "The backend validates that this is a PDF, checks size and signature, stores it privately, and keeps only safe metadata in the database."

## Step 3: Process Statement

Click: Process / Extract transactions.

Say: "The PDF is parsed deterministically. Money is parsed as Decimal, debit/credit direction is normalized, and rows are converted into structured transaction data."

## Step 4: Transactions

Click: Transactions.

Say: "Transactions retain raw descriptions for auditability, but also get normalized merchants and categories using rule-based aliases and user overrides."

## Step 5: Dashboard

Click: Dashboard.

Say: "The dashboard uses backend analytics APIs. The frontend only visualizes numbers; it does not calculate income, expenses, savings, or category totals."

## Step 6: Analytics Assistant

Ask: "Where did most of my money go this month?"

Say: "The LLM chooses a safe analytics tool. The backend calculates the answer, and the model explains the verified result."

## Step 7: Comparison

Ask: "Why were my expenses higher this month?"

Say: "The comparison comes from deterministic period and category deltas, which can later be explained naturally by the assistant."

## Step 8: RAG Document Search

Upload/index `local_uploads/demo/arthadrishti-demo-credit-card-terms.pdf`.

Ask: "What late-payment fee is mentioned in this statement?"

Say: "RAG is used only for unstructured document text. The answer includes source metadata rather than guessing."

## Step 9: Insights

Click: Insights.

Say: "Advanced features are explainable: recurring payments use interval consistency, subscriptions use merchant/category rules, forecasts use a moving average, and anomalies explain why a transaction looks unusual."

## Step 10: Security Wrap-Up

Say: "Passwords are hashed with Argon2id, files are private, SQL queries are controlled, RAG is user-filtered, and the LLM cannot access the database directly."
