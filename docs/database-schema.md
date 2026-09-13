# Database Schema

ArthaDrishti uses PostgreSQL with UUID primary keys and pgvector for document-search embeddings.

## ER Diagram

```text
users
  | 1
  |----< documents
  |        | 1
  |        |----< transactions
  |        |----< document_chunks
  |
  |----< user_merchant_overrides
  |----< budgets
  |----< financial_goals

categories
  | 1
  |----< categories(parent_id)
  |----< merchant_aliases
  |----< transactions
  |----< user_merchant_overrides
  |----< budgets
```

## Tables

### users

Stores authentication identity.

Important fields: `id`, `email`, `password_hash`, `is_active`, `created_at`, `updated_at`.

### documents

Stores metadata for uploaded PDFs.

Important fields: `id`, `user_id`, `original_filename`, `storage_backend`, `storage_key`, `document_type`, `mime_type`, `file_size_bytes`, `sha256_hash`, `processing_status`, `indexing_status`.

PDF binaries are not stored in PostgreSQL.

### transactions

Canonical financial transactions imported from parsed documents.

Important fields: `id`, `user_id`, `document_id`, `transaction_date`, `value_date`, `raw_description`, `normalized_description`, `canonical_merchant`, `merchant_key`, `category_id`, `amount`, `direction`, `currency`, `balance`, `source_page`, `source_row`, `dedupe_fingerprint`.

Money uses `NUMERIC(19,4)` and application `Decimal`. Amounts are positive; direction is `debit` or `credit`.

### categories

System categories and optional parent-child hierarchy.

Examples: Food, Shopping, Transportation, Rent, Bills, Subscriptions, Healthcare, Travel, Investments, Transfers, ATM, Income, Other.

### merchant_aliases

Database-backed alias rules for deterministic merchant normalization and categorization.

Examples: `SWIGGY`, `AMAZON PAY INDIA`, `NETFLIX.COM`.

### user_merchant_overrides

Stores user-specific merchant/category preferences. Future matching transactions can use these overrides.

### document_chunks

Stores RAG chunks.

Important fields: `id`, `user_id`, `document_id`, `chunk_index`, `page_number`, `text`, `embedding`, `embedding_model`, `character_count`.

The vector dimension is controlled by the configured embedding model and migration.

### budgets

Stores user-owned monthly budgets.

Important fields: `id`, `user_id`, optional `category_id`, `amount`, `period`, `start_date`.

### financial_goals

Stores user-owned financial goals.

Important fields: `id`, `user_id`, `name`, `target_amount`, `target_date`, `current_saved_amount`, `status`.

## Key Decisions

- UUID primary keys avoid predictable sequential IDs.
- User-owned records carry `user_id` and are filtered by authenticated identity.
- Transactions keep source `document_id`, `source_page`, and `source_row` for provenance.
- Exact duplicates are prevented with deterministic transaction fingerprints.
- Document duplicates are detected per user by SHA-256 file hash.
- pgvector stores document embeddings for semantic retrieval, not structured analytics.
- Indexes prioritize user/date transaction queries, document listings, merchant/category analytics, and user-filtered vector search.

## Deferred Tables

Recurring patterns and anomalies are currently calculated dynamically. Persistent tables can be added later if cached insight history or user workflow state becomes necessary.
