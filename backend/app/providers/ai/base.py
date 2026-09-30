from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class AIProvider(ABC):
    """
    Abstract AI Provider Interface.
    Enforces that LLMs are used for semantic classification, summarization, entity extraction
    assistance, and narrative generation, but NEVER as the authoritative source for numerical mining figures.
    """

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns provider status: configured or not_configured, model name, etc."""
        pass

    @abstractmethod
    async def classify_document(self, text_snippet: str, filename: str) -> Dict[str, Any]:
        """Categorize mining document (Geological, Production, Drilling, Dispatch, Administrative, etc.)"""
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Identify potential mining entities (Mines, Coalfields, Subsidiaries, Dates, Units) to assist heuristic parsers."""
        pass

    @abstractmethod
    async def summarize_context(self, context_chunks: List[str], max_words: int = 200) -> str:
        """Produce grounded narrative summaries of document sections."""
        pass

    @abstractmethod
    async def answer_from_context(
        self,
        query: str,
        context_chunks: List[str],
        response_mode: str = "STANDARD"
    ) -> str:
        """Answer queries strictly conditioned on grounded context chunks."""
        pass

    @abstractmethod
    async def generate_report_narrative(
        self,
        report_title: str,
        verified_facts: List[Dict[str, Any]],
        template_type: str
    ) -> str:
        """Generate narrative text based strictly on verified structured facts from the Evidence Ledger."""
        pass

    @abstractmethod
    async def generate_parliamentary_brief(
        self,
        query: str,
        period: str,
        subsidiary: str,
        direct_answer: str,
        verified_facts: List[Dict[str, Any]],
        supporting_context: List[str],
        numbersafe_status: str,
        confidence_score: float,
        records_used: int,
        calculation_formula: Optional[str] = None,
    ) -> str:
        """Generate official Lok Sabha / Rajya Sabha parliamentary brief grounded strictly on verified facts."""
        pass
