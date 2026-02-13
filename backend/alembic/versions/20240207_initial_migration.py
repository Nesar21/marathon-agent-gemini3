
"""Initial_migration

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2024-02-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users ---
    op.create_table('users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('plan_tier', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # --- API Keys ---
    op.create_table('api_keys',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=False)

    # --- Validation Result ---
    op.create_table('validation_result',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('plan_hash', sa.String(length=64), nullable=False),
        sa.Column('engine_version', sa.String(length=64), nullable=False),
        sa.Column('canonical_plan_json', sa.Text(), nullable=False),
        sa.Column('dfr_json', sa.Text(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_hash', 'engine_version', name='uq_plan_engine_version')
    )
    op.create_index(op.f('ix_validation_result_engine_version'), 'validation_result', ['engine_version'], unique=False)
    op.create_index(op.f('ix_validation_result_plan_hash'), 'validation_result', ['plan_hash'], unique=False)

    # --- Audit Log ---
    op.create_table('audit_log',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('request_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('violations_count', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_request_id'), 'audit_log', ['request_id'], unique=False)

    # --- AI Rate Limit Tracker ---
    op.create_table('ai_rate_limit_tracker',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('rpm_count', sa.Integer(), nullable=True),
        sa.Column('rpd_count', sa.Integer(), nullable=True),
        sa.Column('last_request_at', sa.DateTime(), nullable=True),
        sa.Column('daily_reset_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ai_rate_limit_tracker')
    op.drop_index(op.f('ix_audit_log_request_id'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index(op.f('ix_validation_result_plan_hash'), table_name='validation_result')
    op.drop_index(op.f('ix_validation_result_engine_version'), table_name='validation_result')
    op.drop_table('validation_result')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
