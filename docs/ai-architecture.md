# AI Architecture

## Principle

The LLM is not the source of financial truth.

Financial numbers come from PostgreSQL, deterministic backend services, `Decimal`, and explainable statistics. The LLM helps interpret language, select approved tools, and explain verified results.

## Deterministic Backend

Responsible for:

- transaction filtering
- income, expenses, savings, savings rate
- category and merchant aggregation
- period comparisons
- budgets and goals
- recurring/subscription detection
- forecasts and anomalies
- RAG retrieval ownership checks

## LLM Layer

Responsible for:

- understanding natural-language questions
- choosing approved tool calls
- explaining structured results
- refusing unsupported or non-financial questions

The LLM cannot:

- query PostgreSQL directly
- execute SQL
- supply `user_id`
- read arbitrary files
- access API keys or JWTs
- create autonomous financial actions

## Tool Calling

```text
User question
-> orchestrator
-> model/tool router
-> strict tool schema validation
-> backend service
-> structured result
-> grounded answer
```

Tool results are JSON-like data, not human-formatted strings the model has to parse.

## RAG

RAG handles unstructured document text:

- statement terms
- fees
- interest rates
- billing clauses
- document wording

It does not calculate spending totals. Those come from analytics.

Retrieved chunks are passed as untrusted data with source metadata. Prompt injection inside a PDF cannot create new tools or bypass ownership.

## Data Minimization

Only necessary data is sent to a configured external provider:

- user question
- selected aggregated values
- limited transaction excerpts
- retrieved document chunks

Raw PDFs, database credentials, JWTs, storage paths, and full transaction exports are not intentionally sent.

## Provider Modes

- `LLM_PROVIDER=mock`: local deterministic demo/testing behavior.
- external provider: requires `LLM_API_KEY` and `LLM_MODEL`.
- `EMBEDDING_PROVIDER=local`: local deterministic RAG embeddings for demo/test.

If AI providers fail, deterministic application features continue working.
