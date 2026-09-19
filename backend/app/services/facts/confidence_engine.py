"""
ConfidenceEngine — Computes an explainable, deterministic confidence score (0.0 to 1.0)
for every extracted fact. Transparently provides human-readable rationale.
"""
from typing import Tuple, Optional
from app.models.enums import ExtractionMethod, ValidationStatus


class ConfidenceEngine:
    @classmethod
    def calculate_confidence(
        cls,
        extraction_method: str,
        has_metric: bool,
        has_unit: bool,
        has_period: bool,
        has_subsidiary: bool,
        document_quality_score: float = 1.0,
        ocr_confidence: Optional[float] = None,
        is_approximate: bool = False,
        is_structured_spreadsheet: bool = False
    ) -> Tuple[float, str]:
        """
        Calculates confidence score (0.0 - 1.0) and human-readable explanation.
        """
        reasons = []

        # 1. Base score by extraction method
        if extraction_method in (ExtractionMethod.STRUCTURED_TABLE.value, "STRUCTURED_TABLE"):
            score = 0.88
            reasons.append("Extracted directly from structured table cell (+0.88)")
            if is_structured_spreadsheet:
                score += 0.04
                reasons.append("Structured Excel spreadsheet source (+0.04)")
        elif extraction_method in (ExtractionMethod.REGEX_PATTERN.value, "REGEX_PATTERN"):
            score = 0.75
            reasons.append("Extracted via deterministic regex pattern (+0.75)")
        elif extraction_method in (ExtractionMethod.OCR_BLOCK.value, "OCR_BLOCK"):
            ocr_conf = ocr_confidence if ocr_confidence is not None else 0.7
            score = 0.55 + (0.25 * ocr_conf)
            reasons.append(f"Extracted from OCR with {ocr_conf * 100:.0f}% confidence (+{score:.2f})")
        else:
            score = 0.65
            reasons.append("Extracted via heuristic parser (+0.65)")

        # 2. Metadata completeness bonuses / penalties
        if has_unit:
            score += 0.04
            reasons.append("Canonical unit identified (+0.04)")
        else:
            score -= 0.05
            reasons.append("Missing explicit unit (-0.05)")

        if has_period:
            score += 0.04
            reasons.append("Reporting period verified (+0.04)")
        else:
            score -= 0.05
            reasons.append("Unspecified reporting period (-0.05)")

        if has_subsidiary:
            score += 0.04
            reasons.append("Operating subsidiary / organization identified (+0.04)")

        # 3. Document quality discount
        if document_quality_score < 0.75:
            penalty = round((0.75 - document_quality_score) * 0.35, 2)
            score -= penalty
            reasons.append(f"Sub-optimal source document quality penalty (-{penalty})")

        if is_approximate:
            score -= 0.10
            reasons.append("Value indicated as approximate/estimated (-0.10)")

        final_score = max(0.10, min(0.99, round(score, 2)))
        rationale = " | ".join(reasons)

        return final_score, rationale

    @classmethod
    def get_initial_validation_status(cls, confidence: float) -> str:
        """
        Prompt 2 Section 38:
        confidence >= 0.90 -> HIGH_CONFIDENCE
        0.70–0.89 -> NEEDS_REVIEW
        < 0.70 -> REVIEW_REQUIRED
        Never marks VERIFIED automatically (requires human review).
        """
        if confidence >= 0.90:
            return ValidationStatus.HIGH_CONFIDENCE.value
        elif confidence >= 0.70:
            return ValidationStatus.NEEDS_REVIEW.value
        else:
            return ValidationStatus.REVIEW_REQUIRED.value
