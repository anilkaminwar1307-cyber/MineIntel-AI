from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    id: str
    timestamp: datetime
    user: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditEventListResponse(BaseModel):
    items: List[AuditEventResponse]
    total: int
