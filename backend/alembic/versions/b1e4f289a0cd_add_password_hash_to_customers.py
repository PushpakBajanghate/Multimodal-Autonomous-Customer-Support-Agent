"""add password_hash to customers

Revision ID: b1e4f289a0cd
Revises: 4f23c750c12c
Create Date: 2026-10-15 23:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e4f289a0cd'
down_revision: Union[str, Sequence[str], None] = '4f23c750c12c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'password_hash')
