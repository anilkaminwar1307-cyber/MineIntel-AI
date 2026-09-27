"""Add schema completeness: tables (document_pages, sheets, tables, quality, logs, claims),
columns (users.password_hash/is_demo, document_chunks.section, report.content_json/pdf_*, facts versioning),
and required fact indexes.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-09-27 06:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Create document_pages if missing
    if "document_pages" not in existing_tables:
        op.create_table(
            "document_pages",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("page_number", sa.Integer(), nullable=False),
            sa.Column("raw_text", sa.Text(), nullable=True),
            sa.Column("char_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("word_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("has_native_text", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("is_ocr_page", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("ocr_confidence", sa.Float(), nullable=True),
            sa.Column("extraction_method", sa.String(length=50), server_default="PDF_NATIVE", nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 2. Create document_sheets if missing
    if "document_sheets" not in existing_tables:
        op.create_table(
            "document_sheets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("sheet_name", sa.String(length=200), nullable=False),
            sa.Column("sheet_index", sa.Integer(), server_default="0", nullable=False),
            sa.Column("row_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("col_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("used_range", sa.String(length=50), nullable=True),
            sa.Column("header_row", sa.Integer(), nullable=True),
            sa.Column("has_merged_cells", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("preview_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 3. Create document_tables if missing
    if "document_tables" not in existing_tables:
        op.create_table(
            "document_tables",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("sheet_id", sa.String(length=36), sa.ForeignKey("document_sheets.id", ondelete="CASCADE"), nullable=True),
            sa.Column("table_index", sa.Integer(), server_default="0", nullable=False),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("sheet_name", sa.String(length=200), nullable=True),
            sa.Column("title", sa.String(length=500), nullable=True),
            sa.Column("source_range", sa.String(length=100), nullable=True),
            sa.Column("row_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("col_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("headers_json", sa.Text(), nullable=True),
            sa.Column("data_json", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), server_default="1.0", nullable=True),
            sa.Column("structure_status", sa.String(length=50), server_default="CLEAN", nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 4. Create document_quality if missing
    if "document_quality" not in existing_tables:
        op.create_table(
            "document_quality",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("quality_label", sa.String(length=30), nullable=True),
            sa.Column("enhancement_recommended", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("blur_score", sa.Float(), nullable=True),
            sa.Column("contrast_score", sa.Float(), nullable=True),
            sa.Column("skew_angle", sa.Float(), nullable=True),
            sa.Column("resolution_dpi", sa.Integer(), nullable=True),
            sa.Column("is_dark", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("is_skewed", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("is_blurry", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("is_low_res", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("enhancement_applied", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 5. Create processing_logs if missing
    if "processing_logs" not in existing_tables:
        op.create_table(
            "processing_logs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("stage", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 6. Create claims and claim_evidence_links if missing
    if "claims" not in existing_tables:
        op.create_table(
            "claims",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("query_history_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("report_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("claim_type", sa.String(length=50), nullable=False),
            sa.Column("statement", sa.Text(), nullable=False),
            sa.Column("support_status", sa.String(length=50), nullable=False),
            sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("is_verified_scope", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("temporal_grain", sa.String(length=30), nullable=True),
            sa.Column("metric_code", sa.String(length=100), nullable=True),
            sa.Column("claimed_value", sa.Float(), nullable=True),
            sa.Column("derived_value", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "claim_evidence_links" not in existing_tables:
        op.create_table(
            "claim_evidence_links",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("claim_id", sa.String(length=36), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("fact_id", sa.String(length=36), sa.ForeignKey("extracted_facts.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("relevance_score", sa.Float(), server_default="1.0", nullable=True),
            sa.Column("is_direct_match", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        )

    # ── Helper for safe column additions without circular batch_alter_table ──
    def add_col_if_missing(table_name: str, col_name: str, col_type: sa.types.TypeEngine, server_default=None):
        if table_name not in existing_tables:
            return
        cols = {c["name"] for c in inspector.get_columns(table_name)}
        if col_name not in cols:
            op.add_column(table_name, sa.Column(col_name, col_type, server_default=server_default, nullable=True))

    # 7. Add auth columns to users
    add_col_if_missing("users", "password_hash", sa.String(255))
    add_col_if_missing("users", "is_demo", sa.Boolean(), server_default=sa.text("0"))

    # 8. Add document intelligence & versioning columns to documents
    add_col_if_missing("documents", "sha256", sa.String(64))
    add_col_if_missing("documents", "source_version", sa.String(50), server_default="v1.0")
    add_col_if_missing("documents", "revision_number", sa.Integer(), server_default="1")
    add_col_if_missing("documents", "supersedes_document_id", sa.String(36))
    add_col_if_missing("documents", "is_latest_version", sa.Boolean(), server_default=sa.text("1"))
    add_col_if_missing("documents", "revision_date", sa.DateTime())
    add_col_if_missing("documents", "pipeline_version", sa.String(50), server_default="2.0")
    add_col_if_missing("documents", "processing_started_at", sa.DateTime())
    add_col_if_missing("documents", "processing_completed_at", sa.DateTime())
    add_col_if_missing("documents", "warning_count", sa.Integer(), server_default="0")
    add_col_if_missing("documents", "real_fact_count", sa.Integer(), server_default="0")

    # 9. Add section column to document_chunks
    add_col_if_missing("document_chunks", "section", sa.String(200))

    # 10. Add extracted_facts columns
    add_col_if_missing("extracted_facts", "temporal_grain", sa.String(30))
    add_col_if_missing("extracted_facts", "source_object_type", sa.String(50))
    add_col_if_missing("extracted_facts", "source_object_id", sa.String(100))
    add_col_if_missing("extracted_facts", "source_hash", sa.String(64))
    add_col_if_missing("extracted_facts", "dedup_key", sa.String(255))
    add_col_if_missing("extracted_facts", "original_numeric_value", sa.Float())
    add_col_if_missing("extracted_facts", "original_metric_code", sa.String(100))
    add_col_if_missing("extracted_facts", "original_unit", sa.String(50))
    add_col_if_missing("extracted_facts", "superseded_by_id", sa.String(36))
    add_col_if_missing("extracted_facts", "is_superseded", sa.Boolean(), server_default=sa.text("0"))

    # 11. Add generated_reports columns
    add_col_if_missing("generated_reports", "content_json", sa.Text())
    add_col_if_missing("generated_reports", "pdf_status", sa.String(50), server_default="READY")
    add_col_if_missing("generated_reports", "pdf_path", sa.String(500))
    add_col_if_missing("generated_reports", "pdf_filename", sa.String(255))
    add_col_if_missing("generated_reports", "pdf_size", sa.Integer(), server_default="0")
    add_col_if_missing("generated_reports", "pdf_generated_at", sa.DateTime())
    add_col_if_missing("generated_reports", "document_ids_json", sa.Text())
    add_col_if_missing("generated_reports", "is_demo_scope", sa.Boolean(), server_default=sa.text("0"))

    # 12. Add review_actions columns
    add_col_if_missing("review_actions", "conflict_id", sa.String(36))
    add_col_if_missing("review_actions", "previous_metric", sa.String(100))
    add_col_if_missing("review_actions", "new_metric", sa.String(100))
    add_col_if_missing("review_actions", "previous_unit", sa.String(50))
    add_col_if_missing("review_actions", "new_unit", sa.String(50))
    add_col_if_missing("review_actions", "previous_status", sa.String(50))
    add_col_if_missing("review_actions", "new_status", sa.String(50))

    # 13. Required indexes for extracted_facts
    if "extracted_facts" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("extracted_facts")}
        if "ix_facts_sub_metric_period" not in existing_indexes:
            try:
                op.create_index(
                    "ix_facts_sub_metric_period",
                    "extracted_facts",
                    ["subsidiary", "metric_code", "reporting_period"],
                    unique=False,
                )
            except Exception:
                pass

        if "ix_extracted_facts_dedup_key" not in existing_indexes:
            try:
                op.create_index(
                    "ix_extracted_facts_dedup_key",
                    "extracted_facts",
                    ["dedup_key"],
                    unique=False,
                )
            except Exception:
                pass

        if "ix_extracted_facts_superseded_by_id" not in existing_indexes:
            try:
                op.create_index(
                    "ix_extracted_facts_superseded_by_id",
                    "extracted_facts",
                    ["superseded_by_id"],
                    unique=False,
                )
            except Exception:
                pass

        if "ix_extracted_facts_is_superseded" not in existing_indexes:
            try:
                op.create_index(
                    "ix_extracted_facts_is_superseded",
                    "extracted_facts",
                    ["is_superseded"],
                    unique=False,
                )
            except Exception:
                pass


def downgrade() -> None:
    pass
