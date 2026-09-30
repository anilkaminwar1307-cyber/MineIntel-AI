"""
MineIntel Demo Data Seeder
==========================
Populates the SQLite database with realistic CIL/CMPDI subsidiary data for
SIH judge demonstrations. Creates:
  - 1 demo Document (virtual statutory filing)
  - 190+ ExtractedFacts across 8 subsidiaries, 6 metric codes, 3 fiscal years
  - 3 EvidenceConflicts (intentional discrepancies between documents)
  - 12 ValidationIssues (sample data quality items)

Run from repo root:
    python scripts/seed_demo_data.py
"""

import sys
import os
import uuid
import json
from datetime import datetime, timezone

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(REPO_ROOT, 'backend', 'data', 'mineintel.db')}")

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.models.validation import ValidationIssue, EvidenceConflict

Base.metadata.create_all(bind=engine)

# ── Constants ─────────────────────────────────────────────────────────────────

SUBSIDIARIES = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CMPDI"]

# Real-world-inspired production data (MT = Million Tonnes)
# Source: CIL Annual Reports FY 2022-23, FY 2023-24, FY 2024-25 provisional
PRODUCTION_DATA = {
    # subsidiary: { FY2022-23: value, FY2023-24: value, FY2024-25: value }
    "ECL":   {"FY 2022-23": 41.8, "FY 2023-24": 42.1, "FY 2024-25": 43.7},
    "BCCL":  {"FY 2022-23": 30.2, "FY 2023-24": 30.8, "FY 2024-25": 31.5},
    "CCL":   {"FY 2022-23": 65.4, "FY 2023-24": 67.2, "FY 2024-25": 69.8},
    "WCL":   {"FY 2022-23": 55.1, "FY 2023-24": 56.8, "FY 2024-25": 58.3},
    "SECL":  {"FY 2022-23": 157.6, "FY 2023-24": 167.2, "FY 2024-25": 175.4},
    "MCL":   {"FY 2022-23": 158.3, "FY 2023-24": 168.5, "FY 2024-25": 180.2},
    "NCL":   {"FY 2022-23": 103.4, "FY 2023-24": 112.8, "FY 2024-25": 119.6},
    "CMPDI": {"FY 2022-23": 0.0,  "FY 2023-24": 0.0,   "FY 2024-25": 0.0},
}

# Production targets
TARGET_DATA = {
    "ECL":   {"FY 2022-23": 42.0, "FY 2023-24": 43.0, "FY 2024-25": 45.0},
    "BCCL":  {"FY 2022-23": 31.0, "FY 2023-24": 31.5, "FY 2024-25": 32.0},
    "CCL":   {"FY 2022-23": 66.0, "FY 2023-24": 68.0, "FY 2024-25": 71.0},
    "WCL":   {"FY 2022-23": 56.0, "FY 2023-24": 58.0, "FY 2024-25": 60.0},
    "SECL":  {"FY 2022-23": 160.0, "FY 2023-24": 168.0, "FY 2024-25": 178.0},
    "MCL":   {"FY 2022-23": 160.0, "FY 2023-24": 170.0, "FY 2024-25": 182.0},
    "NCL":   {"FY 2022-23": 105.0, "FY 2023-24": 115.0, "FY 2024-25": 122.0},
    "CMPDI": {"FY 2022-23": 0.0,  "FY 2023-24": 0.0,   "FY 2024-25": 0.0},
}

# Overburden Removal in million cubic metres (MCuM)
OBR_DATA = {
    "ECL":   {"FY 2022-23": 145.2, "FY 2023-24": 151.8, "FY 2024-25": 158.3},
    "BCCL":  {"FY 2022-23": 78.4,  "FY 2023-24": 80.2,  "FY 2024-25": 83.1},
    "CCL":   {"FY 2022-23": 195.6, "FY 2023-24": 205.4, "FY 2024-25": 218.7},
    "WCL":   {"FY 2022-23": 165.3, "FY 2023-24": 172.8, "FY 2024-25": 179.4},
    "SECL":  {"FY 2022-23": 420.5, "FY 2023-24": 445.2, "FY 2024-25": 468.9},
    "MCL":   {"FY 2022-23": 485.2, "FY 2023-24": 512.6, "FY 2024-25": 538.4},
    "NCL":   {"FY 2022-23": 325.8, "FY 2023-24": 348.9, "FY 2024-25": 375.2},
    "CMPDI": {"FY 2022-23": 0.0,   "FY 2023-24": 0.0,   "FY 2024-25": 0.0},
}

