"""add_llm_log_telemetry_columns

Revision ID: 58f1a23b49de
Revises: 260ef031ac96
Create Date: 2026-11-01 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '58f1a23b49de'
down_revision: Union[str, Sequence[str], None] = '260ef031ac96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add telemetry and token caching columns to llm_logs."""
    op.add_column('llm_logs', sa.Column('session_id', sa.String(length=36), nullable=True))
    op.add_column('llm_logs', sa.Column('cached_prompt_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('llm_logs', sa.Column('error_type', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_llm_logs_session_id'), 'llm_logs', ['session_id'], unique=False)


def downgrade() -> None:
    """Remove telemetry columns."""
    op.drop_index(op.f('ix_llm_logs_session_id'), table_name='llm_logs')
    op.drop_column('llm_logs', 'error_type')
    op.drop_column('llm_logs', 'cached_prompt_tokens')
    op.drop_column('llm_logs', 'session_id')

