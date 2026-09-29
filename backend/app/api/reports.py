import os
import io
import csv
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.auth import require_analyst, require_admin
from app.models.report import GeneratedReport
from app.models.fact import ExtractedFact
from app.schemas.report import (
    GeneratedReportResponse, GeneratedReportListResponse, GenerateReportRequest, ReportGuardRequest
)
from app.services.report_generator import ReportGeneratorService

router = APIRouter(prefix="/reports", tags=["Report Studio"])

AVAILABLE_TEMPLATES = [
    "Production Summary",
    "Target vs Achievement",
    "Subsidiary Performance",
    "Exploration Summary",
    "Geological Overview",
    "Drilling Progress",
    "Reserve Overview",
    "Dispatch Summary",
    "Mine Safety",
    "Administrative Brief",
    "Parliamentary Brief",
    "Custom Report"
]


@router.get("", response_model=GeneratedReportListResponse)
def list_reports(db: Session = Depends(get_db)):
    """
    Lists existing generated reports and available report templates.
    """
    reports = db.query(GeneratedReport).order_by(desc(GeneratedReport.created_at)).all()
    return GeneratedReportListResponse(
        items=[GeneratedReportResponse.model_validate(r) for r in reports],
        total=len(reports),
        available_templates=AVAILABLE_TEMPLATES
    )


