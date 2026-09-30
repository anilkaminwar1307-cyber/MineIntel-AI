"""
Deterministic Intent Classifier for Ask MineIntel.
Executes lightweight intent detection BEFORE any database or vector retrieval.
Guarantees that greetings and help queries never trigger RAG retrieval.
"""
import re
from typing import Tuple, Dict, Any, Optional
from app.services.intelligence.intents import QueryIntent, ResponseMode


GREETING_PATTERNS = [
    r"^(?:hi|hello|hey|namaste|greetings|good\s+(?:morning|afternoon|evening))\b",
    r"^(?:hi|hello|hey)\s+(?:there|mineintel|assistant|bot)\b",
]

HELP_PATTERNS = [
    r"^\b(?:help|how\s+to\s+use|how\s+does\s+this\s+work|guide\s+me|usage\s+guide|how\s+to\s+ask)\b",
    r"\b(?:give\s+me\s+help|need\s+help|what\s+should\s+i\s+ask)\b",
]

CAPABILITY_PATTERNS = [
    r"\b(?:what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities|how\s+does\s+mineintel\s+work|tell\s+me\s+about\s+mineintel|what\s+is\s+mineintel|your\s+features)\b",
    r"\b(?:system\s+capabilities|platform\s+overview)\b",
]

VERIFICATION_PATTERNS = [
    r"\bverify\s+claim\b",
    r"\b(?:verify|validate|check|confirm)\s+(?:whether|if|that)?\s+[a-z0-9\s-]+?\b(?:was|is|reached|achieved|produced|drilled|stands\s+at)\s+\d+",
    r"\bis\s+it\s+true\s+that\b",
    r"\bcheck\s+claim\b",
]

CALCULATION_PATTERNS = [
    r"\b(?:calculate|compute)\s+(?:the\s+)?(?:growth|percentage|achievement|ratio|difference|variance|margin)\b",
    r"\bwhat\s+percentage\s+of\s+(?:its\s+)?target\b",
    r"\btarget\s+achievement\b",
    r"\b(?:growth|increase|decrease|change)\s+from\s+[a-z0-9\s-]+\s+to\s+[a-z0-9\s-]+",
    r"\b(?:actual\s+vs\s+target|target\s+vs\s+actual)\b",
    r"\bdivide|multiply|sum\s+of|difference\s+between\b",
]

COMPARISON_PATTERNS = [
    r"\b(?:compare|comparison|versus|vs)\s+.*?\b(?:across|between|all\s+subsidiaries|subsidiaries)\b",
    r"\bcompare\s+[a-z0-9\s-]+\s+(?:and|with|to)\s+[a-z0-9\s-]+",
    r"\b(?:rank|ranking|highest|lowest|top\s+producing|bottom)\s+(?:subsidiary|subsidiaries|producer|mine|mines)\b",
    r"\bacross\s+all\s+subsidiaries\b",
]

TREND_PATTERNS = [
    r"\b(?:trend|trajectory|historical|over\s+time|year\s+on\s+year|yoy|yearly|time\s+series)\b",
    r"\bhow\s+has\s+.*?\s+(?:changed|grown|evolved)\b",
]

CONFLICT_PATTERNS = [
    r"\b(?:conflict|conflicts|discrepancy|discrepancies|contradiction|contradictions|mismatch|data\s+conflict)\b",
    r"\bunresolved\s+(?:issues|conflicts|records)\b",
]

PARLIAMENTARY_PATTERNS = [
    r"\b(?:parliamentary|lok\s+sabha|rajya\s+sabha|starred\s+question|unstarred\s+question|pq\s+brief|parliament\s+query)\b",
    r"\bparliamentary\s+(?:reply|response|brief)\b",
]

DOCUMENT_SUMMARY_PATTERNS = [
    r"\b(?:summarize|summary\s+of|executive\s+summary|brief\s+summary)\s+(?:the\s+)?(?:report|document|file|annual\s+report|filing)\b",
    r"\bkey\s+takeaways\s+from\s+(?:the\s+)?(?:report|document)\b",
]

DOCUMENT_QUERY_PATTERNS = [
    r"\bwhat\s+does\s+the\s+(?:report|document|file)\s+say\s+about\b",
    r"\baccording\s+to\s+(?:the\s+)?(?:report|document)\b",
    r"\bin\s+(?:the\s+)?(?:report|document|filing)\b",
    r"\bmentioned\s+in\s+the\s+document\b",
]