# Coal Dispatch (MT)
DISPATCH_DATA = {
    "ECL":   {"FY 2022-23": 42.3, "FY 2023-24": 42.8, "FY 2024-25": 44.1},
    "BCCL":  {"FY 2022-23": 30.5, "FY 2023-24": 31.2, "FY 2024-25": 31.8},
    "CCL":   {"FY 2022-23": 65.8, "FY 2023-24": 67.8, "FY 2024-25": 70.2},
    "WCL":   {"FY 2022-23": 55.6, "FY 2023-24": 57.2, "FY 2024-25": 58.9},
    "SECL":  {"FY 2022-23": 158.2, "FY 2023-24": 168.1, "FY 2024-25": 176.2},
    "MCL":   {"FY 2022-23": 159.1, "FY 2023-24": 169.2, "FY 2024-25": 181.0},
    "NCL":   {"FY 2022-23": 104.1, "FY 2023-24": 113.5, "FY 2024-25": 120.3},
    "CMPDI": {"FY 2022-23": 0.0,  "FY 2023-24": 0.0,   "FY 2024-25": 0.0},
}

# CMPDI Drilling Meters (in thousand meters)
DRILLING_DATA = {
    "CMPDI": {"FY 2022-23": 892.5, "FY 2023-24": 945.8, "FY 2024-25": 1012.3},
}

# Stripping Ratio (m³/tonne)
STRIP_DATA = {
    "ECL":  {"FY 2022-23": 3.47, "FY 2023-24": 3.61, "FY 2024-25": 3.62},
    "BCCL": {"FY 2022-23": 2.60, "FY 2023-24": 2.60, "FY 2024-25": 2.64},
    "CCL":  {"FY 2022-23": 2.99, "FY 2023-24": 3.05, "FY 2024-25": 3.13},
    "WCL":  {"FY 2022-23": 3.00, "FY 2023-24": 3.04, "FY 2024-25": 3.07},
    "SECL": {"FY 2022-23": 2.67, "FY 2023-24": 2.66, "FY 2024-25": 2.67},
    "MCL":  {"FY 2022-23": 3.06, "FY 2023-24": 3.04, "FY 2024-25": 3.00},
    "NCL":  {"FY 2022-23": 3.14, "FY 2023-24": 3.09, "FY 2024-25": 3.07},
}

METRIC_UNITS = {
    "COAL_PRODUCTION":   "MT",
    "PRODUCTION_TARGET": "MT",
    "OVERBURDEN_REMOVAL":"MCuM",
    "COAL_DISPATCH":     "MT",
    "DRILLING_METERS":   "000 meters",
    "STRIPPING_RATIO":   "m3/tonne",
}

METRIC_NAMES = {
    "COAL_PRODUCTION":   "Raw Coal Production",
    "PRODUCTION_TARGET": "Production Target",
    "OVERBURDEN_REMOVAL":"Overburden Removal (OBR)",
    "COAL_DISPATCH":     "Coal Dispatch",
    "DRILLING_METERS":   "Core / Borehole Drilling Meters",
    "STRIPPING_RATIO":   "Stripping Ratio",
}


def _utcnow():
    return datetime.now(timezone.utc)


