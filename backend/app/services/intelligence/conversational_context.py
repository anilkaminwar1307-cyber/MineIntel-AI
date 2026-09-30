"""
Conversational Context & Session State for Ask MineIntel.
Maintains context across sequential queries to resolve follow-ups like:
"What was SECL production in FY24-25?" -> "What was the target?"
"""
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ConversationState:
    session_id: str
    last_subsidiary: Optional[str] = None
    last_subsidiaries: list = field(default_factory=list)
    last_mine: Optional[str] = None
    last_metric_code: Optional[str] = None
    last_period: Optional[str] = None
    last_document_ids: Optional[list] = None
    last_query: Optional[str] = None
    last_intent: Optional[str] = None
    updated_at: float = field(default_factory=time.time)


class ConversationalContextManager:
    """Thread-safe, in-memory session context storage with automatic expiration."""

    _sessions: Dict[str, ConversationState] = {}
    _TTL_SECONDS: int = 1800  # 30 minutes

    @classmethod
    def get_session(cls, session_id: Optional[str]) -> Optional[ConversationState]:
        if not session_id:
            return None
        cls._cleanup_expired()
        return cls._sessions.get(session_id)

    @classmethod
    def update_session(
        cls,
        session_id: Optional[str],
        subsidiary: Optional[str] = None,
        subsidiaries: Optional[list] = None,
        mine: Optional[str] = None,
        metric_code: Optional[str] = None,
        period: Optional[str] = None,
        document_ids: Optional[list] = None,
        query: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> None:
        if not session_id:
            return

        state = cls._sessions.get(session_id)
        if not state:
            state = ConversationState(session_id=session_id)
            cls._sessions[session_id] = state

        if subsidiary:
            state.last_subsidiary = subsidiary
        if subsidiaries:
            state.last_subsidiaries = subsidiaries
        if mine:
            state.last_mine = mine
        if metric_code:
            state.last_metric_code = metric_code
        if period:
            state.last_period = period
        if document_ids is not None:
            state.last_document_ids = document_ids
        if query:
            state.last_query = query
        if intent:
            state.last_intent = intent

        state.updated_at = time.time()

    @classmethod
    def inherit_context(
        cls,
        session_id: Optional[str],
        current_entity: Dict[str, Any],
        current_period: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """
        If current query lacks subsidiary or period, inherits from session context.
        Returns (enriched_entity, enriched_period, was_inherited).
        """
        if not session_id:
            return current_entity, current_period, False

        state = cls.get_session(session_id)
        if not state:
            return current_entity, current_period, False

        inherited = False
        enriched_entity = dict(current_entity)
        enriched_period = dict(current_period)

        # Inherit subsidiary if omitted in new query
        if not enriched_entity.get("subsidiary") and not enriched_entity.get("is_all_subsidiaries"):
            if state.last_subsidiary:
                enriched_entity["subsidiary"] = state.last_subsidiary
                enriched_entity["subsidiaries"] = [state.last_subsidiary]
                inherited = True

        # Inherit mine if omitted
        if not enriched_entity.get("mine") and state.last_mine:
            enriched_entity["mine"] = state.last_mine
            inherited = True

        # Inherit period if omitted in new query
        if not enriched_period.get("period") and state.last_period:
            enriched_period["period"] = state.last_period
            enriched_period["period_type"] = "INHERITED_FY"
            inherited = True

        return enriched_entity, enriched_period, inherited

    @classmethod
    def _cleanup_expired(cls) -> None:
        now = time.time()
        expired = [sid for sid, s in cls._sessions.items() if now - s.updated_at > cls._TTL_SECONDS]
        for sid in expired:
            del cls._sessions[sid]