EXPLANATION_PATTERNS = [
    r"\b(?:explain\s+reasons?\s+for|why\s+did|factors?\s+(?:behind|affecting|causing)|reasons?\s+for\s+shortfall)\b",
    r"\bwhy\s+was\s+there\s+a\s+(?:shortfall|surplus|delay|gap)\b",
]

REPORT_QUERY_PATTERNS = [
    r"\b(?:generate\s+report|create\s+report|report\s+studio|export\s+report)\b",
]

SOURCE_QUERY_PATTERNS = [
    r"\b(?:where\s+does\s+this\s+figure\s+come\s+from|source\s+of|show\s+citation|traceability\s+of|provenance\s+of)\b",
]


class IntentClassifier:
    """Classifies user mining queries into canonical QueryIntent."""

    @classmethod
    def classify(cls, query_text: str, response_mode: Optional[str] = None) -> Tuple[QueryIntent, float]:
        """
        Classifies query text into (QueryIntent, confidence).
        Runs deterministically in sub-millisecond time.
        """
        text = (query_text or "").strip().lower()
        if not text:
            return QueryIntent.UNKNOWN, 0.0

        # Exact / Leading Greeting Check
        for pat in GREETING_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                # Ensure it's not followed by a complex question (e.g. "hi, what was SECL production?")
                words = re.findall(r'\b\w+\b', text)
                if len(words) <= 3:
                    return QueryIntent.GREETING, 0.99
                # If greeting words + mining query, prioritize the mining query intent below

        # Help Check
        for pat in HELP_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                words = re.findall(r'\b\w+\b', text)
                if len(words) <= 6:
                    return QueryIntent.HELP, 0.95

        # Capability Check
        for pat in CAPABILITY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.CAPABILITY_QUERY, 0.95

        # Explicit Parliamentary Request
        if response_mode in (ResponseMode.PARLIAMENTARY.value, "PARLIAMENTARY") or any(
            re.search(pat, text, re.IGNORECASE) for pat in PARLIAMENTARY_PATTERNS
        ):
            return QueryIntent.PARLIAMENTARY_QUERY, 0.92

        # Fact Verification Check (e.g., "Verify claim: ECL production was 42.1 MT")
        for pat in VERIFICATION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.FACT_VERIFICATION, 0.95

        # Conflict Query
        for pat in CONFLICT_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.CONFLICT_QUERY, 0.90

        # Calculation Check (growth, percentage, ratio, target vs actual)
        for pat in CALCULATION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.CALCULATION, 0.92

        # Comparison Check (across subsidiaries, compare X and Y, rank)
        for pat in COMPARISON_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.COMPARISON, 0.92

        # Trend Query
        for pat in TREND_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.TREND_ANALYSIS, 0.88

        # Document Summary
        for pat in DOCUMENT_SUMMARY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.DOCUMENT_SUMMARY, 0.88

        # Explanation
        for pat in EXPLANATION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.EXPLANATION, 0.85

        # Document Query
        for pat in DOCUMENT_QUERY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.DOCUMENT_QUERY, 0.85

        # Source / Provenance Query
        for pat in SOURCE_QUERY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.SOURCE_QUERY, 0.85

        # Report Query
        for pat in REPORT_QUERY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return QueryIntent.REPORT_QUERY, 0.85

        # General number check with claim phrasing (e.g., "SECL produced 185.2 MT in FY 2024-25")
        if (
            re.search(r'\b(?:produced|achieved|dispatched|drilled|stands at|was|reached)\b', text)
            and re.search(r'\b\d+(?:\.\d+)?\s*(?:mt|bcm|mm3|m|%|cr)\b', text)
        ):
            return QueryIntent.FACT_VERIFICATION, 0.85

        # Metric Lookup (Default for queries asking about metrics/production/targets/drilling)
        from app.services.mining.metric_registry import metric_registry
        if metric_registry.resolve(text) or any(
            k in text for k in ["production", "target", "offtake", "dispatch", "drilling", "overburden", "obr", "reserve", "stock", "capex", "borehole"]
        ):
            return QueryIntent.METRIC_LOOKUP, 0.85

        return QueryIntent.UNKNOWN, 0.40
