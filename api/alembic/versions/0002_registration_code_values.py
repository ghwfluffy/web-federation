"""store registration code values

Revision ID: 0002_registration_code_values
Revises: 0001_empty_foundation
Create Date: 2026-05-02 16:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_registration_code_values"
down_revision = "0001_empty_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("registration_codes", sa.Column("code_value", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("registration_codes", "code_value")
