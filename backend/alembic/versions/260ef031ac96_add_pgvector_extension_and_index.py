"""add_pgvector_extension_and_index

Revision ID: 260ef031ac96
Revises: 47e95deb65dd
Create Date: 2026-11-01 09:19:57.886322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '260ef031ac96'
down_revision: Union[str, Sequence[str], None] = '47e95deb65dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add pgvector extension and vector similarity index."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Create pgvector extension (PostgreSQL only)
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
        
        # Create ivfflat index for cosine similarity search on chunks.embedding
        op.execute(
            'CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat '
            'ON chunks USING ivfflat (embedding vector_cosine_ops) '
            'WITH (lists = 100)'
        )


def downgrade() -> None:
    """Downgrade schema - remove vector index."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS ix_chunks_embedding_ivfflat')
    # Note: We don't drop the pgvector extension as it may be used by other tables
