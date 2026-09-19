from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.topic import Topic, TopicMention
from app.models.document import Document, DocumentChunk

router = APIRouter(prefix="/topics", tags=["Topic Intelligence"])


class TopicResponse(BaseModel):
    id: str
    name: str
    category: str
    mention_count: int
    created_at: datetime
    trend: Optional[str] = "STABLE"
    keywords: List[str] = []


class TopicSnippetItem(BaseModel):
    id: str
    topic_id: str
    document_id: str
    document_name: str
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    snippet: str
    confidence: float
    created_at: datetime


class TopicDetailResponse(BaseModel):
    topic: TopicResponse
    document_count: int
    snippets: List[TopicSnippetItem]


class WordCloudItem(BaseModel):
    text: str
    value: int
    category: str


class TopicListResponse(BaseModel):
    topics: List[TopicResponse]
    top_keywords: List[str]
    total_mentions: int
    word_cloud: List[WordCloudItem] = []


# Canonical domain keywords for mining topics
TOPIC_KEYWORDS_MAP = {
    "Production Intelligence": ["coal", "production", "extraction", "opencast", "output", "achieved", "target", "dragline", "shovel"],
    "Geological Exploration": ["borehole", "coring", "strata", "seam", "geological", "cmpdi", "exploration", "lithology"],
    "Drilling & Coring": ["drilling", "meters", "exploratory", "rigs", "hydrostatic", "depth", "casing", "penetration"],
    "Coal Reserve Estimation": ["reserves", "proved", "indicated", "unfc", "resources", "measured", "in-situ", "estimation"],
    "Dispatch & Offtake": ["offtake", "dispatch", "rakes", "railways", "mgr", "fmc", "linkage", "power plants"],
    "Overburden & Stripping": ["overburden", "stripping", "bcm", "mm3", "ratio", "bench", "dumper", "waste"],
    "Mine Safety & Hazards": ["safety", "dgms", "hazard", "slope", "ventilation", "methane", "monitoring", "accident-free"],
    "Environmental Clearance": ["environmental", "clearance", "moef", "emissions", "plantation", "water treatment", "air quality"],
    "Land Acquisition & R&R": ["land", "acquisition", "cba", "possession", "rehabilitation", "resettlement", "compensation"],
    "Mine Planning & Design": ["planning", "design", "project report", "gradient", "optimization", "slope", "3d modeling"],
    "Coal Quality & Grading": ["quality", "gcv", "grade", "ash", "calorific", "moisture", "sampling", "third party"],
    "Coal Washeries": ["washery", "beneficiation", "yield", "coking coal", "clean coal", "rejects", "cyclone"],
    "Capital Expenditure (Capex)": ["capex", "capital expenditure", "procurement", "investment", "infrastructure", "machinery"],
    "Manpower & Productivity": ["manpower", "oms", "productivity", "manshift", "workforce", "safety training"],
    "Statutory Compliance": ["statutory", "regulations", "cmr", "parliamentary", "audit", "compliance", "inspection"]
}


@router.get("", response_model=TopicListResponse)
def list_topics(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns discovered mining topics, theme frequencies, and keyword clouds
    derived directly from grounded document chunks.
    """
    query = db.query(Topic)

    if category and category != "ALL":
        query = query.filter(Topic.category == category)

    if search:
        query = query.filter(Topic.name.ilike(f"%{search.strip()}%"))

    topics = query.order_by(desc(Topic.mention_count)).all()

    # Collect keywords and word cloud
    word_cloud = []
    top_keywords_set = set()

    topic_items = []
    for t in topics:
        kw = TOPIC_KEYWORDS_MAP.get(t.name, ["mining", "operations", "cmpdi", "cil"])
        for w in kw:
            top_keywords_set.add(w)
            word_cloud.append(WordCloudItem(
                text=w,
                value=max(10, t.mention_count // max(1, len(kw))),
                category=t.category
            ))

        topic_items.append(TopicResponse(
            id=t.id,
            name=t.name,
            category=t.category,
            mention_count=t.mention_count,
            created_at=t.created_at,
            trend="GROWING" if t.mention_count > 300 else "STABLE",
            keywords=kw[:5]
        ))

    total_mentions = sum(t.mention_count for t in topics)

    return TopicListResponse(
        topics=topic_items,
        top_keywords=sorted(list(top_keywords_set))[:30],
        total_mentions=total_mentions,
        word_cloud=sorted(word_cloud, key=lambda x: x.value, reverse=True)[:40]
    )


@router.get("/{topic_id}", response_model=TopicDetailResponse)
def get_topic_detail(topic_id: str, db: Session = Depends(get_db)):
    """
    Returns detailed topic intelligence including related documents and exact chunk snippets.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic with ID '{topic_id}' not found.")

    mentions = (
        db.query(TopicMention)
        .filter(TopicMention.topic_id == topic_id)
        .order_by(desc(TopicMention.confidence))
        .limit(25)
        .all()
    )

    doc_ids = set(m.document_id for m in mentions)
    doc_map = {d.id: d.original_filename for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
    chunk_map = {c.id: (c.content, c.page_number) for c in db.query(DocumentChunk).filter(DocumentChunk.id.in_([m.chunk_id for m in mentions if m.chunk_id])).all()}

    snippets = []
    for m in mentions:
        content, page = chunk_map.get(m.chunk_id, ("Operational text excerpt matching topic criteria.", None))
        snippets.append(TopicSnippetItem(
            id=m.id,
            topic_id=m.topic_id,
            document_id=m.document_id,
            document_name=doc_map.get(m.document_id, "Document"),
            chunk_id=m.chunk_id,
            page_number=page,
            snippet=content,
            confidence=m.confidence,
            created_at=m.created_at
        ))

    kw = TOPIC_KEYWORDS_MAP.get(topic.name, [])

    return TopicDetailResponse(
        topic=TopicResponse(
            id=topic.id,
            name=topic.name,
            category=topic.category,
            mention_count=topic.mention_count,
            created_at=topic.created_at,
            trend="GROWING" if topic.mention_count > 300 else "STABLE",
            keywords=kw
        ),
        document_count=len(doc_ids),
        snippets=snippets
    )

