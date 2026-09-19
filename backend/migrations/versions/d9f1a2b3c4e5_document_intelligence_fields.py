"""Add document intelligence and demo fields

Revision ID: d9f1a2b3c4e5
Revises: c8d7f282d487
Create Date: 2026-09-19 02:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd9f1a2b3c4e5'
down_revision: Union[str, None] = 'c8d7f282d487'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to documents table
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('source_type', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('table_count', sa.Integer(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('quality_label', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('average_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('is_demo', sa.Boolean(), server_default=sa.text('0'), nullable=False))
        batch_op.create_index('ix_documents_is_demo', ['is_demo'], unique=False)

    # Add columns to extracted_facts table
    with op.batch_alter_table('extracted_facts') as batch_op:
        batch_op.add_column(sa.Column('is_demo', sa.Boolean(), server_default=sa.text('0'), nullable=False))
        batch_op.create_index('ix_extracted_facts_is_demo', ['is_demo'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('extracted_facts') as batch_op:
        batch_op.drop_index('ix_extracted_facts_is_demo')
        batch_op.drop_column('is_demo')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index('ix_documents_is_demo')
        batch_op.drop_column('is_demo')
        batch_op.drop_column('average_confidence')
        batch_op.drop_column('quality_label')
        batch_op.drop_column('table_count')
        batch_op.drop_column('source_type')
