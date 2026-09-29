"""
Deterministic Confidence Engine for Ask MineIntel.
Computes mathematically bounded, grounded confidence scores without LLM hallucination.

FORMULA:
Confidence = BaseScore
           + VerifiedEvidenceBonus
           + MultiSourceBonus
           - UnresolvedConflictPenalty
           - MissingMetadataPenalty

Parameters:
- BaseScore:
    * 0.85 for direct structured database fact matches
    * 0.90 for verified deterministic NumberSafe calculations
    * 0.50 + min(0.25, 0.05 * chunk_count) for narrative RAG retrieval
    * 1.00 for internal system / greeting / help responses
    * 0.00 for insufficient evidence
- VerifiedEvidenceBonus:
    * +0.10 if all utilized facts are human-verified
    * +0.05 if >= 50% are verified
- MultiSourceBonus:
    * +0.05 if independent documents corroborate the figure (>= 2 docs)
- UnresolvedConflictPenalty:
    * -0.30 if conflicting contradictory figures exist in the ledger
- MissingMetadataPenalty:
    * -0.10 if reporting period or subsidiary was inferred/ambiguous

Bands:
- HIGH: score >= 0.85
- MEDIUM: 0.60 <= score < 0.85
- LOW: score < 0.60
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceAssessment:
    score: float
    level: str  # HIGH, MEDIUM, LOW
    reason: str
    details: Dict[str, Any]


class ConfidenceEngine:
    """Calculates deterministic confidence for intelligence query results."""

    @classmethod
    def evaluate(
        cls,
        intent: str,
        answer_status: str,
        records_used: int = 0,
        verified_count: int = 0,
        document_count: int = 0,
        has_conflicts: bool = False,
        period_specified: bool = True,
        entity_specified: bool = True,
        is_calculation: bool = False,
        is_greeting_or_help: bool = False,
    ) -> ConfidenceAssessment:
        # Zero evidence / error / greeting cases
        if is_greeting_or_help:
            return ConfidenceAssessment(
                score=1.0,
                level="HIGH",
                reason="System guidance / operational capability response",
                details={"base": 1.0}
            )

        if answer_status in ("INSUFFICIENT_EVIDENCE", "ERROR") or records_used == 0:
            return ConfidenceAssessment(
                score=0.0,
                level="LOW",
                reason="Insufficient verified evidence in repository",
                details={"base": 0.0, "records_used": 0}
            )

        # 1. Base Score
        if is_calculation:
            base_score = 0.90
            base_reason = "Deterministic NumberSafe mathematical execution"
        elif intent in ("METRIC_LOOKUP", "COMPARISON", "FACT_VERIFICATION"):
            base_score = 0.85
            base_reason = "Direct structured database fact ledger retrieval"
        else:
            # Narrative RAG retrieval
            base_score = round(min(0.75, 0.50 + records_used * 0.05), 2)
            base_reason = f"Hybrid retrieval across {records_used} source chunks"

        score = base_score
        modifiers = []

        # 2. Verified Evidence Bonus
        if records_used > 0:
            verified_pct = (verified_count / records_used) * 100
            if verified_pct == 100.0:
                score += 0.10
                modifiers.append("+0.10 (100% human-verified evidence)")
            elif verified_pct >= 50.0:
                score += 0.05
                modifiers.append(f"+0.05 ({int(verified_pct)}% human-verified evidence)")

        # 3. Multi-Source Corroboration Bonus
        if document_count >= 2:
            score += 0.05
            modifiers.append(f"+0.05 (Corroborated across {document_count} independent documents)")

        # 4. Conflict Penalty
        if has_conflicts or answer_status == "CONFLICT_DETECTED":
            score -= 0.30
            modifiers.append("-0.30 (Active contradiction detected in evidence ledger)")

        # 5. Metadata Penalty
        if not period_specified:
            score -= 0.10
            modifiers.append("-0.10 (Reporting period not explicitly specified)")
        if not entity_specified:
            score -= 0.05
            modifiers.append("-0.05 (Broad subsidiary scope)")

        # Clamp between 0.0 and 0.99 (or 1.0 for clean 100% verified single facts)
        final_score = round(max(0.10, min(1.0, score)), 2)

        if final_score >= 0.85:
            level = "HIGH"
        elif final_score >= 0.60:
            level = "MEDIUM"
        else:
            level = "LOW"

        mod_str = "; ".join(modifiers) if modifiers else "Standard baseline calibration"
        reason = f"{base_reason}. {mod_str}."

        return ConfidenceAssessment(
            score=final_score,
            level=level,
            reason=reason,
            details={
                "base_score": base_score,
                "modifiers": modifiers,
                "verified_pct": round((verified_count / max(1, records_used)) * 100, 1),
                "document_count": document_count,
                "has_conflicts": has_conflicts
            }
        )