def seed(db):
    # ── Check if already seeded ───────────────────────────────────────────────
    existing = db.query(Document).filter(Document.original_filename == "CIL_Consolidated_Annual_Report_FY2024-25.pdf").first()
    if existing:
        print("⚠  Demo data already seeded (document exists). Skipping.")
        return

    print("🌱 Seeding MineIntel demo data...")

    # ── Create demo documents ─────────────────────────────────────────────────
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())   # second document for conflict

    doc1 = Document(
        id=doc1_id,
        original_filename="CIL_Consolidated_Annual_Report_FY2024-25.pdf",
        stored_filename=f"{doc1_id}.pdf",
        file_type="PDF",
        source_type="statutory",
        mime_type="application/pdf",
        file_size=4_850_000,
        document_category="Annual Report",
        organization="Coal India Limited",
        reporting_period="FY 2024-25",
        storage_path=f"uploads/{doc1_id}.pdf",
        page_count=248,
        sheet_count=0,
        table_count=42,
        status="processed",
        processing_progress=100,
        processing_message="Evidence extraction complete",
        fact_count=0,   # updated below
        topic_count=18,
        is_demo=True,
        sha256="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        revision_number=1,
        is_latest_version=True,
        pipeline_version="2.0",
    )

    doc2 = Document(
        id=doc2_id,
        original_filename="SECL_Subsidiary_Production_Report_FY2024-25.pdf",
        stored_filename=f"{doc2_id}.pdf",
        file_type="PDF",
        source_type="subsidiary",
        mime_type="application/pdf",
        file_size=1_230_000,
        document_category="Production Report",
        organization="SECL",
        reporting_period="FY 2024-25",
        storage_path=f"uploads/{doc2_id}.pdf",
        page_count=52,
        sheet_count=0,
        table_count=8,
        status="processed",
        processing_progress=100,
        processing_message="Evidence extraction complete",
        fact_count=0,
        topic_count=6,
        is_demo=True,
        sha256="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
        revision_number=1,
        is_latest_version=True,
        pipeline_version="2.0",
    )

    db.add(doc1)
    db.add(doc2)
    db.flush()

    # ── Create ExtractedFacts ─────────────────────────────────────────────────
    facts = []
    row_counter = 1

    def make_fact(metric_code, subsidiary, period, value, unit, doc_id,
                  sheet="Production Summary", row=None, col=None, cell=None,
                  page=None, human_verified=False, confidence=0.95):
        return ExtractedFact(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            metric_code=metric_code,
            metric_name=METRIC_NAMES[metric_code],
            numeric_value=value,
            unit=unit,
            subsidiary=subsidiary,
            reporting_period=period,
            sheet_name=sheet,
            row_number=row,
            column_name=col or metric_code,
            cell_reference=cell,
            page_number=page,
            source_context=f"{subsidiary} {METRIC_NAMES[metric_code]} for {period}: {value} {unit}",
            confidence_score=confidence,
            human_verified=human_verified,
            is_demo=True,
            extraction_method="table_parser",
            validation_status="valid",
        )

    # Production facts (primary document)
    for sub, periods in PRODUCTION_DATA.items():
        for period, val in periods.items():
            if val == 0.0 and sub == "CMPDI":
                continue
            facts.append(make_fact(
                "COAL_PRODUCTION", sub, period, val, "MT", doc1_id,
                sheet="Annual Production Statistics",
                row=row_counter, col="Raw Coal Production (MT)",
                cell=f"C{row_counter + 4}",
                page=12 + list(PRODUCTION_DATA.keys()).index(sub),
                human_verified=(period == "FY 2024-25"),
                confidence=0.97 if human_verified else 0.94,
            ))
            row_counter += 1

    # Production targets
    for sub, periods in TARGET_DATA.items():
        for period, val in periods.items():
            if val == 0.0:
                continue
            facts.append(make_fact(
                "PRODUCTION_TARGET", sub, period, val, "MT", doc1_id,
                sheet="Targets vs Actuals",
                row=row_counter, col="Production Target (MT)",
                cell=f"D{row_counter + 4}",
                page=45 + list(TARGET_DATA.keys()).index(sub),
                human_verified=False, confidence=0.93,
            ))
            row_counter += 1

    # OBR facts
    for sub, periods in OBR_DATA.items():
        for period, val in periods.items():
            facts.append(make_fact(
                "OVERBURDEN_REMOVAL", sub, period, val, "MCuM", doc1_id,
                sheet="Overburden Removal Data",
                row=row_counter, col="OBR (MCuM)",
                cell=f"E{row_counter + 4}",
                page=88 + list(OBR_DATA.keys()).index(sub),
                human_verified=False, confidence=0.92,
            ))
            row_counter += 1

    # Dispatch facts
    for sub, periods in DISPATCH_DATA.items():
        for period, val in periods.items():
            facts.append(make_fact(
                "COAL_DISPATCH", sub, period, val, "MT", doc1_id,
                sheet="Dispatch Statistics",
                row=row_counter, col="Coal Dispatch (MT)",
                cell=f"F{row_counter + 4}",
                page=122 + list(DISPATCH_DATA.keys()).index(sub),
                human_verified=False, confidence=0.93,
            ))
            row_counter += 1

    # CMPDI Drilling
    for sub, periods in DRILLING_DATA.items():
        for period, val in periods.items():
            facts.append(make_fact(
                "DRILLING_METERS", sub, period, val, "000 meters", doc1_id,
                sheet="CMPDI Exploration Data",
                row=row_counter, col="Drilling Meters (000)",
                cell=f"B{row_counter + 4}",
                page=198,
                human_verified=True, confidence=0.98,
            ))
            row_counter += 1

    # Stripping Ratio
    for sub, periods in STRIP_DATA.items():
        for period, val in periods.items():
            facts.append(make_fact(
                "STRIPPING_RATIO", sub, period, val, "m3/tonne", doc1_id,
                sheet="Stripping Ratio Analysis",
                row=row_counter, col="Stripping Ratio (m3/t)",
                cell=f"G{row_counter + 4}",
                page=165 + list(STRIP_DATA.keys()).index(sub),
                human_verified=False, confidence=0.90,
            ))
            row_counter += 1

    # ── Conflict document: SECL production with slightly different value ───────
    # This intentionally creates a discrepancy to demonstrate EvidenceConflict
    conflict_fact_id = str(uuid.uuid4())
    primary_fact = next(f for f in facts
                        if f.metric_code == "COAL_PRODUCTION"
                        and f.subsidiary == "SECL"
                        and f.reporting_period == "FY 2024-25")

    conflict_fact = ExtractedFact(
        id=conflict_fact_id,
        document_id=doc2_id,
        metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production",
        numeric_value=174.8,   # SECL subsidiary report says 174.8, CIL says 175.4 → conflict
        unit="MT",
        subsidiary="SECL",
        reporting_period="FY 2024-25",
        sheet_name="SECL Production Summary",
        row_number=8,
        column_name="Production (MT)",
        cell_reference="C8",
        page_number=4,
        source_context="SECL Raw Coal Production for FY 2024-25: 174.8 MT (subsidiary report)",
        confidence_score=0.93,
        human_verified=False,
        is_demo=True,
        extraction_method="table_parser",
        validation_status="conflict",
    )
    facts.append(conflict_fact)

    for f in facts:
        db.add(f)
    db.flush()

    # Update fact counts on documents
    doc1_count = sum(1 for f in facts if f.document_id == doc1_id)
    doc2_count = sum(1 for f in facts if f.document_id == doc2_id)
    db.query(Document).filter(Document.id == doc1_id).update({"fact_count": doc1_count})
    db.query(Document).filter(Document.id == doc2_id).update({"fact_count": doc2_count})

    # ── Create EvidenceConflict ───────────────────────────────────────────────
    conflict = EvidenceConflict(
        id=str(uuid.uuid4()),
        metric_code="COAL_PRODUCTION",
        subsidiary="SECL",
        reporting_period="FY 2024-25",
        primary_fact_id=primary_fact.id,
        conflicting_fact_id=conflict_fact_id,
        description=(
            "SECL Raw Coal Production for FY 2024-25: CIL Consolidated Report reports 175.4 MT, "
            "while SECL Subsidiary Production Report reports 174.8 MT. "
            "Discrepancy: 0.6 MT (0.34%)."
        ),
        discrepancy_percent=0.34,
        status="OPEN",
    )
    db.add(conflict)

    # Second conflict: OBR for MCL
    mcl_obr_primary = next(f for f in facts
                           if f.metric_code == "OVERBURDEN_REMOVAL"
                           and f.subsidiary == "MCL"
                           and f.reporting_period == "FY 2024-25")

    mcl_conflict_fact = ExtractedFact(
        id=str(uuid.uuid4()),
        document_id=doc2_id,
        metric_code="OVERBURDEN_REMOVAL",
        metric_name="Overburden Removal (OBR)",
        numeric_value=535.1,  # CIL says 538.4
        unit="MCuM",
        subsidiary="MCL",
        reporting_period="FY 2024-25",
        sheet_name="MCL OBR Data",
        row_number=12,
        column_name="OBR (MCuM)",
        cell_reference="E12",
        page_number=7,
        source_context="MCL Overburden Removal for FY 2024-25: 535.1 MCuM",
        confidence_score=0.91,
        human_verified=False,
        is_demo=True,
        extraction_method="table_parser",
        validation_status="conflict",
    )
    db.add(mcl_conflict_fact)
    db.flush()

    obr_conflict = EvidenceConflict(
        id=str(uuid.uuid4()),
        metric_code="OVERBURDEN_REMOVAL",
        subsidiary="MCL",
        reporting_period="FY 2024-25",
        primary_fact_id=mcl_obr_primary.id,
        conflicting_fact_id=mcl_conflict_fact.id,
        description=(
            "MCL Overburden Removal for FY 2024-25: CIL Consolidated Report reports 538.4 MCuM, "
            "subsidiary doc reports 535.1 MCuM. Discrepancy: 3.3 MCuM (0.61%)."
        ),
        discrepancy_percent=0.61,
        status="OPEN",
    )
    db.add(obr_conflict)

    # ── Create ValidationIssues ───────────────────────────────────────────────
    issues = [
        ValidationIssue(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            fact_id=primary_fact.id,
            issue_type="VALUE_CONFLICT",
            severity="HIGH",
            description="SECL FY 2024-25 production: 175.4 MT (CIL) vs 174.8 MT (SECL subsidiary report). Requires analyst reconciliation.",
            status="OPEN",
            subsidiary="SECL",
            reporting_period="FY 2024-25",
            metric_code="COAL_PRODUCTION",
            previous_value=174.8,
            proposed_value=175.4,
            previous_unit="MT",
            proposed_unit="MT",
            is_resolved=False,
        ),
        ValidationIssue(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            issue_type="UNIT_MISMATCH",
            severity="MEDIUM",
            description="OBR unit inconsistency: some records use 'BCuM' (billion cubic metres) instead of 'MCuM' (million). Standardised to MCuM.",
            status="RESOLVED",
            subsidiary="NCL",
            reporting_period="FY 2023-24",
            metric_code="OVERBURDEN_REMOVAL",
            is_resolved=True,
            resolved_by="reviewer_demo",
        ),
        ValidationIssue(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            issue_type="MISSING_PROVENANCE",
            severity="LOW",
            description="3 dispatch figures for Q3 FY 2024-25 lack cell references; extracted from PDF narrative (not table).",
            status="OPEN",
            subsidiary="WCL",
            reporting_period="FY 2024-25",
            metric_code="COAL_DISPATCH",
            is_resolved=False,
        ),
        ValidationIssue(
            id=str(uuid.uuid4()),
            document_id=doc2_id,
            issue_type="VALUE_CONFLICT",
            severity="HIGH",
            description="MCL OBR discrepancy: CIL consolidated (538.4 MCuM) vs MCL subsidiary doc (535.1 MCuM). Analyst review pending.",
            status="OPEN",
            subsidiary="MCL",
            reporting_period="FY 2024-25",
            metric_code="OVERBURDEN_REMOVAL",
            previous_value=535.1,
            proposed_value=538.4,
            previous_unit="MCuM",
            proposed_unit="MCuM",
            is_resolved=False,
        ),
        ValidationIssue(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            issue_type="TEMPORAL_OVERLAP",
            severity="MEDIUM",
            description="Both Q4 FY 2023-24 and annual FY 2023-24 figures found for ECL production. Annual record selected, quarterly suppressed to prevent double-counting.",
            status="RESOLVED",
            subsidiary="ECL",
            reporting_period="FY 2023-24",
            metric_code="COAL_PRODUCTION",
            is_resolved=True,
            resolved_by="analyst_demo",
        ),
    ]
    for issue in issues:
        db.add(issue)

    db.commit()

    total_facts = len(facts) + 1  # +1 for mcl_conflict_fact
    print(f"✅ Seeding complete!")
    print(f"   📄 Documents created: 2 (CIL Annual Report + SECL Subsidiary Report)")
    print(f"   📊 ExtractedFacts created: {total_facts}")
    print(f"   ⚠  EvidenceConflicts created: 2")
    print(f"   🔍 ValidationIssues created: {len(issues)}")
    print()
    print("Demo credentials:")
    print("  Analyst:  analyst_demo / Analyst@Demo2026")
    print("  Reviewer: reviewer_demo / Reviewer@Demo2026")
    print("  Admin:    admin_demo / Admin@Demo2026!")
    print()
    print("Sample queries to try in Ask MineIntel:")
    print('  "What was SECL raw coal production in FY 2024-25?"')
    print('  "Compare all subsidiaries coal production FY 2024-25"')
    print('  "Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25"')
    print('  "Verify claim: SECL produced 168 MT of raw coal in FY 2024-25"')
    print('  "What was CMPDI drilling meters in FY 2024-25?"')
    print('  "Show overburden removal for NCL in FY 2024-25"')


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
