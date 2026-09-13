"""create categories and merchant rules

Revision ID: 20260911_0004
Revises: 20260911_0003
Create Date: 2026-09-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260911_0004"
down_revision: str | None = "20260911_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])

    op.execute(
        """
        insert into categories (name, slug, description) values
            ('Food', 'food', 'Meals, restaurants, groceries, and food delivery.'),
            ('Shopping', 'shopping', 'Retail purchases and online/offline shopping.'),
            ('Transportation', 'transportation', 'Rides, fuel, transit, and commuting.'),
            ('Rent', 'rent', 'Rent and housing payments.'),
            ('Bills', 'bills', 'Utilities, telecom, and household bills.'),
            ('Entertainment', 'entertainment', 'Movies, games, events, and leisure.'),
            ('Subscriptions', 'subscriptions', 'Recurring digital or service subscriptions.'),
            ('Healthcare', 'healthcare', 'Pharmacy, clinics, and medical expenses.'),
            ('Travel', 'travel', 'Flights, hotels, and trip expenses.'),
            ('Investments', 'investments', 'Investment account activity.'),
            ('Transfers', 'transfers', 'Transfers between accounts or people.'),
            ('ATM', 'atm', 'Cash withdrawals and ATM activity.'),
            ('Income', 'income', 'Salary, refunds, and other inflows.'),
            ('Other', 'other', 'Fallback category for uncategorized transactions.')
        """
    )
    op.execute(
        """
        insert into categories (name, slug, parent_id, description)
        select child.name, child.slug, parent.id, child.description
        from (
            values
                ('Restaurants', 'food-restaurants', 'food', 'Restaurant and food-delivery spending.'),
                ('Groceries', 'food-groceries', 'food', 'Grocery and household food purchases.'),
                ('Online', 'shopping-online', 'shopping', 'Online shopping.'),
                ('Offline', 'shopping-offline', 'shopping', 'In-store shopping.')
        ) as child(name, slug, parent_slug, description)
        join categories parent on parent.slug = child.parent_slug
        """
    )

    op.create_table(
        "merchant_aliases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("merchant_name", sa.String(length=120), nullable=False),
        sa.Column("alias_pattern", sa.Text(), nullable=False),
        sa.Column("alias_key", sa.String(length=160), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_merchant_aliases_confidence_range",
        ),
        sa.UniqueConstraint(
            "merchant_name",
            "alias_pattern",
            name="uq_merchant_aliases_merchant_pattern",
        ),
    )
    op.create_index("ix_merchant_aliases_alias_key", "merchant_aliases", ["alias_key"])
    op.create_index("ix_merchant_aliases_category_id", "merchant_aliases", ["category_id"])

    op.execute(
        """
        insert into merchant_aliases (merchant_name, alias_pattern, alias_key, category_id, confidence)
        select alias.merchant_name, alias.alias_pattern, alias.alias_key, categories.id, alias.confidence
        from (
            values
                ('Swiggy', 'SWIGGY', 'SWIGGY', 'food-restaurants', 0.9800),
                ('Swiggy', 'UPI SWIGGY', 'SWIGGY', 'food-restaurants', 0.9800),
                ('Swiggy', 'SWIGGY LIMITED', 'SWIGGY LIMITED', 'food-restaurants', 0.9800),
                ('Amazon', 'AMAZON PAY INDIA', 'AMAZON PAY INDIA', 'shopping-online', 0.9800),
                ('Amazon', 'AMAZON SELLER SERVICES', 'AMAZON SELLER SERVICES', 'shopping-online', 0.9800),
                ('Amazon', 'AMAZON', 'AMAZON', 'shopping-online', 0.9800),
                ('Uber', 'UBER TRIP BLR', 'UBER TRIP BLR', 'transportation', 0.9800),
                ('Uber', 'UBER', 'UBER', 'transportation', 0.9800),
                ('Netflix', 'NETFLIX.COM', 'NETFLIX COM', 'subscriptions', 0.9800),
                ('Netflix', 'NETFLIX', 'NETFLIX', 'subscriptions', 0.9800),
                ('Apollo Pharmacy', 'APOLLO PHARMACY', 'APOLLO PHARMACY', 'healthcare', 0.9800)
        ) as alias(merchant_name, alias_pattern, alias_key, category_slug, confidence)
        join categories on categories.slug = alias.category_slug
        """
    )

    op.create_table(
        "user_merchant_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_name", sa.String(length=120), nullable=False),
        sa.Column("merchant_key", sa.String(length=160), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "merchant_key",
            name="uq_user_merchant_overrides_user_merchant",
        ),
    )
    op.create_index(
        "ix_user_merchant_overrides_user_merchant",
        "user_merchant_overrides",
        ["user_id", "merchant_key"],
    )

    op.add_column("transactions", sa.Column("canonical_merchant", sa.String(length=120), nullable=True))
    op.add_column("transactions", sa.Column("merchant_key", sa.String(length=160), nullable=True))
    op.add_column("transactions", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("categorization_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column("transactions", sa.Column("categorization_source", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        "transactions_category_id_fkey",
        "transactions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_transactions_categorization_confidence_range",
        "transactions",
        "categorization_confidence is null or (categorization_confidence >= 0 and categorization_confidence <= 1)",
    )
    op.create_check_constraint(
        "ck_transactions_categorization_source",
        "transactions",
        "categorization_source is null or categorization_source in ('override', 'exact_merchant', 'alias', 'regex', 'fallback')",
    )
    op.create_index("ix_transactions_user_category_date", "transactions", ["user_id", "category_id", sa.text("transaction_date DESC")])
    op.create_index("ix_transactions_user_merchant", "transactions", ["user_id", "merchant_key"])


def downgrade() -> None:
    op.drop_index("ix_transactions_user_merchant", table_name="transactions")
    op.drop_index("ix_transactions_user_category_date", table_name="transactions")
    op.drop_constraint("ck_transactions_categorization_source", "transactions", type_="check")
    op.drop_constraint("ck_transactions_categorization_confidence_range", "transactions", type_="check")
    op.drop_constraint("transactions_category_id_fkey", "transactions", type_="foreignkey")
    op.drop_column("transactions", "categorization_source")
    op.drop_column("transactions", "categorization_confidence")
    op.drop_column("transactions", "category_id")
    op.drop_column("transactions", "merchant_key")
    op.drop_column("transactions", "canonical_merchant")

    op.drop_index("ix_user_merchant_overrides_user_merchant", table_name="user_merchant_overrides")
    op.drop_table("user_merchant_overrides")
    op.drop_index("ix_merchant_aliases_category_id", table_name="merchant_aliases")
    op.drop_index("ix_merchant_aliases_alias_key", table_name="merchant_aliases")
    op.drop_table("merchant_aliases")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")
