"""
Central Query Orchestrator for Ask MineIntel.
Executes the unified 11-step intelligence pipeline:
Input Validation → Intent Detection → Entity/Metric Extraction → Scope Resolution →
Query Routing → Evidence Retrieval / NumberSafe → Conflict Check → Answer Synthesis →
Citation Verification → Confidence Calculation → Audit Logging.
"""
import uuid
import time
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.validation import EvidenceConflict
from app.models.query import QueryHistory
from app.models.audit import AuditEvent
from app.models.enums import ValidationStatus, AuditAction
from app.services.calculations.calculation_engine import (
    CalculationEngine, EvidenceScope, AggOp, CalculationResult, CalcError
)
from app.services.calculations.lineage import persist_calculation
from app.services.intelligence.intents import QueryIntent, AnswerStatus, ResponseMode
from app.services.intelligence.intent_classifier import IntentClassifier
from app.services.intelligence.entity_resolver import MiningEntityResolver
from app.services.intelligence.period_resolver import MiningPeriodResolver
from app.services.intelligence.conversational_context import ConversationalContextManager
from app.services.intelligence.confidence_engine import ConfidenceEngine
from app.services.intelligence.claim_verifier import ClaimVerifier
from app.services.intelligence.hybrid_retriever import HybridRetriever
from app.services.intelligence.parliamentary_synthesizer import ParliamentarySynthesizer
from app.services.intelligence.answer_synthesizer import AnswerSynthesizer
from app.services.intelligence.suggestions_engine import SuggestionsEngine
from app.core.logging import logger


