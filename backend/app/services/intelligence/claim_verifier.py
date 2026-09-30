"""
Deterministic Claim Verification Engine.
Performs quantitative comparison of user claims against verified database facts.
Outputs verdicts: SUPPORTED, CONTRADICTED, PARTIALLY_SUPPORTED, INSUFFICIENT_EVIDENCE.
Never allows LLM hallucination for verification decisions.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.enums import ValidationStatus
from app.services.calculations.calculation_engine import CalculationEngine, EvidenceScope, AggOp
from app.services.intelligence.intents import AnswerStatus


class ClaimVerifier:
    """Verifies quantitative mining claims against the ground truth Evidence Ledger."""

    @classmethod
    def verify(
        cls,
        db: Session,
        query_text: str,
        entity_info: Dict[str, Any],
        period_info: Dict[str, Any],
        scope: str = "ALL_EVIDENCE",
        document_ids: Optional[List[str]] = None,
        only_verified: bool = False,
        include_demo: bool = False,
    ) -> Dict[str, Any]:
        """
        Parses claimed number and unit, queries verified facts, and deterministically computes delta.
        """
        subsidiary = entity_info.get("subsidiary")
        metric_code = entity_info.get("metric_code") or "COAL_PRODUCTION"
        metric_name = entity_info.get("metric_name") or "Coal Production"
        expected_unit = entity_info.get("unit") or "MT"
        period = period_info.get("period")

        # 1. Parse claimed value from query string
        claimed_val = cls._extract_claimed_number(query_text)
        if claimed_val is None:
            return {
                "status": "ERROR",
                "verdict": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": "Could not identify the specific numerical claim to verify. Please specify a figure (e.g. 'Verify claim: ECL production was 42.1 MT in FY 2024-25').",
                "citations": [],
                "records_used": 0,
            }

        # 2. Query evidence via NumberSafe EvidenceScope
        evidence_scope = EvidenceScope(
            metric_code=metric_code,
            subsidiary=subsidiary,
            reporting_period=period,
            only_verified=only_verified,
            only_real=not include_demo,
            only_demo=include_demo,
            document_ids=document_ids,
        )

        calc_res = CalculationEngine.calculate(db, evidence_scope, operation=AggOp.SUM)

        # If no facts found
        if not calc_res.success or calc_res.result is None:
            # Check if facts exist without period or with other filters
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "verdict": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": (
                    f"**Claim Verification:** Unable to verify claim of **{claimed_val} {expected_unit}**.\n\n"
                    f"No verified evidence exists in the repository for **{subsidiary or 'CIL'}** "
                    f"for metric `{metric_name}` ({metric_code})"
                    + (f" during period **{period}**." if period else ".")
                ),
                "claim": {
                    "subsidiary": subsidiary,
                    "metric": metric_name,
                    "claimed_value": claimed_val,
                    "unit": expected_unit,
                    "period": period,
                },
                "recorded_value": None,
                "difference": None,
                "difference_pct": None,
                "citations": [],
                "records_used": 0,
            }

        recorded_val = round(calc_res.result, 2)
        diff = round(claimed_val - recorded_val, 2)
        abs_diff = abs(diff)
        rel_diff_pct = round((abs_diff / max(0.0001, recorded_val)) * 100, 2)

        # 3. Deterministic Decision Thresholds: Exact/rounding match <= 0.05 MT is SUPPORTED.
        # Variance > 0.20 MT is CONTRADICTED (0.4 MT is 400,000 tonnes of coal).
        if abs_diff <= 0.05:
            verdict = AnswerStatus.SUPPORTED.value
            verdict_badge = "✓ SUPPORTED"
            verdict_color = "emerald"
            summary_msg = f"The claim of **{claimed_val} {expected_unit}** is **VERIFIED & SUPPORTED** by official records ({recorded_val} {expected_unit})."
        elif abs_diff <= 0.20:
            verdict = AnswerStatus.PARTIALLY_SUPPORTED.value
            verdict_badge = "⚠ PARTIALLY SUPPORTED"
            verdict_color = "amber"
            summary_msg = (
                f"The claim of **{claimed_val} {expected_unit}** is **PARTIALLY SUPPORTED** with a variance of {rel_diff_pct}%. "
                f"Official ledger records **{recorded_val} {expected_unit}** (variance of {diff:+} {expected_unit})."
            )
        else:
            verdict = AnswerStatus.CONTRADICTED.value
            verdict_badge = "✕ CONTRADICTED"
            verdict_color = "red"
            summary_msg = (
                f"The claim of **{claimed_val} {expected_unit}** is **CONTRADICTED** by verified evidence. "
                f"Official ledger records **{recorded_val} {expected_unit}**, indicating a discrepancy of **{diff:+} {expected_unit}** ({rel_diff_pct}% error)."
            )

        # Format Citations
        citations = []
        for inc in calc_res.included_facts:
            doc = db.query(Document).filter(Document.id == inc.document_id).first()
            doc_name = doc.original_filename if doc else "Mining Document"
            citations.append({
                "fact_id": inc.fact_id,
                "document_id": inc.document_id,
                "document_name": doc_name,
                "metric_code": inc.metric_code,
                "metric_name": metric_name,
                "numeric_value": inc.numeric_value,
                "unit": inc.unit or expected_unit,
                "subsidiary": inc.subsidiary,
                "reporting_period": inc.reporting_period,
                "page_number": inc.page_number,
                "sheet_name": inc.sheet_name,
                "cell_reference": inc.cell_reference,
                "source_context": inc.source_context,
                "confidence_score": inc.confidence_score,
                "human_verified": (inc.validation_status == ValidationStatus.VERIFIED.value),
            })

        answer_text = (
            f"### Claim Verification Audit\n\n"
            f"- **Claimed Figure:** **{claimed_val} {expected_unit}**\n"
            f"- **Official Recorded Value:** **{recorded_val} {expected_unit}**\n"
            f"- **Verdict:** **{verdict_badge}**\n"
            f"- **Discrepancy:** **{diff:+} {expected_unit}** ({rel_diff_pct}%)\n"
            f"- **Entity & Period:** {subsidiary or 'All CIL'} ({period or 'Latest'})\n\n"
            f"{summary_msg}\n\n"
            f"Verified against **{len(calc_res.included_facts)} official evidence records** in the Evidence Ledger."
        )

        return {
            "status": "SUCCESS",
            "verdict": verdict,
            "answer": answer_text,
            "claim": {
                "subsidiary": subsidiary,
                "metric": metric_name,
                "claimed_value": claimed_val,
                "unit": expected_unit,
                "period": period,
            },
            "recorded_value": recorded_val,
            "difference": diff,
            "difference_pct": rel_diff_pct,
            "citations": citations,
            "records_used": len(calc_res.included_facts),
            "calculation": f"|{claimed_val} - {recorded_val}| / {recorded_val} * 100 = {rel_diff_pct}%",
            "calculation_result": calc_res,
        }

    @classmethod
    def _extract_claimed_number(cls, text: str) -> Optional[float]:
        """Extracts the claimed quantitative number from query string."""
        # 1. Number immediately before unit
        m = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:mt|bcm|mm3|m|%|inr|cr|crore)\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1))

        # 2. Number after assertion verb
        m = re.search(r'\b(?:was|is|reached|achieved|stands at|produced|drilled|of)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m:
            return float(m.group(1))

        # 3. Any floating point / integer in the query
        m = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
        if m:
            return float(m.group(1))

        return None
