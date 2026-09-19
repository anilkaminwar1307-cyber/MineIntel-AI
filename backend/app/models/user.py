from sqlalchemy import Column, String, Boolean, DateTime
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False, default="CMPDI Analyst")
    role = Column(String(50), nullable=False, default="Analyst")  # Analyst, Reviewer, Admin
    organization = Column(String(100), nullable=False, default="CMPDI / CIL")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
