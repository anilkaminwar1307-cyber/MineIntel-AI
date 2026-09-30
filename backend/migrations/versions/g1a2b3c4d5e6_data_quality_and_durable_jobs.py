"""Add Data Quality fields, ProcessingJob durable columns, and ExtractedFact scale/coordinates

Revision ID: g1a2b3c4d5e6
Revises: f1a2b3c4d5e6
Create Date: 2026-09-27 15:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = 'g1a2b3c4d5e6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
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

    # 1. ProcessingJob enhancements
    add_col_if_missing("processing_jobs", "retry_count", sa.Integer(), server_default="0")
    add_col_if_missing("processing_jobs", "max_retries", sa.Integer(), server_default="3")
    add_col_if_missing("processing_jobs", "version", sa.Integer(), server_default="1")
    add_col_if_missing("processing_jobs", "idempotency_key", sa.String(64))
    add_col_if_missing("processing_jobs", "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"))

    # 2. ValidationIssue (Data Quality) enhancements
    add_col_if_missing("validation_issues", "status", sa.String(50), server_default="OPEN")
    add_col_if_missing("validation_issues", "assigned_to", sa.String(100))
    add_col_if_missing("validation_issues", "mine", sa.String(100))
    add_col_if_missing("validation_issues", "subsidiary", sa.String(50))
    add_col_if_missing("validation_issues", "reporting_period", sa.String(50))
    add_col_if_missing("validation_issues", "metric_code", sa.String(100))
    add_col_if_missing("validation_issues", "previous_value", sa.Float())
    add_col_if_missing("validation_issues", "proposed_value", sa.Float())
    add_col_if_missing("validation_issues", "previous_unit", sa.String(50))
    add_col_if_missing("validation_issues", "proposed_unit", sa.String(50))
    add_col_if_missing("validation_issues", "reviewer_comments", sa.Text())
    add_col_if_missing("validation_issues", "evidence_context", sa.Text())

    # 3. ExtractedFact dimension-safe and coordinate enhancements
    add_col_if_missing("extracted_facts", "scale", sa.Float(), server_default="1.0")
    add_col_if_missing("extracted_facts", "normalized_value", sa.Float())
    add_col_if_missing("extracted_facts", "bounding_box", sa.String(100))

    # 4. Indexes for rapid quality querying and deduplication
    if "validation_issues" in existing_tables:
        existing_val_idx = {idx["name"] for idx in inspector.get_indexes("validation_issues")}
        for idx_name, col_names in [
            ("ix_validation_issues_status", ["status"]),
            ("ix_validation_issues_subsidiary", ["subsidiary"]),
            ("ix_validation_issues_reporting_period", ["reporting_period"]),
            ("ix_validation_issues_metric_code", ["metric_code"]),
        ]:
            if idx_name not in existing_val_idx:
                try:
                    op.create_index(idx_name, "validation_issues", col_names, unique=False)
                except Exception:
                    pass

    if "extracted_facts" in existing_tables:
        existing_fact_idx = {idx["name"] for idx in inspector.get_indexes("extracted_facts")}
        if "ix_extracted_facts_normalized_value" not in existing_fact_idx:
            try:
                op.create_index("ix_extracted_facts_normalized_value", "extracted_facts", ["normalized_value"], unique=False)
            except Exception:
                pass


def downgrade() -> None:
    pass
