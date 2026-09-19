import os
import io
import csv
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
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
def generate_report(request: GenerateReportRequest, db: Session = Depends(get_db)):
    """
    Generates a comprehensive 19-section mining report from grounded SQL evidence.
    Creates downloadable PDF and stores structured metrics and section content.
    """
    title = request.title
    if not title:
        sub_label = request.subsidiary if request.subsidiary != "ALL" else "Consolidated CIL"
        title = f"{request.period} {sub_label} {request.report_type}"

    try:
        report = ReportGeneratorService.generate_report(
            db=db,
            title=title,
            report_type=request.report_type,
            subsidiary=request.subsidiary,
            period=request.period,
            document_ids=request.document_ids,
            only_verified=request.only_verified,
            generated_by=request.generated_by or "CMPDI Senior Analyst"
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
    Exports full underlying evidence facts behind this report as CSV.
    """
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    facts = db.query(ExtractedFact).limit(1000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "fact_id", "metric_code", "metric_name", "numeric_value", "unit",
        "subsidiary", "mine", "coalfield", "reporting_period", "confidence_score",
        "validation_status", "sheet_name", "cell_reference", "page_number"
    ])

    for f in facts:
        writer.writerow([
            f.id, f.metric_code, f.metric_name, f.numeric_value, f.unit,
            f.subsidiary, f.mine, f.coalfield, f.reporting_period, f.confidence_score,
            f.validation_status, f.sheet_name, f.cell_reference, f.page_number
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evidence_{report_id}.csv"}
    )

