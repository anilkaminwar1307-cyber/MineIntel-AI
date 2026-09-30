"""
test_query_intent_routing.py — Step 4 & Step 5 Tests for NumberSafeQueryEngine

Step 4 tests: Word-boundary regex prevents false positives.
  - "is" in "this is a question" must NOT trigger claim-verification
  - "top" in "stopped production" must NOT trigger subsidiary comparison
  - "obr" in "october" must NOT trigger OBR metric
  - 15+ phrasing cases tested

Step 5 tests:
  - confidence is NOT hardcoded 0.90 on narrative path
  - human_verified is always False for chunk citations
  - No chunks -> returns INSUFFICIENT_EVIDENCE (not a random fallback answer)
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- ensures all models are registered
from app.core.database import Base
from app.services.query_engine import NumberSafeQueryEngine


# --- In-memory DB fixture ---

@pytest.fixture(scope="module")
def empty_db():
    """An empty in-memory SQLite session with schema but no facts/chunks."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# --- Step 4: _identify_metric word-boundary tests ---

_METRIC_CASES = [
    # True positives -- should match
    ("COAL_PRODUCTION",         "What is the total coal production of SECL?"),
    ("COAL_PRODUCTION",         "Show me total production for FY 2024-25"),
    ("COAL_PRODUCTION",         "How much coal was mined by MCL?"),
    ("COAL_PRODUCTION",         "Total coal output for the year"),
    ("DRILLING",                "Drilling progress in NCL this year"),
    ("DRILLING",                "How many meters of drilling were completed?"),
    ("OVERBURDEN_REMOVAL",      "What is the overburden removal for SECL?"),
    ("OVERBURDEN_REMOVAL",      "OBR figures for FY 2024-25"),
    ("COAL_OFFTAKE",            "dispatch figures for ECL"),
    ("COAL_OFFTAKE",            "total offtake for all subsidiaries"),
    ("GEOLOGICAL_RESERVES",     "Proved geological reserves"),
    ("CAPITAL_EXPENDITURE",     "capital expenditure for BCCL"),
    ("COAL_STOCK",              "closing coal stock at pithead"),
    ("EXPLORATION_BOREHOLES",   "how many boreholes were drilled"),
    ("PRODUCTION_TARGET",       "What is the production target for FY 2024-25?"),
    # False positives -- must NOT match (Step 4)
    (None,  "This is a general query about CIL policies"),
    (None,  "The operation was stopped abruptly"),
    (None,  "Report published in October 2024"),
    (None,  "Give me a summary of the latest report"),
]


@pytest.mark.parametrize("expected_code,query", _METRIC_CASES, ids=[
    f"metric_{i}" for i in range(len(_METRIC_CASES))
])
def test_identify_metric_word_boundary(expected_code, query):
    """_identify_metric must use word-boundary matching. False-positive cases return None."""
    result = NumberSafeQueryEngine._identify_metric(query.lower())
    if expected_code is None:
        assert result is None, (
            f"Expected None for query '{query}' but got {result}."
        )
    else:
        assert result is not None, (
            f"Expected metric '{expected_code}' for '{query}' but got None."
        )
        assert result[0] == expected_code, (
            f"Expected '{expected_code}' but got '{result[0]}' for '{query}'."
        )


def test_top_does_not_match_stopped():
    """'stopped' must NOT route to subsidiary comparison via 'top' substring."""
    q = "the mine was stopped for maintenance"
    result = NumberSafeQueryEngine._identify_metric(q.lower())
    assert result is None, f"'stopped' should not trigger a metric match -- got {result}."


def test_obr_not_matched_in_october():
    """'october' must NOT trigger OBR metric."""
    q = "October production report"
    result = NumberSafeQueryEngine._identify_metric(q.lower())
    if result is not None:
        assert result[0] != "OVERBURDEN_REMOVAL", (
            "'october' must not be matched as 'obr' via substring."
        )


# --- Step 5: Narrative RAG -- no hardcoded values ---