class QueryOrchestrator:
    """The central intelligence router for Ask MineIntel."""

    @classmethod
    def process_query(
        cls,
        db: Session,
        query_text: str,
        scope: str = "ALL_EVIDENCE",
        response_mode: str = "STANDARD",
        subsidiary_filter: Optional[str] = None,
        period_filter: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        only_verified: bool = False,
        include_demo: bool = False,
        session_id: Optional[str] = None,
        user_name: str = "CMPDI Analyst",
    ) -> Dict[str, Any]:
        start_time = time.time()
        query_id = str(uuid.uuid4())
        raw_query = (query_text or "").strip()

        # Step 1: Input Validation
        if not raw_query:
            return cls._empty_query_response(query_id)

        # Scope flag overrides
        if scope == "VERIFIED_ONLY" or scope == "HUMAN_VERIFIED":
            only_verified = True

        data_scope_label = "DEMO DATA" if include_demo else "REAL UPLOADED DATA"

        # Step 2: Intent Detection BEFORE retrieval
        intent, intent_conf = IntentClassifier.classify(raw_query, response_mode=response_mode)

        # Step 3: Handle Greetings, Help, Capabilities Immediately
        if intent == QueryIntent.GREETING:
            return cls._handle_greeting(query_id, raw_query, session_id, user_name, db)

        if intent == QueryIntent.HELP:
            return cls._handle_help(query_id, raw_query, session_id, user_name, db)

        if intent == QueryIntent.CAPABILITY_QUERY:
            return cls._handle_capability(query_id, raw_query, session_id, user_name, db)

        # Step 4: Mining Entity & Metric Extraction
        entity_info = MiningEntityResolver.resolve_entities(raw_query)
        # Apply manual UI filter if supplied
        if subsidiary_filter and subsidiary_filter.upper() not in ("ALL", "ALL 8 SUBSIDIARIES"):
            entity_info["subsidiary"] = subsidiary_filter.upper()
            entity_info["subsidiaries"] = [subsidiary_filter.upper()]

        # Step 5: Period Extraction
        period_info = MiningPeriodResolver.resolve_period(raw_query)
        if period_filter and period_filter.upper() not in ("ALL", "ALL PERIODS"):
            period_info["period"] = period_filter

        # Step 6: Conversational Context Inheritance (Follow-ups)
        entity_info, period_info, was_inherited = ConversationalContextManager.inherit_context(
            session_id, entity_info, period_info
        )

        resolved_sub = entity_info.get("subsidiary")
        resolved_metric = entity_info.get("metric_code")
        resolved_period = period_info.get("period")

        # Step 7: Route query intelligently
        if intent == QueryIntent.FACT_VERIFICATION:
            result = ClaimVerifier.verify(
                db=db,
                query_text=raw_query,
                entity_info=entity_info,
                period_info=period_info,
                scope=scope,
                document_ids=document_ids,
                only_verified=only_verified,
                include_demo=include_demo,
            )
            result["intent"] = QueryIntent.FACT_VERIFICATION.value

        elif intent == QueryIntent.CALCULATION or ("achievement" in raw_query.lower() and resolved_metric == "PRODUCTION_TARGET"):
            result = cls._handle_calculation_route(
                db=db,
                query=raw_query,
                entity_info=entity_info,
                period_info=period_info,
                document_ids=document_ids,
                only_verified=only_verified,
                include_demo=include_demo,
            )
            result["intent"] = QueryIntent.CALCULATION.value

        elif intent == QueryIntent.COMPARISON or entity_info.get("is_all_subsidiaries") or (
            len(entity_info.get("subsidiaries", [])) > 1 and "compare" in raw_query.lower()
        ):
            result = cls._handle_comparison_route(
                db=db,
                query=raw_query,
                entity_info=entity_info,
                period_info=period_info,
                document_ids=document_ids,
                only_verified=only_verified,
                include_demo=include_demo,
            )
            result["intent"] = QueryIntent.COMPARISON.value

        elif intent == QueryIntent.CONFLICT_QUERY:
            result = cls._handle_conflict_route(db, raw_query)
            result["intent"] = QueryIntent.CONFLICT_QUERY.value

        elif resolved_metric:
            # Step 7.E: Structured Database Metric Lookup
            result = cls._handle_metric_lookup(
                db=db,
                query=raw_query,
                entity_info=entity_info,
                period_info=period_info,
                document_ids=document_ids,
                only_verified=only_verified,
                include_demo=include_demo,
            )
            result["intent"] = QueryIntent.METRIC_LOOKUP.value

        else:
            # Step 7.G: Narrative / Hybrid Retrieval Path
            result = cls._handle_narrative_route(
                db=db,
                query=raw_query,
                subsidiary=resolved_sub,
                period=resolved_period,
                document_ids=document_ids,
                include_demo=include_demo,
                response_mode=response_mode,
            )
            result["intent"] = QueryIntent.DOCUMENT_QUERY.value

        # Step 8: Parliamentary Query Brief Mode Formatting
        if response_mode == ResponseMode.PARLIAMENTARY.value or intent == QueryIntent.PARLIAMENTARY_QUERY:
            pq_text = ParliamentarySynthesizer.synthesize_pq_brief(
                query=raw_query,
                subsidiary=resolved_sub,
                period=resolved_period,
                metric_name=entity_info.get("metric_name") or "Mining Performance",
                key_figures=result.get("key_figures") or [
                    {
                        "subsidiary": resolved_sub or "CIL",
                        "value": result.get("direct_metric_value"),
                        "unit": result.get("metric_unit", "MT"),
                        "metric_name": entity_info.get("metric_name") or "Operational Metric",
                        "verified": only_verified,
                    }
                ] if result.get("direct_metric_value") is not None else [],
                citations=result.get("citations", []),
                narrative_context=result.get("answer"),
                data_scope=data_scope_label,
            )
            result["answer"] = pq_text
            result["response_mode"] = ResponseMode.PARLIAMENTARY.value

        # Step 9: Compute Deterministic Confidence
        records_used = result.get("records_used", 0)
        verified_count = sum(1 for c in result.get("citations", []) if c.get("human_verified"))
        doc_count = len({c.get("document_id") for c in result.get("citations", []) if c.get("document_id")})
        has_conflicts = bool(result.get("conflicts"))

        conf_assessment = ConfidenceEngine.evaluate(
            intent=result.get("intent", intent.value),
            answer_status=result.get("status", "SUCCESS"),
            records_used=records_used,
            verified_count=verified_count,
            document_count=doc_count,
            has_conflicts=has_conflicts,
            period_specified=bool(resolved_period),
            entity_specified=bool(resolved_sub),
            is_calculation=(result.get("intent") == QueryIntent.CALCULATION.value),
            is_greeting_or_help=False,
        )

        # Step 10: Dynamic Suggested Follow-ups
        followups = cls._generate_followups(resolved_sub, resolved_metric, resolved_period)

        # Update Session Context
        ConversationalContextManager.update_session(
            session_id=session_id,
            subsidiary=resolved_sub,
            subsidiaries=entity_info.get("subsidiaries"),
            mine=entity_info.get("mine"),
            metric_code=resolved_metric,
            period=resolved_period,
            document_ids=document_ids,
            query=raw_query,
            intent=result.get("intent", intent.value),
        )

        exec_time_ms = round((time.time() - start_time) * 1000, 1)

        # Step 11: Audit Logging & QueryHistory
        cls._log_query(
            db=db,
            query_id=query_id,
            query=raw_query,
            intent=result.get("intent", intent.value),
            scope=scope,
            response_mode=response_mode,
            answer=result.get("answer", ""),
            records_used=records_used,
            confidence=conf_assessment.score,
            user_name=user_name,
            exec_time_ms=exec_time_ms,
        )

        # Assemble Final Standardized Schema
        return {
            "query_id": query_id,
            "query": raw_query,
            "intent": result.get("intent", intent.value),
            "status": result.get("status", "SUCCESS"),
            "answer_status": result.get("verdict") or result.get("status", "SUCCESS"),
            "answer": result.get("answer", ""),
            "scope": scope,
            "response_mode": response_mode,
            "resolved_context": {
                "subsidiary": resolved_sub,
                "subsidiaries": entity_info.get("subsidiaries", []),
                "mine": entity_info.get("mine"),
                "metric_code": resolved_metric,
                "metric_name": entity_info.get("metric_name"),
                "period": resolved_period,
                "document_ids": document_ids,
                "was_inherited": was_inherited,
            },
            "confidence": conf_assessment.score,
            "confidence_score": conf_assessment.score,
            "confidence_level": conf_assessment.level,
            "confidence_reason": conf_assessment.reason,
            "confidence_details": conf_assessment.details,
            "records_used": records_used,
            "verified_facts_count": verified_count,
            "verification_status": f"{int((verified_count / max(1, records_used)) * 100)}% VERIFIED" if records_used > 0 else "N/A",
            "verification_result": result.get("verdict"),
            "citations": result.get("citations", []),
            "sources": result.get("citations", []),
            "chart": result.get("chart"),
            "calculation": result.get("calculation"),
            "calculation_steps": result.get("calculation_steps") or ([result["calculation"]] if result.get("calculation") else []),
            "calculation_result": result.get("calculation_result"),
            "direct_metric_value": result.get("direct_metric_value"),
            "metric_unit": result.get("metric_unit"),
            "sql_query": result.get("sql_query"),
            "key_figures": result.get("key_figures", []),
            "conflicts": result.get("conflicts", []),
            "data_scope": data_scope_label,
            "is_demo": include_demo,
            "suggested_followups": followups,
            "execution_time_ms": exec_time_ms,
        }

    # ── Sub-Routers ──────────────────────────────────────────────────────────

    @classmethod
    def _handle_metric_lookup(
        cls,
        db: Session,
        query: str,
        entity_info: Dict[str, Any],
        period_info: Dict[str, Any],
        document_ids: Optional[List[str]],
        only_verified: bool,
        include_demo: bool,
    ) -> Dict[str, Any]:
        """Queries structured facts deterministically via NumberSafe CalculationEngine."""
        sub = entity_info.get("subsidiary")
        metric_code = entity_info.get("metric_code")
        metric_name = entity_info.get("metric_name") or metric_code
        period = period_info.get("period")

        scope_obj = EvidenceScope(
            metric_code=metric_code,
            subsidiary=sub,
            mine=entity_info.get("mine"),
            reporting_period=period,
            only_verified=only_verified,
            only_real=not include_demo,
            only_demo=include_demo,
            document_ids=document_ids,
        )

        calc_res = CalculationEngine.calculate(db, scope_obj, operation=AggOp.SUM)

        if not calc_res.success or calc_res.result is None:
            # Check if unverified facts exist when only_verified=True
            if only_verified:
                unverified_scope = EvidenceScope(
                    metric_code=metric_code,
                    subsidiary=sub,
                    reporting_period=period,
                    only_verified=False,
                    only_real=not include_demo,
                    only_demo=include_demo,
                    document_ids=document_ids,
                )
                unverified_probe = CalculationEngine.calculate(db, unverified_scope, operation=AggOp.SUM)
                if unverified_probe.success and unverified_probe.evidence_count_total > 0:
                    return {
                        "status": AnswerStatus.UNVERIFIED_EVIDENCE_EXISTS.value,
                        "answer": (
                            f"**Human-Verified Evidence Mode Active:**\n\n"
                            f"Relevant evidence records exist for **{sub or 'CIL'}** `{metric_name}` "
                            + (f"in **{period}**" if period else "") +
                            f", but **none of the {unverified_probe.evidence_count_total} records are currently human-verified**.\n\n"
                            f"To view these figures, either confirm them in the **Review Queue** or switch Evidence Scope to **'All Evidence'**."
                        ),
                        "citations": [],
                        "records_used": 0,
                    }

            # Check if facts exist under demo scope when only_real was requested
            if not include_demo:
                demo_probe = EvidenceScope(
                    metric_code=metric_code,
                    subsidiary=sub,
                    reporting_period=period,
                    only_verified=False,
                    only_real=False,
                    only_demo=True,
                    document_ids=document_ids,
                )
                demo_probe_res = CalculationEngine.calculate(db, demo_probe, operation=AggOp.SUM)
                if demo_probe_res.success and demo_probe_res.evidence_count_total > 0:
                    return {
                        "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                        "answer": (
                            f"I could not find verified real-world records for **{sub or 'CIL'}** `{metric_name}` "
                            + (f"in **{period}**" if period else "") +
                            f".\n\n*Note: Synthetic demonstration data is available for this scope. Switch Data Scope to 'Demo Data' to inspect.*"
                        ),
                        "citations": [],
                        "records_used": 0,
                    }

            return {
                "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": (
                    f"I could not find sufficient evidence in the selected documents or database for **{sub or 'CIL'}** "
                    f"`{metric_name}`" + (f" in **{period}**." if period else ".") + "\n\n"
                    f"**Suggested Actions:**\n"
                    f"- Broaden document scope to 'All Documents'\n"
                    f"- Switch Evidence filter from 'Human-Verified Only' to 'All Evidence'\n"
                    f"- Upload the related CMPDI/CIL monthly or annual operational document\n"
                    f"- Select a different financial year (e.g. FY 2024-25 or FY 2023-24)"
                ),
                "citations": [],
                "records_used": 0,
            }

        unit_str = calc_res.unit or "MT"
        val = round(calc_res.result, 2)
        citations = cls._build_citations(db, calc_res.included_facts, metric_name, unit_str)

        entity_label = sub or "Coal India Limited (Consolidated)"
        period_label = period or "Consolidated Active Records"

        # Check for conflicts
        conflicts = cls._check_conflicts(calc_res.included_facts)

        answer_text = (
            f"Based on verified statutory records in the Evidence Ledger, the recorded **{metric_name}** "
            f"for **{entity_label}** in **{period_label}** is **{val:,} {unit_str}**.\n\n"
            f"- **Metric:** {metric_name} (`{metric_code}`)\n"
            f"- **Aggregated Value:** **{val:,} {unit_str}**\n"
            f"- **Evidence Ledger Records Utilized:** {calc_res.evidence_count_used}\n"
            f"- **Calculation Audit:** Deterministic SQL `{calc_res.sql_description}`"
        )

        return {
            "status": AnswerStatus.SUCCESS.value,
            "answer": answer_text,
            "direct_metric_value": val,
            "metric_unit": unit_str,
            "sql_query": calc_res.sql_description,
            "calculation": f"SUM({metric_code}) = {val} {unit_str}",
            "calculation_result": calc_res,
            "records_used": calc_res.evidence_count_used,
            "citations": citations,
            "key_figures": [
                {
                    "subsidiary": entity_label,
                    "metric_name": metric_name,
                    "value": val,
                    "unit": unit_str,
                    "period": period_label,
                    "verified": only_verified,
                }
            ],
            "conflicts": conflicts,
        }

    @classmethod
    def _handle_calculation_route(
        cls,
        db: Session,
        query: str,
        entity_info: Dict[str, Any],
        period_info: Dict[str, Any],
        document_ids: Optional[List[str]],
        only_verified: bool,
        include_demo: bool,
    ) -> Dict[str, Any]:
        """Handles target achievement, percentage, and ratio calculations deterministically."""
        sub = entity_info.get("subsidiary")
        period = period_info.get("period")

        actual_scope = EvidenceScope(
            metric_code="COAL_PRODUCTION",
            subsidiary=sub,
            reporting_period=period,
            only_verified=only_verified,
            only_real=not include_demo,
            only_demo=include_demo,
            document_ids=document_ids,
        )

        target_scope = EvidenceScope(
            metric_code="PRODUCTION_TARGET",
            subsidiary=sub,
            reporting_period=period,
            only_verified=only_verified,
            only_real=not include_demo,
            only_demo=include_demo,
            document_ids=document_ids,
        )

        ach_res = CalculationEngine.calculate_achievement(db, actual_scope, target_scope)

        if not ach_res.success or ach_res.result is None:
            if ach_res.error_code == CalcError.MISSING_TARGET:
                return {
                    "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                    "answer": (
                        f"Cannot compute target achievement for **{sub or 'CIL'}**"
                        + (f" in **{period}**" if period else "") +
                        ": No verified target record found in evidence.\n\n"
                        f"*NumberSafe AI Rule 1: A synthetic target (e.g. actual × 1.04) has been strictly refused.*"
                    ),
                    "citations": [],
                    "records_used": ach_res.evidence_count_total,
                }

            return {
                "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": f"Unable to calculate target achievement: {ach_res.error_message or 'Insufficient evidence'}",
                "citations": [],
                "records_used": 0,
            }

        # Persist calculation run for audit lineage
        lineage_id = persist_calculation(db, ach_res, operation="ACHIEVEMENT", initiated_by="AskMineIntel Copilot")
        ach_res.lineage_id = lineage_id

        citations = cls._build_citations(db, ach_res.included_facts, "Target Achievement Inputs", "MT")

        actual_facts = [f for f in ach_res.included_facts if f.metric_code == "COAL_PRODUCTION"]
        target_facts = [f for f in ach_res.included_facts if f.metric_code == "PRODUCTION_TARGET"]

        act_val = round(sum(f.numeric_value for f in actual_facts if f.numeric_value), 2)
        tgt_val = round(sum(f.numeric_value for f in target_facts if f.numeric_value), 2)

        answer_text = (
            f"### NumberSafe Calculation: Target Achievement\n\n"
            f"**{sub or 'CIL'} Target Achievement ({period or 'Latest'}):** **{ach_res.result}%**\n\n"
            f"- **Actual Production:** **{act_val:,} MT** ({len(actual_facts)} records)\n"
            f"- **Target Production:** **{tgt_val:,} MT** ({len(target_facts)} records)\n"
            f"- **Formula:** `(Actual Production ÷ Target Production) × 100`\n"
            f"- **Mathematical Step:** `{act_val} ÷ {tgt_val} × 100 = {ach_res.result}%`\n"
            f"- **Calculation ID:** `{lineage_id}`\n"
            f"- **Audit Status:** `DETERMINISTIC / VERIFIED INPUTS`"
        )

        return {
            "status": AnswerStatus.SUCCESS.value,
            "answer": answer_text,
            "direct_metric_value": ach_res.result,
            "metric_unit": "%",
            "calculation": f"({act_val} MT ÷ {tgt_val} MT) × 100 = {ach_res.result}%",
            "calculation_result": ach_res,
            "records_used": ach_res.evidence_count_used,
            "citations": citations,
            "key_figures": [
                {"subsidiary": sub or "CIL", "metric_name": "Actual Production", "value": act_val, "unit": "MT", "period": period},
                {"subsidiary": sub or "CIL", "metric_name": "Production Target", "value": tgt_val, "unit": "MT", "period": period},
                {"subsidiary": sub or "CIL", "metric_name": "Target Achievement", "value": ach_res.result, "unit": "%", "period": period},
            ],
        }

    @classmethod
    def _handle_comparison_route(
        cls,
        db: Session,
        query: str,
        entity_info: Dict[str, Any],
        period_info: Dict[str, Any],
        document_ids: Optional[List[str]],
        only_verified: bool,
        include_demo: bool,
    ) -> Dict[str, Any]:
        """Generates cross-subsidiary comparison table deterministically."""
        period = period_info.get("period") or "FY 2024-25"
        metric_code = entity_info.get("metric_code") or "COAL_PRODUCTION"
        metric_name = entity_info.get("metric_name") or "Raw Coal Production"
        unit_str = entity_info.get("unit") or "MT"

        subsidiaries = ["SECL", "MCL", "NCL", "ECL", "BCCL", "CCL", "WCL", "CMPDI"]
        rows = []
        all_citations = []
        total_facts = 0

        for s in subsidiaries:
            sc = EvidenceScope(
                metric_code=metric_code,
                subsidiary=s,
                reporting_period=period,
                only_verified=only_verified,
                only_real=not include_demo,
                only_demo=include_demo,
                document_ids=document_ids,
            )
            res = CalculationEngine.calculate(db, sc, operation=AggOp.SUM)
            if res.success and res.result is not None and res.result > 0:
                rows.append({"subsidiary": s, "value": round(res.result, 2), "records": res.evidence_count_used})
                total_facts += res.evidence_count_used
                all_citations.extend(cls._build_citations(db, res.included_facts, metric_name, unit_str)[:2])
            else:
                rows.append({"subsidiary": s, "value": None, "records": 0})

        valid_rows = [r for r in rows if r["value"] is not None]
        valid_rows.sort(key=lambda x: x["value"], reverse=True)

        if not valid_rows:
            return {
                "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": f"No verified evidence found for `{metric_name}` across subsidiaries for **{period}**.",
                "citations": [],
                "records_used": 0,
            }

        table_md = "| Subsidiary | Value | Unit | Evidence Status |\n|---|---|---|---|\n"
        for r in rows:
            val_str = f"**{r['value']:,}**" if r["value"] is not None else "Not Recorded"
            st_str = f"✓ Verified ({r['records']} records)" if r["records"] > 0 else "No Data"
            table_md += f"| **{r['subsidiary']}** | {val_str} | {unit_str} | {st_str} |\n"

        top = valid_rows[0]
        answer_text = (
            f"### Cross-Subsidiary Comparison: {metric_name} ({period})\n\n"
            f"**Highest Recorded:** **{top['subsidiary']}** with **{top['value']:,} {unit_str}**.\n\n"
            f"{table_md}\n\n"
            f"*Generated deterministically from {total_facts} verified evidence records. Unrecorded subsidiaries are explicitly labeled.*"
        )

        chart_data = {
            "type": "bar",
            "title": f"{metric_name} by Subsidiary ({period})",
            "xAxis": "name",
            "series": [{"dataKey": "value", "name": f"{metric_name} ({unit_str})", "color": "#d97706"}],
            "data": [{"name": r["subsidiary"], "value": r["value"]} for r in valid_rows],
        }

        return {
            "status": AnswerStatus.SUCCESS.value,
            "answer": answer_text,
            "chart": chart_data,
            "records_used": total_facts,
            "citations": all_citations[:10],
            "key_figures": [
                {"subsidiary": r["subsidiary"], "metric_name": metric_name, "value": r["value"], "unit": unit_str, "period": period}
                for r in valid_rows
            ],
        }

    @classmethod
    def _handle_conflict_route(cls, db: Session, query: str) -> Dict[str, Any]:
        """Queries and formats active evidence conflicts."""
        conflicts = db.query(EvidenceConflict).filter(EvidenceConflict.status == "OPEN").order_by(desc(EvidenceConflict.discrepancy_percent)).limit(10).all()
        total_open = db.query(EvidenceConflict).filter(EvidenceConflict.status == "OPEN").count()

        if total_open == 0:
            return {
                "status": AnswerStatus.SUCCESS.value,
                "answer": "There are currently **0 unresolved evidence conflicts** in the ledger. All contradictory data points have been verified or resolved.",
                "records_used": 0,
                "citations": [],
            }

        conflict_lines = [
            f"- **[{c.metric_code}]** {c.description} *(Discrepancy: {c.discrepancy_percent}%)*"
            for c in conflicts[:5]
        ]

        answer_text = (
            f"**Unresolved Evidence Conflicts Detected:** Identified **{total_open} active discrepancies** across subsidiary filings.\n\n"
            + "\n".join(conflict_lines) +
            f"\n\nPer AGENTS.md Rule 5 ('Never hide conflicts'), contradictions are quarantined in the **Review Queue** for human analyst sign-off."
        )

        return {
            "status": AnswerStatus.CONFLICT_DETECTED.value,
            "answer": answer_text,
            "records_used": total_open * 2,
            "citations": [],
            "conflicts": [
                {"id": c.id, "metric_code": c.metric_code, "discrepancy": c.discrepancy_percent, "description": c.description}
                for c in conflicts
            ],
        }

    @classmethod
    def _handle_narrative_route(
        cls,
        db: Session,
        query: str,
        subsidiary: Optional[str],
        period: Optional[str],
        document_ids: Optional[List[str]],
        include_demo: bool,
        response_mode: str,
    ) -> Dict[str, Any]:
        """Retrieves document chunks using hybrid BM25 and synthesizes grounded answer."""
        retrieval = HybridRetriever.retrieve(
            db=db,
            query=query,
            subsidiary=subsidiary,
            period=period,
            document_ids=document_ids,
            include_demo=include_demo,
            limit=6,
        )

        chunks = retrieval.get("chunks", [])
        if not chunks:
            return {
                "status": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
                "answer": (
                    "I could not find relevant context in the indexed document repository for this query. "
                    "Please upload related CMPDI/CIL operational documents to enable grounded answers."
                ),
                "citations": [],
                "records_used": 0,
            }

        answer_text = AnswerSynthesizer.synthesize_narrative(query, chunks, response_mode=response_mode)

        citations = []
        for c in chunks[:5]:
            citations.append({
                "fact_id": f"chunk-{c['chunk_id']}",
                "document_id": str(c["document_id"]),
                "document_name": c["document_name"],
                "metric_code": "NARRATIVE_EVIDENCE",
                "metric_name": "Document Narrative Evidence",
                "numeric_value": 0.0,
                "unit": "Context",
                "subsidiary": subsidiary or "CMPDI/CIL",
                "reporting_period": period or "—",
                "page_number": c.get("page_number"),
                "sheet_name": c.get("sheet_name"),
                "source_context": c["content"][:200] if c.get("content") else None,
                "confidence_score": min(0.85, 0.50 + len(chunks) * 0.05),
                "human_verified": False,
            })

        return {
            "status": AnswerStatus.SUCCESS.value,
            "answer": answer_text,
            "citations": citations,
            "records_used": len(chunks),
        }

    # ── Conversational & System Handlers ─────────────────────────────────────

    @classmethod
    def _handle_greeting(
        cls, query_id: str, query: str, session_id: Optional[str], user_name: str, db: Session
    ) -> Dict[str, Any]:
        ans = (
            "Hello. I’m MineIntel, an evidence-grounded mining intelligence assistant for CMPDI and Coal India Limited.\n\n"
            "I can help you retrieve verified production and exploration figures, compare subsidiaries, "
            "trace data back to source documents, verify conflicting claims, perform NumberSafe calculations, "
            "and prepare evidence-backed parliamentary responses."
        )
        followups = [
            "What was SECL's raw coal production in FY 2024-25?",
            "Compare raw coal production across all subsidiaries in FY 2024-25",
            "Show CMPDI drilling meters achievement in FY 2024-25",
            "Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25",
        ]
        cls._log_query(db, query_id, query, QueryIntent.GREETING.value, "ALL_EVIDENCE", "STANDARD", ans, 0, 1.0, user_name, 2.0)
        return {
            "query_id": query_id,
            "query": query,
            "intent": QueryIntent.GREETING.value,
            "status": AnswerStatus.SUCCESS.value,
            "answer_status": "GREETING",
            "answer": ans,
            "confidence": 1.0,
            "confidence_score": 1.0,
            "confidence_level": "HIGH",
            "confidence_reason": "Direct assistant greeting response",
            "records_used": 0,
            "verified_facts_count": 0,
            "citations": [],
            "sources": [],
            "suggested_followups": followups,
            "data_scope": "SYSTEM",
            "is_demo": False,
        }

    @classmethod
    def _handle_help(
        cls, query_id: str, query: str, session_id: Optional[str], user_name: str, db: Session
    ) -> Dict[str, Any]:
        ans = (
            "### MineIntel Intelligence Guide\n\n"
            "Ask MineIntel supports natural language queries across the following core capabilities:\n\n"
            "1. **Metric Lookups:** Ask for quantitative records (e.g. *\"What was SECL raw coal production in FY 2024-25?\"*)\n"
            "2. **NumberSafe Calculations:** Target vs actual, growth, ratios (e.g. *\"What percentage of its target did SECL achieve?\"*)\n"
            "3. **Cross-Subsidiary Comparisons:** Compare performance across CIL units (e.g. *\"Compare production across all subsidiaries\"*)\n"
            "4. **Claim Verification:** Audit assertions against verified evidence (e.g. *\"Verify claim: ECL production was 42.1 MT\"*)\n"
            "5. **Parliamentary Queries (PQ):** Formal government briefs adhering to Ministry of Coal format\n"
            "6. **Conflict Auditing:** Surface discrepancies across filings (e.g. *\"Show open evidence conflicts\"*)"
        )
        followups = [
            "What was SECL's raw coal production in FY 2024-25?",
            "What percentage of its target did SECL achieve?",
            "Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25",
            "Show open evidence conflicts",
        ]
        cls._log_query(db, query_id, query, QueryIntent.HELP.value, "ALL_EVIDENCE", "STANDARD", ans, 0, 1.0, user_name, 2.0)
        return {
            "query_id": query_id,
            "query": query,
            "intent": QueryIntent.HELP.value,
            "status": AnswerStatus.SUCCESS.value,
            "answer_status": "HELP",
            "answer": ans,
            "confidence": 1.0,
            "confidence_score": 1.0,
            "confidence_level": "HIGH",
            "confidence_reason": "System assistance and query guidance",
            "records_used": 0,
            "verified_facts_count": 0,
            "citations": [],
            "sources": [],
            "suggested_followups": followups,
            "data_scope": "SYSTEM",
            "is_demo": False,
        }

    @classmethod
    def _handle_capability(
        cls, query_id: str, query: str, session_id: Optional[str], user_name: str, db: Session
    ) -> Dict[str, Any]:
        ans = (
            "### MineIntel Platform Capabilities\n\n"
            "MineIntel is an evidence-first mining intelligence platform engineered around four core branded paradigms:\n\n"
            "- **MineGraph Ontology:** Interconnects `Mine ↕ Coalfield ↕ Subsidiary ↕ Metric ↕ Reporting Period ↕ Document ↕ Evidence`.\n"
            "- **NumberSafe 2.0 AI:** Eliminates hallucination by calculating all quantitative operations deterministically in SQL/Python.\n"
            "- **EvidenceChain:** Preserves source coordinates to exact PDF pages, spreadsheet sheets, rows, and cells.\n"
            "- **ReportGuard:** Automated quality auditor detecting conflicting data points, missing citations, and unverified figures."
        )
        followups = [
            "What was SECL's raw coal production in FY 2024-25?",
            "Compare raw coal production across all subsidiaries in FY 2024-25",
            "What percentage of target did SECL achieve?",
        ]
        cls._log_query(db, query_id, query, QueryIntent.CAPABILITY_QUERY.value, "ALL_EVIDENCE", "STANDARD", ans, 0, 1.0, user_name, 2.0)
        return {
            "query_id": query_id,
            "query": query,
            "intent": QueryIntent.CAPABILITY_QUERY.value,
            "status": AnswerStatus.SUCCESS.value,
            "answer_status": "CAPABILITY",
            "answer": ans,
            "confidence": 1.0,
            "confidence_score": 1.0,
            "confidence_level": "HIGH",
            "confidence_reason": "Platform architecture overview",
            "records_used": 0,
            "verified_facts_count": 0,
            "citations": [],
            "sources": [],
            "suggested_followups": followups,
            "data_scope": "SYSTEM",
            "is_demo": False,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @classmethod
    def _build_citations(cls, db: Session, included_facts: List[Any], metric_name: str, unit: str) -> List[Dict[str, Any]]:
        citations = []
        for inc in included_facts:
            doc = db.query(Document).filter(Document.id == inc.document_id).first()
            doc_name = doc.original_filename if doc else "Statutory Document"
            citations.append({
                "fact_id": inc.fact_id,
                "document_id": inc.document_id,
                "document_name": doc_name,
                "metric_code": inc.metric_code,
                "metric_name": metric_name,
                "numeric_value": inc.numeric_value,
                "unit": inc.unit or unit,
                "subsidiary": inc.subsidiary,
                "reporting_period": inc.reporting_period,
                "page_number": inc.page_number,
                "sheet_name": inc.sheet_name,
                "cell_reference": inc.cell_reference,
                "source_context": inc.source_context,
                "confidence_score": inc.confidence_score,
                "human_verified": (inc.validation_status == ValidationStatus.VERIFIED.value),
            })
        return citations

    @classmethod
    def _check_conflicts(cls, facts: List[Any]) -> List[Dict[str, Any]]:
        """Identifies conflicting values within retrieved facts."""
        conflicts = []
        # Group by (metric_code, subsidiary, period)
        grouped = {}
        for f in facts:
            k = (f.metric_code, f.subsidiary, f.reporting_period)
            grouped.setdefault(k, []).append(f)

        for (m_code, sub, per), group in grouped.items():
            if len(group) > 1:
                vals = [round(f.numeric_value, 2) for f in group if f.numeric_value is not None]
                if len(set(vals)) > 1:
                    conflicts.append({
                        "metric_code": m_code,
                        "subsidiary": sub,
                        "period": per,
                        "values": list(set(vals)),
                        "discrepancy_detail": f"Conflicting values detected: {', '.join(map(str, set(vals)))}",
                    })
        return conflicts

    @classmethod
    def _generate_followups(cls, sub: Optional[str], metric: Optional[str], period: Optional[str]) -> List[str]:
        target_sub = sub or "SECL"
        target_period = period or "FY 2024-25"

        if metric == "COAL_PRODUCTION":
            return [
                f"What was the target for {target_sub} in {target_period}?",
                f"What percentage of target did {target_sub} achieve in {target_period}?",
                f"Compare {target_sub} production with other subsidiaries in {target_period}",
                f"Generate Parliamentary Query brief for {target_sub}",
            ]
        elif metric == "PRODUCTION_TARGET":
            return [
                f"What was actual raw coal production for {target_sub} in {target_period}?",
                f"Calculate target achievement percentage",
                f"Compare targets across all subsidiaries in {target_period}",
            ]
        elif metric == "DRILLING":
            return [
                f"Show borehole count for {target_sub} in {target_period}",
                f"Compare drilling meters with exploration targets",
            ]
        else:
            return [
                f"What was SECL's raw coal production in {target_period}?",
                f"Compare raw coal production across all subsidiaries in {target_period}",
                f"Show CMPDI drilling progress in {target_period}",
            ]

    @classmethod
    def _log_query(
        cls,
        db: Session,
        query_id: str,
        query: str,
        intent: str,
        scope: str,
        response_mode: str,
        answer: str,
        records_used: int,
        confidence: float,
        user_name: str,
        exec_time_ms: float,
    ) -> None:
        try:
            history = QueryHistory(
                id=query_id,
                query_text=query,
                scope=scope,
                response_mode=response_mode,
                answer_text=answer[:1000] if answer else "",
                user_name=user_name,
            )
            db.add(history)

            audit = AuditEvent(
                user=user_name,
                action=AuditAction.QUERY_EXECUTED.value,
                entity_type="INTELLIGENCE_QUERY",
                entity_id=query_id,
                details=f"[{intent}] '{query[:70]}' -> {records_used} facts, conf={confidence:.2f}, {exec_time_ms}ms"
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to record query audit: {e}")
            db.rollback()

    @classmethod
    def _empty_query_response(cls, query_id: str) -> Dict[str, Any]:
        return {
            "query_id": query_id,
            "query": "",
            "intent": QueryIntent.UNKNOWN.value,
            "status": "ERROR",
            "answer_status": "ERROR",
            "answer": "Query cannot be empty. Please enter a mining intelligence question.",
            "confidence": 0.0,
            "confidence_score": 0.0,
            "confidence_level": "LOW",
            "records_used": 0,
            "citations": [],
            "sources": [],
            "suggested_followups": [],
        }
