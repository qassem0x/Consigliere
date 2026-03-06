"""add summary column to chats

Revision ID: daabce827dc3
Revises: 
Create Date: 2026-03-06 02:55:20.763376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'daabce827dc3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add summary column to chats table."""
    op.add_column('chats', sa.Column('summary', sa.Text(), nullable=True, server_default=''))
    op.alter_column('chats', 'summary', server_default=None)


def downgrade() -> None:
    """Remove summary column from chats table."""
    op.drop_column('chats', 'summary')
