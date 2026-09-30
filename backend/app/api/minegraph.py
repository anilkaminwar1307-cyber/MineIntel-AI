"""
Phase 9 — MineGraph API
Serves the ontology graph of Mine ↔ Coalfield ↔ Subsidiary ↔ Metric ↔ Document ↔ Evidence
as graph-ready node/edge JSON for interactive D3 / force-graph visualization.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.validation import EvidenceConflict

router = APIRouter(prefix="/minegraph", tags=["MineGraph"])

# ─── Color + type config ─────────────────────────────────────────────────────
NODE_COLORS = {
    "CIL": "#f59e0b",          # Amber — root parent
    "SUBSIDIARY": "#3b82f6",   # Blue
    "COALFIELD": "#10b981",    # Green
    "MINE": "#8b5cf6",         # Purple
    "METRIC": "#ef4444",       # Red
    "DOCUMENT": "#64748b",     # Slate
}

SUBSIDIARIES = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CMPDI"]

COALFIELD_MAP = {
    "ECL": ["Raniganj", "Birbhum"],
    "BCCL": ["Jharia"],
    "CCL": ["North Karanpura", "South Karanpura", "Ramgarh", "Bokaro"],
    "WCL": ["Wardha Valley", "Pench", "Kanhan"],
    "SECL": ["Korba", "Mand Raigarh", "Hasdeo-Arand", "Sohagpur"],
    "MCL": ["Ib Valley", "Talcher"],
    "NCL": ["Singrauli"],
    "CMPDI": ["Exploration Zones"],
}

TOP_METRICS = [
    "COAL_PRODUCTION", "PRODUCTION_TARGET", "OVERBURDEN_REMOVAL",
    "COAL_DISPATCH", "DRILLING_METERS", "STRIPPING_RATIO",
]


@router.get("/graph")
def get_minegraph(
    subsidiary: Optional[str] = Query(None, description="Filter to a single subsidiary"),
    metric_code: Optional[str] = Query(None, description="Filter to a specific metric"),
    include_documents: bool = Query(False, description="Include document nodes (adds density)"),
    include_metrics: bool = Query(True, description="Include metric nodes"),
    max_mines: int = Query(30, description="Maximum mine nodes to include"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns MineGraph as {nodes, edges, stats} for D3 / react-force-graph rendering.
    Hierarchy: CIL → Subsidiary → Coalfield → Mine → Metric → Document
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    node_ids: set = set()

    def add_node(node_id: str, label: str, node_type: str, value: float = 1.0,
                 extra: Optional[Dict] = None):
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        n = {
            "id": node_id,
            "label": label,
            "type": node_type,
            "color": NODE_COLORS.get(node_type, NODE_COLORS.get(node_type, "#94a3b8")),
            "size": value,
        }
        if extra:
            n.update(extra)
        nodes.append(n)

    def add_edge(source: str, target: str, rel: str, weight: float = 1.0):
        edges.append({"source": source, "target": target, "relation": rel, "weight": weight})

    # ─── Root: CIL ───
    add_node("CIL", "Coal India Limited", "CIL", value=40,
             extra={"description": "Parent holding company", "level": 0})

    # ─── Pull live data from DB ───
    # Fact counts per subsidiary + coalfield + mine
    q = db.query(
        ExtractedFact.subsidiary,
        ExtractedFact.coalfield,
        ExtractedFact.mine,
        ExtractedFact.metric_code,
        func.count(ExtractedFact.id).label("cnt"),
        func.avg(ExtractedFact.numeric_value).label("avg_val"),
    ).filter(
        ExtractedFact.subsidiary.isnot(None),
        ExtractedFact.numeric_value.isnot(None),
    )

    if subsidiary:
        q = q.filter(ExtractedFact.subsidiary == subsidiary)
    if metric_code:
        q = q.filter(ExtractedFact.metric_code == metric_code)

    q = q.group_by(
        ExtractedFact.subsidiary,
        ExtractedFact.coalfield,
        ExtractedFact.mine,
        ExtractedFact.metric_code,
    )

    rows = q.all()

    # Track what mines we've added to respect max_mines
    mines_added = 0
    subsidiaries_in_data = set()
    coalfields_in_data = set()

    for row in rows:
        sub = row.subsidiary
        cf = row.coalfield or f"{sub} Operations"
        mine = row.mine
        metric = row.metric_code
        cnt = row.cnt
        avg_val = row.avg_val or 0

        # Subsidiary node
        sub_id = f"SUB_{sub}"
        if sub_id not in node_ids:
            fact_cnt_sub = db.query(func.count(ExtractedFact.id)).filter(
                ExtractedFact.subsidiary == sub
            ).scalar() or 0
            add_node(sub_id, sub, "SUBSIDIARY", value=max(10, min(30, fact_cnt_sub / 10)),
                     extra={"fact_count": fact_cnt_sub, "level": 1})
            add_edge("CIL", sub_id, "OWNS", weight=2.0)
            subsidiaries_in_data.add(sub)

        # Coalfield node
        cf_id = f"CF_{sub}_{cf}".replace(" ", "_")
        if cf_id not in node_ids:
            add_node(cf_id, cf, "COALFIELD", value=8,
                     extra={"subsidiary": sub, "level": 2})
            add_edge(sub_id, cf_id, "OPERATES", weight=1.5)
            coalfields_in_data.add(cf_id)

        # Mine node (cap at max_mines)
        if mine and mines_added < max_mines:
            mine_id = f"MINE_{sub}_{mine}".replace(" ", "_")
            if mine_id not in node_ids:
                add_node(mine_id, mine, "MINE", value=5,
                         extra={"coalfield": cf, "subsidiary": sub, "level": 3})
                add_edge(cf_id, mine_id, "CONTAINS", weight=1.0)
                mines_added += 1

        # Metric node
        if include_metrics and metric in TOP_METRICS:
            metric_id = f"METRIC_{metric}"
            if metric_id not in node_ids:
                label = metric.replace("_", " ").title()
                add_node(metric_id, label, "METRIC", value=6,
                         extra={"metric_code": metric, "level": 4})

            # Link mine or coalfield to metric
            if mine and mines_added <= max_mines:
                mine_id = f"MINE_{sub}_{mine}".replace(" ", "_")
                if mine_id in node_ids:
                    edge_id = f"{mine_id}→{metric_id}"
                    add_edge(mine_id, metric_id, "REPORTS", weight=round(cnt / 10, 1))
            else:
                edge_id = f"{cf_id}→{metric_id}"
                add_edge(cf_id, metric_id, "REPORTS", weight=round(cnt / 10, 1))

    # ─── Add subsidiaries with no data (from canonical list) ──────────────────
    subs_to_add = [subsidiary] if subsidiary else SUBSIDIARIES
    for sub in subs_to_add:
        sub_id = f"SUB_{sub}"
        if sub_id not in node_ids:
            add_node(sub_id, sub, "SUBSIDIARY", value=10,
                     extra={"fact_count": 0, "level": 1})
            add_edge("CIL", sub_id, "OWNS", weight=2.0)

        for cf in COALFIELD_MAP.get(sub, []):
            cf_id = f"CF_{sub}_{cf}".replace(" ", "_")
            if cf_id not in node_ids:
                add_node(cf_id, cf, "COALFIELD", value=6,
                         extra={"subsidiary": sub, "level": 2})
                add_edge(sub_id, cf_id, "OPERATES", weight=1.0)

    # ─── Optional: Document nodes ─────────────────────────────────────────────
    if include_documents:
        docs_q = db.query(Document).filter(Document.status == "PROCESSED").limit(20).all()
        for doc in docs_q:
            doc_id = f"DOC_{doc.id}"
            add_node(doc_id, doc.original_filename[:30], "DOCUMENT", value=4,
                     extra={"document_id": doc.id, "file_type": doc.file_type,
                            "fact_count": doc.fact_count, "level": 5})
            if doc.organization and f"SUB_{doc.organization}" in node_ids:
                add_edge(f"SUB_{doc.organization}", doc_id, "SOURCE", weight=0.5)

    # ─── Conflict edges ───────────────────────────────────────────────────────
    conflicts = db.query(EvidenceConflict).filter(
        EvidenceConflict.status == "OPEN"
    ).limit(10).all()

    if conflicts:
        conflict_fact_ids = []
        for c in conflicts:
            conflict_fact_ids.extend([c.primary_fact_id, c.conflicting_fact_id])
        c_facts_map = {f.id: f for f in db.query(ExtractedFact).filter(ExtractedFact.id.in_(conflict_fact_ids)).all()} if conflict_fact_ids else {}

        for conflict in conflicts:
            pf = c_facts_map.get(conflict.primary_fact_id)
            cf = c_facts_map.get(conflict.conflicting_fact_id)
            sub = (pf.subsidiary if pf else (cf.subsidiary if cf else None)) or getattr(conflict, "subsidiary", None)
            if sub:
                sub_id = f"SUB_{sub}"
                if sub_id in node_ids and conflict.metric_code:
                    metric_id = f"METRIC_{conflict.metric_code}"
                    if metric_id in node_ids:
                        edges.append({
                            "source": sub_id,
                            "target": metric_id,
                            "relation": "CONFLICT",
                            "weight": 0.3,
                            "conflict": True,
                        })

    # ─── Stats ────────────────────────────────────────────────────────────────
    total_facts = db.query(func.count(ExtractedFact.id)).scalar() or 0
    total_docs = db.query(func.count(Document.id)).scalar() or 0

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "subsidiaries": len(subsidiaries_in_data),
            "coalfields": len(coalfields_in_data),
            "mines": mines_added,
            "total_facts_in_db": total_facts,
            "total_documents": total_docs,
        },
    }


@router.get("/subsidiaries")
def get_subsidiary_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns per-subsidiary fact counts, mine counts, and top metrics for the
    MineGraph summary panel.
    """
    results = []
    for sub in SUBSIDIARIES:
        fact_cnt = db.query(func.count(ExtractedFact.id)).filter(
            ExtractedFact.subsidiary == sub
        ).scalar() or 0

        mine_cnt = db.query(func.count(distinct(ExtractedFact.mine))).filter(
            ExtractedFact.subsidiary == sub,
            ExtractedFact.mine.isnot(None),
        ).scalar() or 0

        top_metrics_q = (
            db.query(ExtractedFact.metric_code, func.count(ExtractedFact.id).label("cnt"))
            .filter(ExtractedFact.subsidiary == sub)
            .group_by(ExtractedFact.metric_code)
            .order_by(func.count(ExtractedFact.id).desc())
            .limit(3)
            .all()
        )

        results.append({
            "subsidiary": sub,
            "coalfields": COALFIELD_MAP.get(sub, []),
            "fact_count": fact_cnt,
            "mine_count": mine_cnt,
            "top_metrics": [{"metric_code": m.metric_code, "count": m.cnt} for m in top_metrics_q],
        })

    return {"subsidiaries": results, "total": len(results)}


