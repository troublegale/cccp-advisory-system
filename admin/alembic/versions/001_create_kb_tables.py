"""Create kb_versions and kb_files tables

Revision ID: 001
Revises:
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kb_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("version_num", sa.Integer, unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("s3_prefix", sa.Text, nullable=False),
        sa.Column("qdrant_collection", sa.Text, nullable=True),
        sa.Column("file_count", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
    )

    op.create_table(
        "kb_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kb_versions.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("s3_key", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("sha256", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("kb_files")
    op.drop_table("kb_versions")
