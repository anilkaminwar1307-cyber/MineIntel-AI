"""NumberSafe 2.0 — calculation lineage tables and temporal_grain column

Revision ID: e1f2a3b4c5d6
Revises: d9f1a2b3c4e5
Create Date: 2026-09-20 04:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd9f1a2b3c4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add temporal_grain to extracted_facts
    with op.batch_alter_table('extracted_facts') as batch_op:
        batch_op.add_column(
            sa.Column('temporal_grain', sa.String(length=30), nullable=True)
        )
        batch_op.create_index('ix_extracted_facts_temporal_grain', ['temporal_grain'], unique=False)

    # 2. Create calculation_runs table
    op.create_table(
        'calculation_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('metric_code', sa.String(100), nullable=False, index=True),
        sa.Column('filters_json', sa.Text(), nullable=True),
        sa.Column('result', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('calculation_method', sa.String(100), nullable=True),
        sa.Column('sql_description', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evidence_used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('excluded_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified_pct', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('warnings_json', sa.Text(), nullable=True),
        sa.Column('is_demo_scope', sa.String(30), nullable=True),
        sa.Column('initiated_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 3. Create calculation_inputs table
    op.create_table(
        'calculation_inputs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('calculation_id', sa.String(36), sa.ForeignKey('calculation_runs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('fact_id', sa.String(36), nullable=False, index=True),
        sa.Column('inclusion_status', sa.String(20), nullable=False),
        sa.Column('exclusion_reason', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('calculation_inputs')
    op.drop_table('calculation_runs')

    with op.batch_alter_table('extracted_facts') as batch_op:
        batch_op.drop_index('ix_extracted_facts_temporal_grain')
        batch_op.drop_column('temporal_grain')
