"""
Tests for Phase 2 Document Intelligence Pipeline.
Verifies extractors, chunking, mining metric normalization, fact extraction,
confidence engine, quality assessment, and full pipeline processing.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.database import Base
from app.models.document import Document
from app.models.enums import DocumentStatus, FileType, ExtractionMethod
from app.models.fact import ExtractedFact
from app.services.mining.metric_registry import MiningMetricRegistry
from app.services.mining.period_normalizer import PeriodNormalizer
from app.services.mining.unit_normalizer import UnitNormalizer
from app.services.mining.org_normalizer import OrgNormalizer
from app.services.mining.entity_extractor import MiningEntityExtractor
from app.services.chunking.chunking_service import ChunkingService
from app.services.facts.confidence_engine import ConfidenceEngine
from app.services.facts.fact_extractor import FactExtractor
from app.services.pipeline.quality_assessment import QualityAssessmentService
from app.services.pipeline.document_processor import DocumentProcessor
from app.services.extractors.csv_extractor import CSVExtractor
from app.services.extractors.txt_extractor import TXTExtractor


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_metric_registry():
    # Production metric
    m = MiningMetricRegistry.find_metric("Raw Coal Production")
    assert m is not None
    assert m["code"] == "COAL_PRODUCTION"
    assert m["default_unit"] == "MT"

    # Alias matching
    m_alias = MiningMetricRegistry.find_metric("ob removal")
    assert m_alias is not None
    assert m_alias["code"] == "OVERBURDEN_REMOVAL"
    assert m_alias["default_unit"] == "Mm3"

    # Stripping ratio
    m_sr = MiningMetricRegistry.find_metric("stripping ratio")
    assert m_sr is not None
    assert m_sr["code"] == "STRIPPING_RATIO"


def test_period_normalizer():
    assert PeriodNormalizer.normalize_period("FY 2024-25") == "FY 2024-25"
    assert PeriodNormalizer.normalize_period("2024-25") == "FY 2024-25"
    assert PeriodNormalizer.normalize_period("2024/25") == "FY 2024-25"
    assert PeriodNormalizer.normalize_period("Q2 FY 2024-25") == "Q2 FY 2024-25"
    assert PeriodNormalizer.normalize_period("April 2024") == "Apr 2024"


def test_unit_normalizer():
    unit, _ = UnitNormalizer.normalize("167.5 MT")
    assert unit == "MT"

    unit, _ = UnitNormalizer.normalize("Million Tonnes")
    assert unit == "MT"

    unit, _ = UnitNormalizer.normalize("BCM")
    assert unit == "BCM"

    unit, _ = UnitNormalizer.normalize("meters")
    assert unit == "m"


def test_org_normalizer():
    assert OrgNormalizer.normalize_org("SECL") == "SECL"
    assert OrgNormalizer.normalize_org("south eastern coalfields limited") == "SECL"
    assert OrgNormalizer.normalize_org("CMPDI") == "CMPDI"
    assert OrgNormalizer.normalize_org("BCCL") == "BCCL"


def test_confidence_engine():
    score, rationale = ConfidenceEngine.calculate_confidence(
        extraction_method=ExtractionMethod.STRUCTURED_TABLE.value,
        has_metric=True,
        has_unit=True,
        has_period=True,
        has_subsidiary=True,
        document_quality_score=1.0
    )
    assert score >= 0.90
    assert "structured table" in rationale.lower()
    assert "canonical unit" in rationale.lower()


def test_chunking_service():
    sample_text = (
        "Coal India Limited (CIL) produced 773.6 MT of coal in FY 2023-24. "
        "South Eastern Coalfields Limited (SECL) was the largest contributor.\n\n"
        "Overburden removal stood at 1964.8 BCM across all subsidiaries."
    )
    chunks = ChunkingService.chunk_text(sample_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    assert all("chunk_hash" in c for c in chunks)
    assert all("content" in c for c in chunks)


def test_csv_extraction_and_facts():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("Subsidiary,Raw Coal Production,Overburden Removal,Reporting Period\n")
        f.write("SECL,167.0,245.5,FY 2023-24\n")
        f.write("MCL,193.2,189.0,FY 2023-24\n")
        temp_csv = f.name

    try:
        csv_res = CSVExtractor.extract(temp_csv)
        assert len(csv_res["tables"]) == 1
        assert csv_res["row_count"] == 2

        facts = FactExtractor.extract_from_tables(
            tables=csv_res["tables"],
            document_id="doc-test-123"
        )
        assert len(facts) >= 2

        # Check SECL fact
        secl_prod = next((f for f in facts if f["subsidiary"] == "SECL" and f["metric_code"] == "COAL_PRODUCTION"), None)
        assert secl_prod is not None
        assert secl_prod["numeric_value"] == 167.0
        assert secl_prod["unit"] == "MT"
        assert secl_prod["reporting_period"] == "FY 2023-24"

    finally:
        os.remove(temp_csv)


def test_text_fact_extraction():
    text = "In FY 2023-24, ECL achieved raw coal production of 35.40 MT across all open cast mines."
    facts = FactExtractor.extract_from_text(
        text=text,
        document_id="doc-text-456"
    )
    assert len(facts) >= 1
    fact = facts[0]
    assert fact["numeric_value"] == 35.40
    assert fact["unit"] == "MT"
    assert fact["subsidiary"] == "ECL"


def test_full_pipeline_csv_processing(test_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("Subsidiary,Raw Coal Production,Reporting Period\n")
        f.write("SECL,167.0,FY 2023-24\n")
        f.write("BCCL,40.1,FY 2023-24\n")
        temp_path = f.name

    try:
        doc = Document(
            id="doc-pipeline-test",
            original_filename="cil_production_report.csv",
            stored_filename="cil_production_report.csv",
            file_type=FileType.CSV.value,
            mime_type="text/csv",
            file_size=os.path.getsize(temp_path),
            storage_path=temp_path,
            status=DocumentStatus.UPLOADED.value
        )
        test_db.add(doc)
        test_db.commit()

        processed_doc = DocumentProcessor.process_document(test_db, doc.id)

        assert processed_doc.status == DocumentStatus.READY.value
        assert processed_doc.fact_count >= 2
        assert processed_doc.table_count == 1
        assert len(processed_doc.chunks) >= 1

        # Verify facts saved in DB
        db_facts = test_db.query(ExtractedFact).filter(ExtractedFact.document_id == doc.id).all()
        assert len(db_facts) >= 2
        secl = next(f for f in db_facts if f.subsidiary == "SECL")
        assert secl.numeric_value == 167.0
        assert secl.cell_reference is None or secl.row_number is not None

    finally:
        os.remove(temp_path)
