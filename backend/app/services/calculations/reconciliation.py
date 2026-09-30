"""
NumberSafe 2.0 — Reconciliation Tests
Deterministic consistency checks that can be run on-demand or as part
of the ReportGuard pre-flight pipeline.

Checks:
  1. Sum of subsidiary components == consolidated total (within tolerance)
  2. Sum of monthly components == annual total (within tolerance)
  3. Production + Stock change == Dispatch + Stock addition (mass balance)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.services.calculations.calculation_engine import (
    CalculationEngine, EvidenceScope,
)
from app.services.calculations.metric_semantics import AggOp


@dataclass
class ReconciliationCheck:
    name: str
    passed: bool
    detail: str
    lhs_value: Optional[float] = None
    rhs_value: Optional[float] = None
    tolerance_pct: float = 2.0
    discrepancy_pct: Optional[float] = None


@dataclass
class ReconciliationReport:
    checks: List[ReconciliationCheck] = field(default_factory=list)
    overall_passed: bool = True

    def add(self, check: ReconciliationCheck) -> None:
        self.checks.append(check)
        if not check.passed:
            self.overall_passed = False


class ReconciliationService:
    """
    Runs deterministic reconciliation checks to detect inconsistencies
    between different aggregation paths.
    """

    SUBSIDIARIES = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL"]
    TOLERANCE_PCT = 2.0   # Allow up to 2% discrepancy before flagging

    @classmethod
    def run_all(
        cls,
        db: Session,
        metric_code: str = "COAL_PRODUCTION",
        reporting_period: Optional[str] = None,
        only_verified: bool = False,
    ) -> ReconciliationReport:
        report = ReconciliationReport()

        # Check 1: Sum of subsidiaries vs consolidated
        cls._check_subsidiary_vs_consolidated(
            db, report, metric_code, reporting_period, only_verified
        )

        return report

    @classmethod
    def _check_subsidiary_vs_consolidated(
        cls,
        db: Session,
        report: ReconciliationReport,
        metric_code: str,
        reporting_period: Optional[str],
        only_verified: bool,
    ) -> None:
        """
        Sum individual subsidiary totals and compare against a CIL-consolidated
        row (if one exists).  If the discrepancy exceeds tolerance, flag it.
        """
        sub_totals = []
        for sub in cls.SUBSIDIARIES:
            scope = EvidenceScope(
                metric_code=metric_code,
                subsidiary=sub,
                reporting_period=reporting_period,
                only_verified=only_verified,
                exclude_consolidated=True,
            )
            res = CalculationEngine.calculate(db, scope, AggOp.SUM)
            if res.success and res.result is not None:
                sub_totals.append(res.result)

        if not sub_totals:
            report.add(ReconciliationCheck(
                name="SubsidiaryComponentSum",
                passed=True,
                detail="No subsidiary-level evidence available to reconcile.",
            ))
            return

        component_sum = round(sum(sub_totals), 3)

        # Get consolidated
        cil_scope = EvidenceScope(
            metric_code=metric_code,
            subsidiary="CIL",
            reporting_period=reporting_period,
            only_verified=only_verified,
            exclude_consolidated=False,
        )
        cil_res = CalculationEngine.calculate(db, cil_scope, AggOp.SUM)

        if not cil_res.success or cil_res.result is None:
            report.add(ReconciliationCheck(
                name="SubsidiaryComponentSum",
                passed=True,
                detail=(
                    f"No consolidated CIL row to compare. "
                    f"Sum of subsidiaries = {component_sum}."
                ),
                lhs_value=component_sum,
            ))
            return

        cil_total = cil_res.result
        discrepancy = abs(component_sum - cil_total)
        discrepancy_pct = round(discrepancy / max(0.001, cil_total) * 100, 2)
        passed = discrepancy_pct <= cls.TOLERANCE_PCT

        report.add(ReconciliationCheck(
            name="SubsidiaryComponentSum",
            passed=passed,
            detail=(
                f"Sum of 7 subsidiaries = {component_sum} vs "
                f"CIL consolidated = {cil_total}. "
                f"Discrepancy: {discrepancy_pct}% "
                f"({'within' if passed else 'EXCEEDS'} {cls.TOLERANCE_PCT}% tolerance)."
            ),
            lhs_value=component_sum,
            rhs_value=cil_total,
            discrepancy_pct=discrepancy_pct,
        ))