@router.get("/paths")
def get_evidence_path(
    fact_id: str = Query(..., description="Fact ID to trace full provenance path"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the full MineGraph path for a single ExtractedFact:
    CIL → Subsidiary → Coalfield → Mine → Metric → Fact → Document
    """
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Fact not found")

    doc = db.query(Document).filter(Document.id == fact.document_id).first()

    path = [
        {"level": 0, "type": "CIL", "label": "Coal India Limited", "id": "CIL"},
        {"level": 1, "type": "SUBSIDIARY", "label": fact.subsidiary or "Unknown", "id": f"SUB_{fact.subsidiary}"},
        {"level": 2, "type": "COALFIELD", "label": fact.coalfield or f"{fact.subsidiary} Operations",
         "id": f"CF_{fact.subsidiary}_{fact.coalfield}"},
        {"level": 3, "type": "MINE", "label": fact.mine or "Unspecified Mine", "id": f"MINE_{fact.mine}"},
        {"level": 4, "type": "METRIC", "label": fact.metric_name, "id": f"METRIC_{fact.metric_code}"},
        {"level": 5, "type": "FACT", "label": f"{fact.numeric_value} {fact.unit}",
         "id": fact.id, "value": fact.numeric_value, "unit": fact.unit,
         "period": fact.reporting_period, "confidence": fact.confidence_score},
        {
            "level": 6, "type": "DOCUMENT",
            "label": doc.original_filename if doc else "Unknown",
            "id": fact.document_id,
            "page_number": fact.page_number,
            "sheet_name": fact.sheet_name,
            "cell_reference": fact.cell_reference,
            "source_context": fact.source_context,
        },
    ]

    return {"fact_id": fact_id, "path": path, "path_length": len(path)}
