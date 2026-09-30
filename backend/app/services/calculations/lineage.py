"""
NumberSafe 2.0 — Calculation Lineage Persistence
Stores every CalculationRun and its CalculationInput rows so that
every derived value in MineIntel is reproducible and auditable.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.calculations.calculation_engine import CalculationResult


def persist_calculation(
    db: Session,
    result: "CalculationResult",
    operation: str,
    initiated_by: str = "system",
) -> Optional[str]:
    """
    Persists a CalculationResult to the calculation_runs and
    calculation_inputs tables.  Returns the lineage ID (UUID str).
    Safe to call — never raises; returns None on any DB error.
    """
    try:
        from app.models.calculation import CalculationRun, CalculationInput

        run_id = str(uuid.uuid4())
        warnings_json = json.dumps(result.warnings) if result.warnings else "[]"

        run = CalculationRun(
            id=run_id,
            operation=operation,
            metric_code=result.metric_code,
            filters_json=json.dumps(result.filters_applied),
            result=result.result,
            unit=result.unit,
            evidence_count=result.evidence_count_total,
            evidence_used_count=result.evidence_count_used,
            verified_count=result.verified_count,
            excluded_count=result.excluded_count,
            verified_pct=result.verified_pct,
            confidence=result.verified_pct / 100.0 if result.verified_pct else None,
            warnings_json=warnings_json,
            is_demo_scope=result.is_demo_scope,
            error_code=result.error_code,
            formula=result.formula,
            calculation_method=result.calculation_method,
            sql_description=result.sql_description,
            success=result.success,
            initiated_by=initiated_by,
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)

        # Insert calculation inputs (included facts)
        for inc in result.included_facts:
            db.add(CalculationInput(
                id=str(uuid.uuid4()),
                calculation_id=run_id,
                fact_id=inc.fact_id,
                inclusion_status="INCLUDED",
                exclusion_reason=None,
                weight=None,
            ))

        # Insert excluded facts
        for exc in result.exclusions:
            db.add(CalculationInput(
                id=str(uuid.uuid4()),
                calculation_id=run_id,
                fact_id=exc.fact_id,
                inclusion_status="EXCLUDED",
                exclusion_reason=exc.reason,
                weight=None,
            ))

        db.flush()
        result.lineage_id = run_id
        return run_id

    except Exception as exc:
        logger.warning(f"[Lineage] Failed to persist calculation: {exc}")
        db.rollback()
        return None


def get_lineage(db: Session, lineage_id: str) -> Optional[dict]:
    """Retrieves a full CalculationRun + inputs as a structured dict."""
    try:
        from app.models.calculation import CalculationRun, CalculationInput

        run = db.query(CalculationRun).filter(CalculationRun.id == lineage_id).first()
        if not run:
            return None

        inputs = (
            db.query(CalculationInput)
            .filter(CalculationInput.calculation_id == lineage_id)
            .all()
        )

        included = [
            {"fact_id": inp.fact_id, "weight": inp.weight}
            for inp in inputs if inp.inclusion_status == "INCLUDED"
        ]
        excluded = [
            {"fact_id": inp.fact_id, "reason": inp.exclusion_reason}
            for inp in inputs if inp.inclusion_status == "EXCLUDED"
        ]

        return {
            "id": run.id,
            "operation": run.operation,
            "metric_code": run.metric_code,
            "filters": json.loads(run.filters_json or "{}"),
            "result": run.result,
            "unit": run.unit,
            "formula": run.formula,
            "calculation_method": run.calculation_method,
            "sql_description": run.sql_description,
            "success": run.success,
            "error_code": run.error_code,
            "evidence_count": run.evidence_count,
            "evidence_used_count": run.evidence_used_count,
            "verified_count": run.verified_count,
            "excluded_count": run.excluded_count,
            "verified_pct": run.verified_pct,
            "is_demo_scope": run.is_demo_scope,
            "warnings": json.loads(run.warnings_json or "[]"),
            "initiated_by": run.initiated_by,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "included_facts": included,
            "excluded_facts": excluded,
        }

    except Exception as exc:
        logger.warning(f"[Lineage] Failed to retrieve lineage {lineage_id}: {exc}")
        return None