@router.get("/reportguard")
def check_reportguard_get(
    subsidiary: str = Query("ALL"),
    period: str = Query("ALL"),
    only_verified: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Runs pre-flight ReportGuard quality verification before generation (GET).
    """
    return ReportGeneratorService.run_reportguard(
        db=db,
        subsidiary=subsidiary,
        period=period,
        only_verified=only_verified
    )


@router.post("/reportguard")
def check_reportguard_post(
    req: ReportGuardRequest,
    db: Session = Depends(get_db)
):
    """
    Runs pre-flight ReportGuard quality verification before generation (POST).
    """
    return ReportGeneratorService.run_reportguard(
        db=db,
        subsidiary=req.subsidiary or "ALL",
        period=req.period or "ALL",
        only_verified=req.only_verified if req.only_verified is not None else True
    )


@router.post("/generate", response_model=GeneratedReportResponse)
def generate_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Generates a comprehensive 19-section mining report from grounded SQL evidence.
    Creates downloadable PDF and stores structured metrics and section content.
    Requires at minimum Analyst role.
    """
    title = request.title
    if not title:
        sub_label = request.subsidiary if request.subsidiary != "ALL" else "Consolidated CIL"
        title = f"{request.period} {sub_label} {request.report_type}"

    # Use authenticated user as the report author, fall back to request field
    generated_by = (
        request.generated_by
        or current_user.get("full_name")
        or current_user.get("username")
        or "CMPDI Senior Analyst"
    )

    try:
        report = ReportGeneratorService.generate_report(
            db=db,
            title=title,
            report_type=request.report_type,
            subsidiary=request.subsidiary,
            period=request.period,
            document_ids=request.document_ids,
            only_verified=request.only_verified,
            generated_by=generated_by,
            draft_override=request.draft_override
        )
        return GeneratedReportResponse.model_validate(report)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/{report_id}", response_model=GeneratedReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Retrieves full metadata and section JSON for an existing report."""
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return GeneratedReportResponse.model_validate(report)


@router.get("/{report_id}/claims", summary="Get claims asserted in report")
def get_report_claims(report_id: str, db: Session = Depends(get_db)):
    """
    EvidenceChain 2.0: Returns all claims made in this report with their support statuses.
    """
    import json
    from app.models.claim import Claim, ClaimEvidenceLink

    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    claims = db.query(Claim).filter(Claim.report_id == report_id).all()
    out = []
    for c in claims:
        links = db.query(ClaimEvidenceLink).filter(ClaimEvidenceLink.claim_id == c.id).all()
        out.append({
            "id": c.id,
            "claim_type": c.claim_type,
            "text": c.text,
            "support_status": c.support_status,
            "confidence": c.confidence,
            "evidence_links": [
                {
                    "link_id": l.id,
                    "fact_id": l.fact_id,
                    "calculation_id": l.calculation_id,
                    "relationship_type": l.relationship_type
                }
                for l in links
            ]
        })
    return {"report_id": report_id, "claims": out, "total": len(out)}


@router.get("/{report_id}/claims/{claim_id}/evidence", summary="Get evidence behind a report claim")
def get_report_claim_evidence(report_id: str, claim_id: str, db: Session = Depends(get_db)):
    """
    EvidenceChain 2.0: Deep trace from a report claim back to its supporting facts and calculation runs.
    """
    from app.models.claim import Claim, ClaimEvidenceLink
    from app.services.evidence.provenance_service import ProvenanceService

    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.report_id == report_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found in this report.")

    links = db.query(ClaimEvidenceLink).filter(ClaimEvidenceLink.claim_id == claim.id).all()
    facts_provenance = []
    for link in links:
        if link.fact_id:
            try:
                prov = ProvenanceService.get_fact_provenance(db, link.fact_id)
                facts_provenance.append(prov)
            except Exception:
                pass

    return {
        "claim": {
            "id": claim.id,
            "type": claim.claim_type,
            "text": claim.text,
            "support_status": claim.support_status,
            "confidence": claim.confidence
        },
        "evidence_facts": facts_provenance,
        "calculation_id": links[0].calculation_id if links and links[0].calculation_id else None
    }


@router.get("/{report_id}/evidence-register", summary="Get Evidence Register for report")
def get_report_evidence_register(report_id: str, db: Session = Depends(get_db)):
    """
    EvidenceChain 2.0: Returns complete tabular Evidence Register linking report numbers to source coordinates.
    """
    import json
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    register = []
    if report.content_json:
        try:
            content = json.loads(report.content_json)
            register = content.get("evidence_register", [])
        except Exception:
            pass

    return {
        "report_id": report_id,
        "report_title": report.title,
        "evidence_register": register,
        "total": len(register)
    }


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: str, db: Session = Depends(get_db)):
    """Downloads official A4 PDF compiled for the report."""
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if not report.output_path or not os.path.exists(report.output_path):
        # Regenerate on demand if needed
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")

    filename = os.path.basename(report.output_path)
    return FileResponse(
        path=report.output_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/{report_id}/export-csv")
def export_report_evidence_csv(report_id: str, db: Session = Depends(get_db)):
    """
    Exports the specific evidence facts referenced by this report as CSV.
    Only exports facts linked to THIS report (by parameters / evidence_register),
    not the global first-1000 facts.
    """
    import json
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Try to load fact IDs from evidence_register stored in content_json
    fact_ids = []
    if report.content_json:
        try:
            content = json.loads(report.content_json)
            register = content.get("evidence_register", [])
            fact_ids = [r.get("fact_id") for r in register if r.get("fact_id")]
        except Exception:
            pass

    # Fall back to report-scoped parameters if no register
    if fact_ids:
        facts = db.query(ExtractedFact).filter(ExtractedFact.id.in_(fact_ids)).all()
    else:
        # Scope query by report parameters (subsidiary/period if available in parameters)
        params = {}
        if report.parameters:
            try:
                params = json.loads(report.parameters)
            except Exception:
                pass
        q = db.query(ExtractedFact)
        if params.get("subsidiary") and params["subsidiary"] != "ALL":
            q = q.filter(ExtractedFact.subsidiary == params["subsidiary"])
        if params.get("period") and params["period"] != "ALL":
            q = q.filter(ExtractedFact.reporting_period.like(f"%{params['period']}%"))
        facts = q.limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "fact_id", "metric_code", "metric_name", "numeric_value", "unit",
        "subsidiary", "mine", "coalfield", "reporting_period",
        "temporal_grain", "confidence_score", "validation_status",
        "human_verified", "is_demo",
        "document_id", "page_number", "sheet_name", "cell_reference",
        "row_number", "column_name", "table_reference", "source_context"
    ])

    for f in facts:
        writer.writerow([
            f.id, f.metric_code, f.metric_name, f.numeric_value, f.unit,
            f.subsidiary, f.mine, f.coalfield, f.reporting_period,
            f.temporal_grain, f.confidence_score, f.validation_status,
            f.human_verified, f.is_demo,
            f.document_id, f.page_number, f.sheet_name, f.cell_reference,
            f.row_number, f.column_name, f.table_reference, f.source_context
        ])

    csv_data = output.getvalue()
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in (report.title or report_id))[:60]
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evidence_{safe_title}.csv"}
    )


@router.delete("/{report_id}", summary="Delete a generated report")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Deletes a generated report record and its associated PDF file.
    Requires Admin role. Creates an immutable AuditEvent before deletion.
    Returns 404 if not found; idempotent if file is already missing.
    """
    from app.models.audit import AuditEvent
    from app.models.enums import AuditAction

    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Write audit event BEFORE deletion so the record exists
    audit = AuditEvent(
        user=current_user.get("username", "Admin"),
        action=AuditAction.DOCUMENT_DELETED.value,
        entity_type="GENERATED_REPORT",
        entity_id=report_id,
        details=f"Report '{report.title}' (type={report.report_type}) deleted. "
                f"PDF path={report.output_path}."
    )
    db.add(audit)

    # Delete PDF file safely
    for path_field in [report.output_path, report.pdf_path]:
        if path_field and os.path.exists(path_field):
            try:
                os.remove(path_field)
            except OSError:
                pass  # File already gone — idempotent

    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully.", "id": report_id}


