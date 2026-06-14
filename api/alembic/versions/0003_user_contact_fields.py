"""add central user contact fields

Revision ID: 0003_user_contact_fields
Revises: 0002_registration_code_values
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_user_contact_fields"
down_revision = "0002_registration_code_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
    op.drop_column("users", "email")
