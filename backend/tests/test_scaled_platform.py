import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

@pytest.fixture(scope="module", autouse=True)
def ensure_real_db():
    app.dependency_overrides.pop(get_db, None)
    yield
    app.dependency_overrides.pop(get_db, None)

client = TestClient(app)


def test_system_capabilities():
    response = client.get("/api/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["query_engine"] is True
    assert data["report_generation"] is True
    assert data["topic_intelligence"] is True
    assert data["semantic_search"] is True
    assert data["evidence_ledger"] is True


def test_system_settings_and_counts():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "MineIntel"
    assert "components" in data
    assert data["components"]["query_engine"]["status"] == "OPERATIONAL"
    assert data["components"]["report_generator"]["status"] == "OPERATIONAL"
    assert data["components"]["topic_intelligence"]["status"] == "OPERATIONAL"

    # Record counts from SQLite database
    counts = data.get("record_counts", {})
    assert counts.get("extracted_facts", 0) > 40000
    assert counts.get("documents", 0) > 300
    assert counts.get("discovered_topics", 0) >= 10


def test_analytics_overview():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert data["kpis"]["facts_extracted"] > 40000
    assert "multi_year_production_trends" in data
    assert len(data["multi_year_production_trends"]) > 0
    assert "target_vs_achievement" in data
    assert len(data["target_vs_achievement"]) > 0
    assert "confidence_distribution" in data


def test_numbersafe_query_subsidiary_production():
    response = client.post("/api/query", json={
        "query": "What was SECL's raw coal production in FY 2024-25?",
        "scope": "ALL_EVIDENCE",
        "response_mode": "STANDARD"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "SECL" in data["answer"]
    assert data["direct_metric_value"] is not None
    assert data["direct_metric_value"] > 0
    assert data["metric_unit"] == "MT"
    assert data["confidence_score"] > 0.8
    assert len(data["sources"]) > 0
    assert data["sources"][0]["document_name"] is not None


def test_numbersafe_query_comparison_chart():
    response = client.post("/api/query", json={
        "query": "Compare raw coal production across all subsidiaries in FY 2024-25",
        "scope": "ALL_EVIDENCE",
        "response_mode": "STANDARD"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["chart"] is not None
    assert data["chart"]["type"] in ["bar", "line"]
    assert len(data["chart"]["data"]) > 0


def test_numbersafe_claim_verification():
    response = client.post("/api/query", json={
        "query": "Verify claim: SECL produced 168.0 MT of raw coal in FY 2024-25",
        "scope": "ALL_EVIDENCE",
        "response_mode": "STANDARD"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["verification_result"] in ["SUPPORTED", "CONFLICTING", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE"]


def test_topic_intelligence():
    response = client.get("/api/topics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) >= 10
    assert len(data["top_keywords"]) > 0
    assert data["total_mentions"] > 1000

    topic_id = data["topics"][0]["id"]
    detail_response = client.get(f"/api/topics/{topic_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert "snippets" in detail_data
    assert len(detail_data["snippets"]) > 0


def test_review_queue_and_actions():
    response = client.get("/api/reviews?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["open_reviews"] > 0

    if data["items"]:
        issue = data["items"][0]
        issue_id = issue["id"]
        # Test edit and approve
        edit_res = client.post(f"/api/reviews/{issue_id}/edit-and-approve", json={
            "corrected_value": 45.5,
            "notes": "Automated test analyst verification"
        })
        assert edit_res.status_code == 200
        assert edit_res.json()["new_value"] == 45.5


def test_conflicts_and_resolution():
    response = client.get("/api/reviews/conflicts")
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert data["total"] > 0

    conflict = data["conflicts"][0]
    resolve_res = client.post(f"/api/reviews/conflicts/{conflict['id']}/resolve", json={
        "chosen_fact_id": conflict["fact_a_id"],
        "resolution_notes": "Test resolved to Fact A"
    })
    assert resolve_res.status_code == 200
    assert "resolved" in resolve_res.json()["message"].lower()


def test_report_generation_and_pdf_export():
    # 1. Pre-flight check
    guard_res = client.post("/api/reports/reportguard", json={
        "report_type": "Coal Production & Offtake Monthly Brief",
        "subsidiary": "SECL",
        "period": "FY 2024-25"
    })
    assert guard_res.status_code == 200
    guard_data = guard_res.json()
    assert guard_data["can_proceed"] is True
    assert guard_data["verified_evidence_ratio"] > 0.5

    # 2. Generate Report
    gen_res = client.post("/api/reports/generate", json={
        "title": "SECL Executive Production Brief (Test)",
        "report_type": "Coal Production & Offtake Monthly Brief",
        "subsidiary": "SECL",
        "period": "FY 2024-25"
    })
    assert gen_res.status_code == 200
    report_data = gen_res.json()
    report_id = report_data["id"]
    assert report_data["evidence_count"] > 0

    # 3. PDF Download
    pdf_res = client.get(f"/api/reports/{report_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # 4. CSV Download
    csv_res = client.get(f"/api/reports/{report_id}/export-csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "metric_code" in csv_res.text
