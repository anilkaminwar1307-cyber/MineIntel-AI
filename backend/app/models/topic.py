from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class Topic(Base):
    """
    Topic intelligence categories and themes discovered across mining documentation.
    """
    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, default="Operational")  # Geological, Production, Environmental, Safety
    mention_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    mentions = relationship("TopicMention", back_populates="topic", cascade="all, delete-orphan")


class TopicMention(Base):
    """
    Occurrence of a topic inside a document chunk.
    """
    __tablename__ = "topic_mentions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    topic = relationship("Topic", back_populates="mentions")
