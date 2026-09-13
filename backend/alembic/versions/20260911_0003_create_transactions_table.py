"""create transactions table

Revision ID: 20260911_0003
Revises: 20260909_0002
Create Date: 2026-09-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260911_0003"
down_revision: str | None = "20260909_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("balance", sa.Numeric(19, 4), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("dedupe_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "direction in ('debit', 'credit')",
            name="ck_transactions_direction",
        ),
        sa.CheckConstraint(
            "length(currency) = 3 and currency = upper(currency)",
            name="ck_transactions_currency_code",
        ),
        sa.CheckConstraint(
            "extraction_confidence is null or (extraction_confidence >= 0 and extraction_confidence <= 1)",
            name="ck_transactions_extraction_confidence_range",
        ),
        sa.CheckConstraint(
            "source_page is null or source_page > 0",
            name="ck_transactions_source_page_positive",
        ),
        sa.CheckConstraint(
            "source_row is null or source_row > 0",
            name="ck_transactions_source_row_positive",
        ),
        sa.UniqueConstraint(
            "user_id",
            "dedupe_fingerprint",
            name="uq_transactions_user_fingerprint",
        ),
    )
    op.create_index(
        "ix_transactions_user_date",
        "transactions",
        ["user_id", sa.text("transaction_date DESC"), sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_transactions_user_direction_date",
        "transactions",
        ["user_id", "direction", sa.text("transaction_date DESC")],
    )
    op.create_index("ix_transactions_document_id", "transactions", ["document_id"])
    op.create_index(
        "ix_transactions_user_document",
        "transactions",
        ["user_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_document", table_name="transactions")
    op.drop_index("ix_transactions_document_id", table_name="transactions")
    op.drop_index("ix_transactions_user_direction_date", table_name="transactions")
    op.drop_index("ix_transactions_user_date", table_name="transactions")
    op.drop_table("transactions")
