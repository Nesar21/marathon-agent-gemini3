
"""Add schema_version to validation_result

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2024-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add schema_version column with default '1.0'
    op.add_column('validation_result', sa.Column('schema_version', sa.String(length=16), nullable=False, server_default='1.0'))


def downgrade() -> None:
    op.drop_column('validation_result', 'schema_version')
