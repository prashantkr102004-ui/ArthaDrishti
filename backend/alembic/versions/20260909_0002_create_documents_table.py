"""create documents table

Revision ID: 20260909_0002
Revises: 20260909_0001
Create Date: 2026-09-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0002"
down_revision: str | Sequence[str] | None = "20260909_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "document_type in ('bank_statement', 'credit_card_statement')",
            name="ck_documents_document_type",
        ),
        sa.CheckConstraint(
            "processing_status in ('ready_for_processing', 'processing', 'completed', 'failed')",
            name="ck_documents_processing_status",
        ),
        sa.CheckConstraint(
            "storage_backend in ('local', 'object_storage')",
            name="ck_documents_storage_backend",
        ),
        sa.CheckConstraint("file_size_bytes > 0", name="ck_documents_file_size_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "sha256_hash", name="uq_documents_user_sha256"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index(
        "ix_documents_user_uploaded_at",
        "documents",
        ["user_id", sa.text("uploaded_at DESC")],
    )
    op.create_index(
        "ix_documents_user_status",
        "documents",
        ["user_id", "processing_status"],
    )
    op.create_index("ix_documents_user_type", "documents", ["user_id", "document_type"])


def downgrade() -> None:
    op.drop_index("ix_documents_user_type", table_name="documents")
    op.drop_index("ix_documents_user_status", table_name="documents")
    op.drop_index("ix_documents_user_uploaded_at", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
