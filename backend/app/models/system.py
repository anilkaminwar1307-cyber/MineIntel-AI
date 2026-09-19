from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base
from app.models.base import _utcnow


class SystemSetting(Base):
    """
    Key-value persistence for system-level configuration overrides.
    """
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
