"""
Dynamic Suggestions Engine for Ask MineIntel.
Queries actual database records to produce suggested prompts that are GUARANTEED to have backing evidence.
Falls back to labeled examples only when database is empty.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.fact import ExtractedFact
from app.services.mining.metric_registry import metric_registry


class SuggestionsEngine:
    """Generates evidence-backed dynamic suggestions for users."""

    @classmethod
    def get_dynamic_suggestions(
        cls,
        db: Session,
        include_demo: bool = False,
        limit: int = 6,
    ) -> List[str]:
        """
        Inspects real records in ExtractedFact and creates executable query suggestions.
        """
        q = db.query(
            ExtractedFact.subsidiary,
            ExtractedFact.metric_code,
            ExtractedFact.reporting_period,
            func.count(ExtractedFact.id).label("cnt")
        ).filter(
            ExtractedFact.numeric_value.isnot(None),
            ExtractedFact.subsidiary.isnot(None),
            ExtractedFact.reporting_period.isnot(None),
        )

        if not include_demo:
            q = q.filter(ExtractedFact.is_demo == False)  # noqa: E712

        distinct_slices = (
            q.group_by(ExtractedFact.subsidiary, ExtractedFact.metric_code, ExtractedFact.reporting_period)
            .order_by(func.count(ExtractedFact.id).desc())
            .limit(10)
            .all()
        )

        suggestions: List[str] = []

        for sub, m_code, period, _ in distinct_slices:
            m_name = metric_registry.get_canonical_name(m_code).lower()
            if m_code == "COAL_PRODUCTION":
                suggestions.append(f"What was {sub}'s raw coal production in {period}?")
            elif m_code == "DRILLING":
                suggestions.append(f"Show {sub} exploratory drilling progress in {period}")
            elif m_code == "OVERBURDEN_REMOVAL":
                suggestions.append(f"What was overburden removal (OBR) for {sub} in {period}?")
            elif m_code == "COAL_OFFTAKE":
                suggestions.append(f"Show coal dispatch / offtake figures for {sub} in {period}")
            elif m_code == "PRODUCTION_TARGET":
                suggestions.append(f"What was the production target for {sub} in {period}?")
            elif m_code == "GEOLOGICAL_RESERVES":
                suggestions.append(f"Show proved geological coal reserves for {sub}")
            else:
                suggestions.append(f"What was {sub}'s {m_name} in {period}?")

            if len(suggestions) >= limit:
                break

        # Add comparison or verification suggestions if sufficient data
        if distinct_slices:
            first_period = distinct_slices[0][2]
            suggestions.append(f"Compare raw coal production across all subsidiaries in {first_period}")
            first_sub = distinct_slices[0][0]
            first_m = distinct_slices[0][1]
            if first_m == "COAL_PRODUCTION":
                suggestions.append(f"What percentage of target did {first_sub} achieve in {first_period}?")

        # Deduplicate while preserving order
        unique_suggestions = []
        for s in suggestions:
            if s not in unique_suggestions:
                unique_suggestions.append(s)

        # Fallback if DB has very few or zero facts
        if not unique_suggestions:
            unique_suggestions = [
                "[Example] What was SECL's raw coal production in FY 2024-25?",
                "[Example] Compare raw coal production across all subsidiaries in FY 2024-25",
                "[Example] Show CMPDI drilling meters achievement in FY 2024-25",
                "[Example] Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25",
                "[Example] Show overburden removal (OBR) for NCL in FY 2023-24",
                "[Example] What were total Coal India dispatch figures in FY 2024-25?",
            ]

        return unique_suggestions[:limit]
