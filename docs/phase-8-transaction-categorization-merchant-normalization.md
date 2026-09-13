# Phase 8: Transaction Categorization & Merchant Normalization

## Scope

Phase 8 enriches stored transactions with deterministic merchant and category metadata.

Implemented:

- merchant normalization service
- database-backed merchant aliases
- seeded category hierarchy
- rule-based categorization engine
- explainable confidence scores
- user merchant-category overrides
- protected category API
- protected category update API
- frontend category editing on the Transactions page

Deferred:

- analytics and charts
- budgeting and forecasting
- RAG, embeddings, pgvector
- LLM financial Q&A
- anomaly detection
- recurring-payment detection
- transaction amount/date/description editing

## Normalization Pipeline

For each transaction description, the backend:

1. Preserves `raw_description`.
2. Creates `normalized_description` by trimming and collapsing whitespace.
3. Creates merchant lookup candidates by:
   - uppercasing text
   - replacing punctuation with spaces
   - removing payment prefixes such as `UPI`, `POS`, `NEFT`, `IMPS`
   - removing obvious noisy IDs such as long numeric reference tokens
   - generating indexed n-gram candidates for alias lookup
4. Chooses a canonical merchant when a rule can explain it.
5. Assigns category and confidence through the layered categorization engine.

Examples:

- `UPI SWIGGY BANGALORE` -> `Swiggy`
- `SWIGGY LIMITED` -> `Swiggy`
- `AMAZON PAY INDIA` -> `Amazon`
- `AMAZON SELLER SERVICES` -> `Amazon`
- `UBER TRIP BLR` -> `Uber`
- `NETFLIX.COM` -> `Netflix`
- `APOLLO PHARMACY` -> `Apollo Pharmacy`

## Alias System

Aliases are stored in PostgreSQL in `merchant_aliases`.

Important fields:

- `merchant_name`
- `alias_pattern`
- `alias_key`
- `category_id`
- `confidence`

`alias_key` is indexed for fast lookup. It is not globally unique because different raw aliases can collapse to the same key after prefix cleanup.

Seed aliases include Swiggy, Amazon, Uber, Netflix, and Apollo Pharmacy.

## Category Hierarchy

Categories are stored in PostgreSQL in `categories`.

Top-level seed categories:

- Food
- Shopping
- Transportation
- Rent
- Bills
- Entertainment
- Subscriptions
- Healthcare
- Travel
- Investments
- Transfers
- ATM
- Income
- Other

Initial child categories:

- Restaurants under Food
- Groceries under Food
- Online under Shopping
- Offline under Shopping

The MVP primarily uses categories for labeling and later analytics preparation.

## Categorization Engine

Priority order:

1. User override
2. Exact merchant match
3. Alias match
4. Regex/rule match
5. Fallback to `Other`

The engine does not call an LLM. Each result stores:

- `canonical_merchant`
- `merchant_key`
- `category_id`
- `categorization_confidence`
- `categorization_source`

## Confidence Model

Confidence values are explainable rule strengths, not ML probabilities.

- user override: `1.00`
- exact merchant: `1.00`
- alias: seeded alias confidence, usually `0.98`
- regex/rule: `0.85`
- fallback: `0.40`

This keeps the output honest and testable.

## User Overrides

Users can recategorize a transaction through:

```text
PATCH /api/v1/transactions/{transaction_id}/category
```

Payload:

```json
{
  "category_id": "...",
  "apply_to_merchant": true
}
```

MVP behavior:

- the selected transaction is updated
- when `apply_to_merchant` is true, a per-user merchant override is stored
- future matching transactions for the same user use the override first
- matching existing transactions for that user and merchant are updated
- overrides do not affect other users

## API Endpoints

Categories:

- `GET /api/v1/categories`

Transactions:

- `GET /api/v1/transactions`
- `GET /api/v1/transactions/{transaction_id}`
- `PATCH /api/v1/transactions/{transaction_id}/category`

All endpoints require authentication and enforce current-user ownership.

## Performance Notes

Alias lookup uses indexed `alias_key` values and candidate `IN` queries. The backend does not scan every alias in Python for each transaction.

Future improvements may include:

- richer alias administration
- merchant tables separate from alias rows
- trigram search for controlled fuzzy matching
- batch categorization jobs

These are intentionally deferred until real statement diversity justifies them.

## Security Notes

- Clients cannot send or choose `user_id`.
- Transaction ownership is always checked server-side.
- Cross-user category updates return `404`.
- User overrides are scoped by `user_id + merchant_key`.
- No raw PDF text or bulk transaction history is sent to an LLM.
- No financial calculations are performed by the categorization layer.

## Limitations

- Rule coverage is intentionally small.
- No AI categorization.
- No fuzzy matching yet.
- No merchant admin UI.
- No user-created categories yet.
- Ambiguous merchants can still fall back to `Other`.
- Existing transactions imported before Phase 8 are not backfilled automatically unless reprocessed or updated later.

## Viva Explanations

### Why not use an LLM for categorization?

Categorization must be deterministic, cheap, private, and testable. An LLM may be useful later for suggestions, but the stored category should come from explainable rules, aliases, or user decisions. This prevents hallucinated merchants and keeps financial data handling predictable.

### What is merchant normalization?

Merchant normalization turns messy bank descriptions into a stable merchant label. For example, `UPI SWIGGY BANGALORE` and `SWIGGY LIMITED` both become `Swiggy`. This makes later analytics cleaner because spending can be grouped by a canonical merchant.

### Why preserve `raw_description`?

The raw description is audit evidence from the statement. If normalization or categorization is wrong, the original text lets us debug, correct, and explain where the stored result came from.

### How do user overrides improve the system?

Different users may treat the same merchant differently. One user may classify Amazon as Shopping, another as Groceries. Overrides let the system learn a user's preference without changing global rules or affecting other users.

## Phase 8 Completion Checklist

- [x] Merchant normalization works
- [x] Alias table exists
- [x] Category seed data exists
- [x] Category hierarchy is supported
- [x] Categorization engine works
- [x] Confidence values are produced
- [x] User overrides work
- [x] Future matching merchant categorization uses overrides
- [x] Ownership is enforced
- [x] Frontend category editing exists
- [x] Tests pass
- [x] Documentation is complete
- [x] No Phase 9 analytics work has started
