"""
Phase 10 — Parliamentary Query Mode API
Serves parliamentary-style briefings from grounded evidence.
"""
from fastapi import APIRouter, Depends, Query as FQuery
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.query_engine import NumberSafeQueryEngine
from app.providers.ai.gemini import get_ai_provider

router = APIRouter(prefix="/parliamentary", tags=["Parliamentary Brief"])


@router.post("/brief")
async def generate_parliamentary_brief(
    query: str = FQuery(..., description="Parliamentary question text"),
    period: str = FQuery("ALL", description="Reporting period (e.g. FY 2024-25)"),
    subsidiary: str = FQuery("ALL", description="Subsidiary (ALL for consolidated)"),
    db: Session = Depends(get_db),
):
    """
    Generates a parliamentary-style question brief with grounded evidence answer,
    supporting details table, citation appendix, and NumberSafe data integrity certificate.
    """
    full_query = query
    if period != "ALL" and period.lower() not in query.lower():
        full_query += f" in {period}"
    if subsidiary != "ALL" and subsidiary.lower() not in query.lower():
        full_query += f" for {subsidiary}"

    result = NumberSafeQueryEngine.execute(
        db=db,
        query_text=full_query,
        scope=f"{subsidiary}_EVIDENCE" if subsidiary != "ALL" else "ALL_EVIDENCE",
        response_mode="PARLIAMENTARY",
    )

    records_used = result.get("records_used", 0)
    confidence = result.get("confidence", 0.0)
    verification_status = result.get("verification_status", "UNKNOWN")
    answer_md = result.get("answer", "Insufficient evidence in the Evidence Ledger for this query.")
    citations = result.get("citations", [])

    numbersafe_status = (
        "DETERMINISTIC SQL — Zero LLM Hallucination" if records_used > 0
        else "INSUFFICIENT EVIDENCE — Manual review required"
    )

    subsidiary_label = subsidiary if subsidiary != "ALL" else "Coal India Limited (Consolidated)"

    # Synthesize official Ministry of Coal 5-section Parliamentary Brief via AI Provider
    ai_provider = get_ai_provider()
    supporting_context = [
        c.get("source_context", "") for c in citations if c.get("source_context")
    ]
    brief_markdown = await ai_provider.generate_parliamentary_brief(
        query=query,
        period=period,
        subsidiary=subsidiary_label,
        direct_answer=answer_md,
        verified_facts=citations,
        supporting_context=supporting_context,
        numbersafe_status=numbersafe_status,
        confidence_score=confidence,
        records_used=records_used,
        calculation_formula=result.get("sql_query") or result.get("calculation"),
    )

    gen_mode = "gemini_llm" if ai_provider.get_status().get("status") == "configured" else "extractive_no_llm"

    return {
        "query": query,
        "period": period,
        "subsidiary": subsidiary,
        "brief_text": brief_markdown,
        "answer_markdown": answer_md,
        "status": result.get("status", "SUCCESS"),
        "mode": gen_mode,
        "records_used": records_used,
        "confidence": confidence,
        "citations": citations,
        "direct_metric_value": result.get("direct_metric_value"),
        "metric_unit": result.get("metric_unit"),
        "calculation": result.get("calculation"),
        "verification_status": verification_status,
        "verification_result": result.get("verification_result", ""),
        "chart": result.get("chart"),
        "suggestions": result.get("suggestions", []),
        "calculation_steps": result.get("calculation_steps", []),
        "sql_query": result.get("sql_query", ""),
    }


@router.get("/sample-questions")
def get_sample_parliamentary_questions():
    """Returns pre-built sample parliamentary questions for the demo."""
    return {
        "questions": [
            {
                "id": "q1",
                "question": "What was the total raw coal production of Coal India Limited in FY 2024-25?",
                "period": "FY 2024-25",
                "subsidiary": "ALL",
                "category": "Production",
            },
            {
                "id": "q2",
                "question": "What is the target vs achievement for SECL coal production?",
                "period": "FY 2024-25",
                "subsidiary": "SECL",
                "category": "Target Achievement",
            },
            {
                "id": "q3",
                "question": "What was the overburden removal across all subsidiaries?",
                "period": "FY 2024-25",
                "subsidiary": "ALL",
                "category": "OBR",
            },
            {
                "id": "q4",
                "question": "How many meters of core drilling were completed by CMPDI?",
                "period": "FY 2024-25",
                "subsidiary": "CMPDI",
                "category": "Exploration",
            },
            {
                "id": "q5",
                "question": "What was NCL's coal dispatch in FY 2024-25?",
                "period": "FY 2024-25",
                "subsidiary": "NCL",
                "category": "Dispatch",
            },
        ]
    }
