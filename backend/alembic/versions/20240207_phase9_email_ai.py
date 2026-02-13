
"""Phase 9: Add email verification fields and AISuggestion table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2024-02-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email verification fields to users
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=64), nullable=True))
    
    # Create AISuggestion table
    op.create_table('ai_suggestions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('plan_hash', sa.String(length=64), nullable=False),
        sa.Column('engine_version', sa.String(length=64), nullable=False),
        sa.Column('suggestion_json', sa.Text(), nullable=False),
        sa.Column('prompt_mode', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_suggestions_plan_hash'), 'ai_suggestions', ['plan_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_suggestions_plan_hash'), table_name='ai_suggestions')
    op.drop_table('ai_suggestions')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'is_active')
