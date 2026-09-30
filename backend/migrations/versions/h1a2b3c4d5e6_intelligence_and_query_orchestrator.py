"""Add QueryHistory intelligence fields and indexes

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-09-30 02:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = 'h1a2b3c4d5e6'
down_revision: Union[str, None] = 'g1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = set(inspector.get_table_names())

    def add_col_if_missing(table_name: str, col_name: str, col_type: sa.types.TypeEngine, server_default=None):
        if table_name not in existing_tables:
            return
        cols = {c["name"] for c in inspector.get_columns(table_name)}
        if col_name not in cols:
            op.add_column(table_name, sa.Column(col_name, col_type, server_default=server_default, nullable=True))

    # Add QueryHistory columns
    add_col_if_missing("query_history", "intent", sa.String(50))
    add_col_if_missing("query_history", "confidence", sa.Float())
    add_col_if_missing("query_history", "status", sa.String(50))
    add_col_if_missing("query_history", "records_used", sa.Integer())
    add_col_if_missing("query_history", "execution_time_ms", sa.Float())


def downgrade() -> None:
    pass