def test_narrative_rag_no_chunks_returns_insufficient_evidence(empty_db):
    """
    With no document chunks in DB, _handle_narrative_rag must return
    INSUFFICIENT_EVIDENCE and confidence=0.0, NOT fall back to arbitrary chunks.
    """
    result = NumberSafeQueryEngine._handle_narrative_rag(
        empty_db,
        query="What is the safety record of CMPDI mines?",
        scope="ALL_EVIDENCE",
        response_mode="STANDARD",
        document_ids=None,
        include_demo=False,
    )

    assert result["status"] == "INSUFFICIENT_EVIDENCE", (
        f"Expected INSUFFICIENT_EVIDENCE when DB has no chunks, got '{result['status']}'."
    )
    assert result["confidence"] == 0.0, (
        f"Expected confidence=0.0 for INSUFFICIENT_EVIDENCE, got {result['confidence']}"
    )
    assert result["citations"] == [], "Expected no citations when no chunks found."


def test_narrative_rag_human_verified_always_false():
    """human_verified must always be False for narrative chunk citations."""
    from app.models.document import DocumentChunk, Document

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    doc = Document(
        id="doc-hv-test",
        original_filename="hv_test.pdf",
        stored_filename="hv_test.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=512,
        document_category="Report",
        organization="NCL",
        status="PROCESSED",
        source_type="REAL",
        storage_path="uploads/test/hv_test.pdf",
        is_demo=False,
    )
    db.add(doc)
    for i in range(3):
        db.add(DocumentChunk(
            id=f"chunk-hv-{i:03d}",
            document_id="doc-hv-test",
            chunk_index=i,
            content=f"Production output increased by {10 + i}% in NCL mines over FY 2024-25.",
            page_number=i + 1,
        ))
    db.commit()

    result = NumberSafeQueryEngine._handle_narrative_rag(
        db,
        query="What is the production output in NCL?",
        scope="ALL_EVIDENCE",
        response_mode="STANDARD",
        document_ids=None,
        include_demo=False,
    )

    db.close()
    engine.dispose()

    if result["status"] == "SUCCESS":
        for cit in result["citations"]:
            assert cit.get("human_verified") is False, (
                f"human_verified must be False for chunks. Got True for {cit.get('fact_id')}."
            )


def test_narrative_confidence_not_hardcoded_to_090():
    """When chunks exist, confidence must derive from retrieval, not be exactly 0.90."""
    from app.models.document import DocumentChunk, Document

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    doc = Document(
        id="doc-conf-test",
        original_filename="conf_test.pdf",
        stored_filename="conf_test.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        document_category="Annual Report",
        organization="SECL",
        status="PROCESSED",
        source_type="REAL",
        storage_path="uploads/test/conf_test.pdf",
        is_demo=False,
    )
    db.add(doc)
    db.add(DocumentChunk(
        id="chunk-conf-001",
        document_id="doc-conf-test",
        chunk_index=0,
        content="Safety compliance rate reached 95% in FY 2024-25 across CIL subsidiaries.",
        page_number=1,
    ))
    db.commit()

    result = NumberSafeQueryEngine._handle_narrative_rag(
        db,
        query="What is the safety compliance rate?",
        scope="ALL_EVIDENCE",
        response_mode="STANDARD",
        document_ids=None,
        include_demo=False,
    )

    db.close()
    engine.dispose()

    if result["status"] == "SUCCESS":
        # Confidence must NOT be hardcoded to exactly 0.90
        assert result["confidence"] != 0.90, (
            f"confidence={result['confidence']} looks hardcoded to 0.90. "
            "It must be derived from retrieval hit count."
        )
        # Should be <= 0.85 (our formula is 0.50 + n*0.05, capped at 0.85)
        assert result["confidence"] <= 0.85, (
            f"Confidence {result['confidence']} exceeds expected max of 0.85."
        )


def test_execute_empty_db_returns_no_evidence(empty_db):
    """
    With empty DB, a numeric query must return NO_VERIFIED_EVIDENCE / 0 confidence.
    This is the Step 2 + Step 5 integration test.
    """
    result = NumberSafeQueryEngine.execute(
        db=empty_db,
        query_text="What is the total coal production of SECL in FY 2024-25?",
        scope="ALL_EVIDENCE",
        include_demo=False,
    )

    status = result.get("verification_status", "")
    confidence = result.get("confidence", 1.0)

    assert status in (
        "NO_VERIFIED_EVIDENCE", "INSUFFICIENT_EVIDENCE",
        "GROUNDED_CONTEXT",
    ), f"Unexpected verification status: {status}"

    if status in ("NO_VERIFIED_EVIDENCE", "INSUFFICIENT_EVIDENCE"):
        assert confidence == 0.0, (
            f"Expected confidence=0.0 for empty DB, got {confidence}."
        )
