"""add private_email and temp_password_hash to employees

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("corporate_email", sa.String(255), nullable=True))
    op.add_column("employees", sa.Column("private_email", sa.String(255), nullable=True))
    op.add_column("employees", sa.Column("temp_password_hash", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_employees_corporate_email", "employees", ["corporate_email"])


def downgrade() -> None:
    op.drop_constraint("uq_employees_corporate_email", "employees", type_="unique")
    op.drop_column("employees", "temp_password_hash")
    op.drop_column("employees", "private_email")
    op.drop_column("employees", "corporate_email")
