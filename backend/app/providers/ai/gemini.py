import os
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.providers.ai.base import AIProvider

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiProvider(AIProvider):
    """
    Official Google Gemini API implementation of AIProvider.
    Gracefully handles unconfigured keys by returning 'not_configured' status without crashing.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model or settings.GEMINI_MODEL
        self.client = None
        self._is_configured = False

        if not GENAI_AVAILABLE:
            logger.warning("google-genai library not installed or import failed.")
            return

        if self.api_key and len(self.api_key.strip()) > 5:
            try:
                self.client = genai.Client(api_key=self.api_key.strip())
                self._is_configured = True
                logger.info(f"GeminiProvider initialized successfully with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self._is_configured = False
        else:
            logger.info("GeminiProvider: GEMINI_API_KEY not provided. Operating in 'not_configured' mode.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "configured" if self._is_configured else "not_configured",
            "provider": "gemini",
            "model": self.model_name,
            "api_key_set": bool(self.api_key and len(self.api_key.strip()) > 5),
            "library_available": GENAI_AVAILABLE
        }

    async def classify_document(self, text_snippet: str, filename: str) -> Dict[str, Any]:
        if not self._is_configured or not self.client:
            return {
                "category": "General Mining Document",
                "confidence": 0.5,
                "note": "AI Provider not configured; using heuristic classification"
            }
        
        prompt = (
            f"You are a mining and geological document classification assistant for CMPDI and Coal India Limited.\n"
            f"Filename: {filename}\n"
            f"Content snippet: {text_snippet[:1500]}\n\n"
            f"Classify this document into one of: Geological Report, Production Report, Exploration & Drilling Report, "
            f"Monthly Dispatch Statement, Reserve Estimation, Administrative / Parliamentary Query, Safety & Environmental.\n"
            f"Return ONLY valid JSON with keys: category (string), confidence (float 0.0-1.0), reason (string)."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            import json
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini classify_document error: {e}")
            return {"category": "General Mining Report", "confidence": 0.5, "error": str(e)}

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        if not self._is_configured or not self.client:
            return []
        
        prompt = (
            f"Extract mining entities from the following text for Coal India Limited / CMPDI.\n"
            f"Identify: Subsidiaries (ECL, BCCL, CCL, NCL, WCL, SECL, MCL, CMPDI), Mines, Coalfields, "
            f"Reporting Periods, and Mining Units (MT, BCM, meters).\n"
            f"Text: {text[:2000]}\n"
            f"Return ONLY a JSON array of objects with keys: entity, type, confidence."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            import json
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini extract_entities error: {e}")
            return []

    async def summarize_context(self, context_chunks: List[str], max_words: int = 200) -> str:
        if not self._is_configured or not self.client:
            return "Document summary will be generated once AI Provider is configured."

        combined = "\n\n".join(context_chunks[:5])
        prompt = (
            f"Provide an objective, concise summary (under {max_words} words) of this mining operational text. "
            f"Do NOT invent figures.\n\n{combined}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini summarize error: {e}")
            return f"Summary unavailable: {e}"

    async def answer_from_context(
        self,
        query: str,
        context_chunks: List[str],
        response_mode: str = "STANDARD"
    ) -> str:
        if not self._is_configured or not self.client:
            return "Query engine will become available after evidence processing and AI provider configuration."

        joined_context = "\n---\n".join(context_chunks[:6])
        instructions = (
            f"You are MineIntel, an evidence-first mining intelligence assistant for Coal India Limited & CMPDI.\n"
            f"Answer the query strictly based on the provided context below.\n"
            f"Response Mode: {response_mode}. (If PARLIAMENTARY, provide formal, factual, concise points).\n"
            f"CRITICAL RULE: If figures or facts are not in the context, explicitly state that the evidence does not contain that figure. NEVER invent numbers.\n\n"
            f"Context:\n{joined_context}\n\nQuery: {query}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=instructions
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini answer_from_context error: {e}")
            return f"Error executing query: {e}"

    async def generate_report_narrative(
        self,
        report_title: str,
        verified_facts: List[Dict[str, Any]],
        template_type: str
    ) -> str:
        if not self._is_configured or not self.client:
            return "Report narrative generation will become active once evidence processing and AI provider are enabled."

        import json
        facts_str = json.dumps(verified_facts[:25], indent=2)
        prompt = (
            f"Draft the executive narrative for report: '{report_title}'.\n"
            f"Template: {template_type}\n"
            f"Use ONLY the following verified facts from the Evidence Ledger:\n{facts_str}\n"
            f"Cite specific metrics and subsidiaries. Maintain a formal, audit-ready tone."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini report narrative error: {e}")
            return f"Unable to generate narrative: {e}"


# Singleton instance
gemini_provider = GeminiProvider()


def get_ai_provider() -> AIProvider:
    """Dependency injector for AIProvider"""
    return gemini_provider
