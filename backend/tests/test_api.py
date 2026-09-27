import os
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

from sqlalchemy.pool import StaticPool

# Use an isolated in-memory SQLite test database
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["storage"] == "available"
    assert data["gemini"] in ["configured", "not_configured"]
    assert data["app_name"] == "MineIntel"
    assert data["version"] in ["0.1.0", "0.2.0"]  # Accept current version


def test_system_capabilities(client):
    response = client.get("/api/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["document_upload"] is True
    assert data["evidence_ledger"] is True
    assert data["pdf_extraction"] is True
    assert data["spreadsheet_processing"] is True
    assert data["document_enhancement"] is True
    assert data["query_engine"] is True


def test_document_upload_and_lifecycle(client):
    # 1. Upload a CSV file
    csv_content = b"Subsidiary,Mine,Reporting_Period,Coal_Production_MT\nECL,Rajmahal,2024-Q2,12.5\nBCCL,Jharia_Block_II,2024-Q2,8.4\n"
    file_payload = {
        "file": ("sample_production.csv", io.BytesIO(csv_content), "text/csv")
    }
    data_payload = {
        "document_category": "Production Report",
        "organization": "Coal India Limited",
        "reporting_period": "2024-Q2"
    }

    upload_resp = client.post("/api/documents/upload", files=file_payload, data=data_payload)
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    assert "document" in upload_data
    doc = upload_data["document"]
    assert doc["original_filename"] == "sample_production.csv"
    assert doc["file_type"] == "CSV"
    assert doc["status"] == "UPLOADED"
    doc_id = doc["id"]

    # 2. Verify Document appears in Document List
    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    matched = [d for d in list_data["items"] if d["id"] == doc_id]
    assert len(matched) == 1

    # 3. Retrieve Document Details by ID
    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == doc_id

    # 4. Verify Audit Event was created for upload
    audit_resp = client.get("/api/audit")
    assert audit_resp.status_code == 200
    audit_items = audit_resp.json()["items"]
    assert any(a["action"] == "DOCUMENT_UPLOADED" and a["entity_id"] == doc_id for a in audit_items)

    # 5. Delete Document
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200

    # 6. Confirm Document is deleted
    get_after_del = client.get(f"/api/documents/{doc_id}")
    assert get_after_del.status_code == 404

    # 7. Confirm DOCUMENT_DELETED audit event
    audit_resp2 = client.get("/api/audit")
    audit_items2 = audit_resp2.json()["items"]
    assert any(a["action"] == "DOCUMENT_DELETED" and a["entity_id"] == doc_id for a in audit_items2)


def test_unsupported_upload(client):
    exe_content = b"fake binary executable content"
    file_payload = {
        "file": ("malicious_script.exe", io.BytesIO(exe_content), "application/x-msdownload")
    }
    resp = client.post("/api/documents/upload", files=file_payload)
    assert resp.status_code == 400
    assert "Unsupported file extension" in resp.json()["detail"]


def test_evidence_ledger_empty_and_valid(client):
    response = client.get("/api/evidence")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "verified_count" in data
    assert isinstance(data["items"], list)


def test_analytics_overview(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "documents_processed" in data["kpis"]
    assert "facts_extracted" in data["kpis"]


def test_reports_listing(client):
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    assert "available_templates" in data
    assert "Production Summary" in data["available_templates"]


def test_settings_status(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert data["components"]["backend_api"]["status"] == "OPERATIONAL"
    assert data["components"]["database"]["status"] == "OPERATIONAL"
    assert data["components"]["storage"]["status"] == "OPERATIONAL"
    assert data["components"]["pdf_processor"]["status"] == "OPERATIONAL"
    assert data["components"]["spreadsheet_processor"]["status"] == "OPERATIONAL"
    assert data["components"]["document_enhancement"]["status"] == "OPERATIONAL"
    assert data["components"]["ocr_engine"]["status"] in ("OPERATIONAL", "UNAVAILABLE")
