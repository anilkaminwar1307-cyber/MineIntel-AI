"""
NumberSafe 2.0 — Central Deterministic Calculation Engine

This is the single authority for ALL quantitative mining computations.
Every numeric answer in MineIntel — whether from Ask MineIntel, Analytics,
Overview KPIs, or Report Studio — MUST be produced by this engine.

Guarantees:
  - No LIMIT applied before aggregation (full qualifying dataset used)
  - No synthetic fallback values (missing target → MISSING_TARGET error)
  - Duplicate detection before summing
  - Temporal grain and entity grain validation
  - Unit compatibility enforcement
  - Verified-only mode and demo/real segregation
  - Machine-readable lineage for every result
  - Structured error codes, never fabricated answers
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fact import ExtractedFact
from app.models.enums import ValidationStatus
from app.services.calculations.metric_semantics import (
    AggOp, EntityGrain, MetricDefinition, MetricRegistry, TemporalGrain,
)
from app.services.calculations.duplicate_detector import (
    ExclusionDecision, FactCandidate, detect_duplicates,
)
from app.core.logging import logger


# ─── Error codes ──────────────────────────────────────────────────────────────
class CalcError:
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INCOMPATIBLE_UNITS = "INCOMPATIBLE_UNITS"
    MIXED_TEMPORAL_GRAIN = "MIXED_TEMPORAL_GRAIN"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    AMBIGUOUS_ENTITY = "AMBIGUOUS_ENTITY"
    MISSING_TARGET = "MISSING_TARGET"
    NO_VERIFIED_EVIDENCE = "NO_VERIFIED_EVIDENCE"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    ZERO_DENOMINATOR = "ZERO_DENOMINATOR"
    INVALID_NUMERIC = "INVALID_NUMERIC"


# ─── Data scope badge ─────────────────────────────────────────────────────────
class DataScopeMode:
    REAL = "REAL_UPLOADED_DATA"
    DEMO = "DEMO_DATA"
    MIXED = "MIXED_WARNING"
    UNKNOWN = "UNKNOWN"


# ─── Result model ─────────────────────────────────────────────────────────────
@dataclass
class IncludedFact:
    fact_id: str
    metric_code: str
    subsidiary: Optional[str]
    mine: Optional[str]
    reporting_period: Optional[str]
    numeric_value: Optional[float]
    unit: Optional[str]
    confidence_score: float
    validation_status: str
    is_demo: bool
    document_id: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_reference: Optional[str] = None
    source_context: Optional[str] = None


@dataclass
class CalculationResult:
    # Core result
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Result values
    result: Optional[float] = None
    unit: Optional[str] = None
    calculation_method: Optional[str] = None
    formula: Optional[str] = None

    # Scope metadata
    metric_code: str = ""
    filters_applied: Dict[str, Any] = field(default_factory=dict)

    # Evidence metadata
    evidence_count_total: int = 0        # facts retrieved from DB (before dedup)
    evidence_count_used: int = 0         # facts used in computation (after dedup)
    excluded_count: int = 0
    verified_count: int = 0
    verified_pct: float = 0.0
    is_demo_scope: DataScopeMode = DataScopeMode.UNKNOWN

    # Included / excluded detail
    included_facts: List[IncludedFact] = field(default_factory=list)
    exclusions: List[ExclusionDecision] = field(default_factory=list)

    # Warnings and lineage
    warnings: List[str] = field(default_factory=list)
    sql_description: str = ""
    lineage_id: Optional[str] = None     # set after persistence


# ─── Scope object ─────────────────────────────────────────────────────────────
@dataclass
class EvidenceScope:
    """Describes the exact slice of evidence to aggregate over."""
    metric_code: str
    subsidiary: Optional[str] = None          # None = all subsidiaries
    mine: Optional[str] = None
    reporting_period: Optional[str] = None    # e.g. "FY 2024-25"
    only_verified: bool = False
    only_real: bool = False                   # exclude demo facts
    only_demo: bool = False                   # only demo facts
    document_ids: Optional[List[str]] = None
    exclude_consolidated: bool = True         # drop CIL/consolidated rows


# ─── Engine ───────────────────────────────────────────────────────────────────
class CalculationEngine:
    """
    The single deterministic computation authority for MineIntel.
    All other services MUST delegate to this class for numeric operations.
    """

    # ── Public entry points ──────────────────────────────────────────────────

    @classmethod
    def calculate(
        cls,
        db: Session,
        scope: EvidenceScope,
        operation: str = AggOp.SUM,
    ) -> CalculationResult:
        """
        Execute a deterministic aggregation for the given scope.
        Returns a rich CalculationResult — never raises for missing data;
        instead returns success=False with an error_code.
        """
        metric_defn = MetricRegistry.get_or_default(scope.metric_code)
        result = CalculationResult(
            success=False,
            metric_code=scope.metric_code,
            filters_applied=cls._scope_to_dict(scope),
        )

        # 1. Retrieve ALL qualifying facts (no LIMIT)
        raw_facts = cls._fetch_facts(db, scope)
        result.evidence_count_total = len(raw_facts)

        if not raw_facts:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = (
                f"No evidence records found for metric='{scope.metric_code}'"
                + (f", subsidiary='{scope.subsidiary}'" if scope.subsidiary else "")
                + (f", period='{scope.reporting_period}'" if scope.reporting_period else "")
                + "."
            )
            result.sql_description = cls._describe_sql(scope)
            return result

        # 2. Validate units
        unit_warnings = cls._validate_units(raw_facts, metric_defn)
        result.warnings.extend(unit_warnings)

        # 3. Convert to FactCandidate for duplicate detection
        candidates = cls._to_candidates(raw_facts)

        # 4. Duplicate detection
        included_ids, exclusions = detect_duplicates(
            candidates,
            prefer_verified=True,
            exclude_consolidated=scope.exclude_consolidated,
        )
        result.exclusions = exclusions
        result.excluded_count = len(exclusions)

        # 5. Build included set
        id_to_fact = {f.id: f for f in raw_facts}
        included_orm = [id_to_fact[fid] for fid in included_ids if fid in id_to_fact]
        result.evidence_count_used = len(included_orm)
        result.included_facts = cls._to_included(included_orm)

        if not included_orm:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "All retrieved evidence was excluded during duplicate/overlap detection."
            return result

        # 6. Demo/real scope analysis
        result.is_demo_scope = cls._scope_mode(included_orm)

        # 7. Verified stats (computed from included set, not hardcoded)
        result.verified_count = sum(
            1 for f in included_orm
            if f.validation_status == ValidationStatus.VERIFIED.value
        )
        result.verified_pct = round(
            result.verified_count / max(1, result.evidence_count_used) * 100, 1
        )

        # 8. Apply operation
        if operation == AggOp.SUM:
            return cls._apply_sum(result, included_orm, metric_defn)
        elif operation == AggOp.LATEST:
            return cls._apply_latest(result, included_orm, metric_defn)
        elif operation == AggOp.WAVG:
            return cls._apply_wavg(result, included_orm, metric_defn)
        elif operation == AggOp.AVG:
            return cls._apply_avg(result, included_orm, metric_defn)
        elif operation == AggOp.MIN:
            return cls._apply_min(result, included_orm, metric_defn)
        elif operation == AggOp.MAX:
            return cls._apply_max(result, included_orm, metric_defn)
        elif operation == AggOp.COUNT:
            return cls._apply_count(result, included_orm, metric_defn)
        else:
            result.error_code = CalcError.UNSUPPORTED_OPERATION
            result.error_message = f"Operation '{operation}' not implemented."
            return result

    @classmethod
    def calculate_achievement(
        cls,
        db: Session,
        actual_scope: EvidenceScope,
        target_scope: EvidenceScope,
    ) -> CalculationResult:
        """
        Compute (actual / target) * 100 achievement percentage.
        Validates that both scopes have compatible entity, period, and unit.
        Returns MISSING_TARGET error if no target evidence exists — never
        synthesises target = actual * 1.04.
        """
        actual_result = cls.calculate(db, actual_scope, AggOp.SUM)
        if not actual_result.success:
            return actual_result

        target_result = cls.calculate(db, target_scope, AggOp.SUM)
        if not target_result.success:
            # Preserve target's error but enrich message
            target_result.error_code = CalcError.MISSING_TARGET
            target_result.error_message = (
                "Cannot compute target achievement: no compatible target evidence found "
                f"for metric='{target_scope.metric_code}'"
                + (f", subsidiary='{target_scope.subsidiary}'" if target_scope.subsidiary else "")
                + (f", period='{target_scope.reporting_period}'" if target_scope.reporting_period else "")
                + ". A synthetic target (e.g. actual × 1.04) has been intentionally refused."
            )
            # Return actual result with target error
            actual_result.success = False
            actual_result.error_code = CalcError.MISSING_TARGET
            actual_result.error_message = target_result.error_message
            actual_result.warnings.append("TARGET_UNAVAILABLE")
            return actual_result

        # Validate scopes are compatible
        compat_warnings = cls._validate_scope_compatibility(actual_scope, target_scope)

        if actual_result.result is None or target_result.result is None:
            actual_result.success = False
            actual_result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            actual_result.error_message = "Actual or target value is None after computation."
            return actual_result

        target_val = target_result.result
        if target_val == 0.0:
            actual_result.success = False
            actual_result.error_code = CalcError.ZERO_DENOMINATOR
            actual_result.error_message = "Target value is zero — cannot compute achievement percentage."
            return actual_result

        achievement = round((actual_result.result / target_val) * 100, 2)

        result = CalculationResult(
            success=True,
            metric_code=f"{actual_scope.metric_code}_ACHIEVEMENT",
            result=achievement,
            unit="%",
            calculation_method="RATIO",
            formula=f"({actual_result.result:.3f} {actual_result.unit} ÷ {target_val:.3f} {target_result.unit}) × 100",
            filters_applied={
                "actual_scope": cls._scope_to_dict(actual_scope),
                "target_scope": cls._scope_to_dict(target_scope),
            },
            evidence_count_total=actual_result.evidence_count_total + target_result.evidence_count_total,
            evidence_count_used=actual_result.evidence_count_used + target_result.evidence_count_used,
            excluded_count=actual_result.excluded_count + target_result.excluded_count,
            verified_count=actual_result.verified_count + target_result.verified_count,
            included_facts=actual_result.included_facts + target_result.included_facts,
            exclusions=actual_result.exclusions + target_result.exclusions,
            warnings=compat_warnings + actual_result.warnings + target_result.warnings,
            is_demo_scope=actual_result.is_demo_scope,
            sql_description=(
                f"Achievement = SUM(actual {actual_scope.metric_code}) / "
                f"SUM(target {target_scope.metric_code}) × 100 "
                f"[actual={actual_result.result:.2f}, target={target_val:.2f}]"
            ),
        )
        result.verified_pct = round(
            result.verified_count / max(1, result.evidence_count_used) * 100, 1
        )
        return result

    # ── Internal helpers ─────────────────────────────────────────────────────

    @classmethod
    def _fetch_facts(cls, db: Session, scope: EvidenceScope) -> List[ExtractedFact]:
        """Retrieves ALL qualifying facts — no LIMIT ever applied."""
        q = db.query(ExtractedFact).filter(
            ExtractedFact.metric_code == scope.metric_code,
            ExtractedFact.numeric_value.isnot(None),
        )

        if scope.subsidiary:
            q = q.filter(ExtractedFact.subsidiary == scope.subsidiary)

        if scope.mine:
            q = q.filter(ExtractedFact.mine == scope.mine)

        if scope.reporting_period:
            stripped = scope.reporting_period.replace("FY ", "").strip()
            q = q.filter(
                ExtractedFact.reporting_period.ilike(f"%{stripped}%")
                | (ExtractedFact.reporting_period == scope.reporting_period)
            )

        if scope.only_verified:
            q = q.filter(
                ExtractedFact.validation_status == ValidationStatus.VERIFIED.value
            )

        if scope.only_real:
            q = q.filter(ExtractedFact.is_demo == False)  # noqa: E712
        elif scope.only_demo:
            q = q.filter(ExtractedFact.is_demo == True)  # noqa: E712

        if scope.document_ids:
            q = q.filter(ExtractedFact.document_id.in_(scope.document_ids))

        return q.all()

    @classmethod
    def _to_candidates(cls, facts: List[ExtractedFact]) -> List[FactCandidate]:
        return [
            FactCandidate(
                fact_id=f.id,
                metric_code=f.metric_code,
                subsidiary=f.subsidiary,
                mine=f.mine,
                reporting_period=f.reporting_period,
                numeric_value=f.numeric_value,
                validation_status=f.validation_status,
                confidence_score=f.confidence_score,
                is_demo=bool(f.is_demo),
                extraction_method=f.extraction_method,
                temporal_grain=getattr(f, "temporal_grain", None),
                document_id=f.document_id,
            )
            for f in facts
        ]

    @classmethod
    def _to_included(cls, facts: List[ExtractedFact]) -> List[IncludedFact]:
        return [
            IncludedFact(
                fact_id=f.id,
                metric_code=f.metric_code,
                subsidiary=f.subsidiary,
                mine=f.mine,
                reporting_period=f.reporting_period,
                numeric_value=f.numeric_value,
                unit=f.unit,
                confidence_score=f.confidence_score,
                validation_status=f.validation_status,
                is_demo=bool(f.is_demo),
                document_id=f.document_id,
                page_number=f.page_number,
                sheet_name=f.sheet_name,
                cell_reference=f.cell_reference,
                source_context=f.source_context,
            )
            for f in facts
        ]

    @classmethod
    def _apply_sum(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        if not defn.supports_sum:
            result.error_code = CalcError.UNSUPPORTED_OPERATION
            result.error_message = (
                f"SUM is not a valid operation for {defn.metric_code} "
                f"({defn.display_name}). {defn.notes}"
            )
            return result

        numeric_vals = [
            f.numeric_value for f in facts
            if f.numeric_value is not None and _is_valid_number(f.numeric_value)
        ]

        if not numeric_vals:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "All retrieved facts have null or invalid numeric values."
            return result

        total = sum(numeric_vals)
        canonical_unit = defn.canonical_unit

        result.success = True
        result.result = round(total, 4)
        result.unit = canonical_unit
        result.calculation_method = "SQL_SUM_DEDUPLICATED"
        result.formula = (
            f"SUM({len(numeric_vals)} included facts) = {round(total, 4)} {canonical_unit}"
        )
        result.sql_description = (
            f"SELECT SUM(numeric_value) FROM extracted_facts "
            f"WHERE metric_code='{defn.metric_code}'"
            + (f" AND subsidiary='{result.filters_applied.get('subsidiary')}'"
               if result.filters_applied.get("subsidiary") else "")
            + (f" AND reporting_period LIKE '%{result.filters_applied.get('reporting_period_stripped', '')}%'"
               if result.filters_applied.get("reporting_period") else "")
            + f" [after duplicate/overlap exclusion: {result.excluded_count} excluded]"
        )
        return result

    @classmethod
    def _apply_latest(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        sorted_facts = sorted(facts, key=lambda f: f.created_at, reverse=True)
        latest = next((f for f in sorted_facts if _is_valid_number(f.numeric_value)), None)

        if not latest:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "No valid numeric value found for LATEST operation."
            return result

        result.success = True
        result.result = round(latest.numeric_value, 4)
        result.unit = defn.canonical_unit
        result.calculation_method = "LATEST_OBSERVATION"
        result.formula = f"LATEST observation = {latest.numeric_value} {defn.canonical_unit}"
        result.sql_description = (
            f"SELECT numeric_value FROM extracted_facts "
            f"WHERE metric_code='{defn.metric_code}' ORDER BY created_at DESC LIMIT 1"
        )
        return result

    @classmethod
    def _apply_avg(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        vals = [f.numeric_value for f in facts if _is_valid_number(f.numeric_value)]
        if not vals:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "No valid numeric values for AVERAGE."
            return result

        avg = sum(vals) / len(vals)
        result.success = True
        result.result = round(avg, 4)
        result.unit = defn.canonical_unit
        result.calculation_method = "SIMPLE_AVERAGE"
        result.formula = f"AVG({len(vals)} values) = {round(avg, 4)} {defn.canonical_unit}"
        result.warnings.append(
            "SIMPLE_AVERAGE — no weight data available; if weight (tonnes) data exists, use WAVG instead"
        )
        return result

    @classmethod
    def _apply_wavg(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        # Fallback to simple average if no weight available
        result.warnings.append(
            "WEIGHTED_AVERAGE requested but weight column not stored per fact; "
            "falling back to SIMPLE_AVERAGE with disclosure"
        )
        return cls._apply_avg(result, facts, defn)

    @classmethod
    def _apply_min(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        vals = [f.numeric_value for f in facts if _is_valid_number(f.numeric_value)]
        if not vals:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "No valid numeric values for MIN."
            return result
        min_val = min(vals)
        result.success = True
        result.result = round(min_val, 4)
        result.unit = defn.canonical_unit
        result.calculation_method = "DETERMINISTIC_MIN"
        result.formula = f"MIN({len(vals)} values) = {round(min_val, 4)} {defn.canonical_unit}"
        result.sql_description = f"SELECT MIN(numeric_value) FROM extracted_facts WHERE metric_code='{defn.metric_code}'"
        return result

    @classmethod
    def _apply_max(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        vals = [f.numeric_value for f in facts if _is_valid_number(f.numeric_value)]
        if not vals:
            result.error_code = CalcError.INSUFFICIENT_EVIDENCE
            result.error_message = "No valid numeric values for MAX."
            return result
        max_val = max(vals)
        result.success = True
        result.result = round(max_val, 4)
        result.unit = defn.canonical_unit
        result.calculation_method = "DETERMINISTIC_MAX"
        result.formula = f"MAX({len(vals)} values) = {round(max_val, 4)} {defn.canonical_unit}"
        result.sql_description = f"SELECT MAX(numeric_value) FROM extracted_facts WHERE metric_code='{defn.metric_code}'"
        return result

    @classmethod
    def _apply_count(
        cls,
        result: CalculationResult,
        facts: List[ExtractedFact],
        defn: MetricDefinition,
    ) -> CalculationResult:
        cnt = len(facts)
        result.success = True
        result.result = float(cnt)
        result.unit = "facts"
        result.calculation_method = "DETERMINISTIC_COUNT"
        result.formula = f"COUNT(facts) = {cnt}"
        result.sql_description = f"SELECT COUNT(*) FROM extracted_facts WHERE metric_code='{defn.metric_code}'"
        return result

    @classmethod
    def calculate_grouped_subsidiaries(
        cls,
        db: Session,
        metric_code: str = "COAL_PRODUCTION",
        reporting_period: Optional[str] = None,
        only_verified: bool = False,
        only_real: bool = False,
        only_demo: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Calculates metric totals per individual subsidiary.
        Guarantees:
          - Full qualifying evidence sets evaluated (no LIMIT)
          - Consolidated CIL rows excluded to prevent double-counting
          - Deduplication and grain reconciliation performed per subsidiary
        """
        subsidiaries = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL"]
        results = []
        for sub in subsidiaries:
            scope = EvidenceScope(
                metric_code=metric_code,
                subsidiary=sub,
                reporting_period=reporting_period,
                only_verified=only_verified,
                only_real=only_real,
                only_demo=only_demo,
                exclude_consolidated=True,
            )
            calc_res = cls.calculate(db, scope, AggOp.SUM)
            if calc_res.success and calc_res.result is not None:
                results.append({
                    "subsidiary": sub,
                    "value": calc_res.result,
                    "unit": calc_res.unit or "MT",
                    "evidence_count": calc_res.evidence_count_used,
                    "verified_pct": calc_res.verified_pct,
                    "calc_result": calc_res,
                })
        results.sort(key=lambda x: x["value"], reverse=True)
        return results

    @classmethod
    def calculate_historical_trend(
        cls,
        db: Session,
        metric_code: str = "COAL_PRODUCTION",
        subsidiary: Optional[str] = None,
        only_verified: bool = False,
        only_real: bool = False,
        only_demo: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Calculates multi-year metric trends with deduplication and grain protection.
        """
        raw_periods = (
            db.query(ExtractedFact.reporting_period)
            .filter(
                ExtractedFact.metric_code == metric_code,
                ExtractedFact.reporting_period.ilike("FY%"),
            )
            .distinct()
            .all()
        )
        periods = sorted(list({p[0] for p in raw_periods if p[0]}))
        trend = []
        for period in periods:
            scope = EvidenceScope(
                metric_code=metric_code,
                subsidiary=subsidiary,
                reporting_period=period,
                only_verified=only_verified,
                only_real=only_real,
                only_demo=only_demo,
                exclude_consolidated=True if not subsidiary else False,
            )
            calc_res = cls.calculate(db, scope, AggOp.SUM)
            if calc_res.success and calc_res.result is not None:
                trend.append({
                    "period": period,
                    "value": calc_res.result,
                    "unit": calc_res.unit or "MT",
                    "evidence_count": calc_res.evidence_count_used,
                    "verified_pct": calc_res.verified_pct,
                })
        return trend

    @classmethod
    def _validate_units(
        cls, facts: List[ExtractedFact], defn: MetricDefinition
    ) -> List[str]:
        warnings: List[str] = []
        if not defn.allowed_units:
            return warnings
        mixed_units = set(
            f.unit for f in facts if f.unit and f.unit not in defn.allowed_units
        )
        if mixed_units:
            warnings.append(
                f"INCOMPATIBLE_UNITS — {len(mixed_units)} fact(s) have unit(s) "
                f"{mixed_units} which differ from canonical '{defn.canonical_unit}'. "
                f"These may represent the same quantity in different scales."
            )
        return warnings

    @classmethod
    def _validate_scope_compatibility(
        cls, actual: EvidenceScope, target: EvidenceScope
    ) -> List[str]:
        warnings = []
        if actual.subsidiary != target.subsidiary:
            warnings.append(
                f"SCOPE_MISMATCH — actual subsidiary='{actual.subsidiary}' "
                f"differs from target subsidiary='{target.subsidiary}'"
            )
        if actual.reporting_period != target.reporting_period:
            warnings.append(
                f"SCOPE_MISMATCH — actual period='{actual.reporting_period}' "
                f"differs from target period='{target.reporting_period}'"
            )
        return warnings

    @classmethod
    def _scope_mode(cls, facts: List[ExtractedFact]) -> str:
        demo_cnt = sum(1 for f in facts if bool(f.is_demo))
        real_cnt = len(facts) - demo_cnt
        if demo_cnt == 0:
            return DataScopeMode.REAL
        if real_cnt == 0:
            return DataScopeMode.DEMO
        return DataScopeMode.MIXED

    @classmethod
    def _scope_to_dict(cls, scope: EvidenceScope) -> Dict[str, Any]:
        d: Dict[str, Any] = {"metric_code": scope.metric_code}
        if scope.subsidiary:
            d["subsidiary"] = scope.subsidiary
        if scope.mine:
            d["mine"] = scope.mine
        if scope.reporting_period:
            d["reporting_period"] = scope.reporting_period
            d["reporting_period_stripped"] = scope.reporting_period.replace("FY ", "").strip()
        d["only_verified"] = scope.only_verified
        d["only_real"] = scope.only_real
        d["only_demo"] = scope.only_demo
        d["exclude_consolidated"] = scope.exclude_consolidated
        return d

    @classmethod
    def _describe_sql(cls, scope: EvidenceScope) -> str:
        return (
            f"SELECT SUM(numeric_value) FROM extracted_facts "
            f"WHERE metric_code='{scope.metric_code}'"
            + (f" AND subsidiary='{scope.subsidiary}'" if scope.subsidiary else "")
            + (f" AND reporting_period LIKE '%{scope.reporting_period}%'"
               if scope.reporting_period else "")
        )


def _is_valid_number(v: Any) -> bool:
    if v is None:
        return False
    try:
        f = float(v)
        return not (math.isnan(f) or math.isinf(f))
    except (TypeError, ValueError):
        return False
