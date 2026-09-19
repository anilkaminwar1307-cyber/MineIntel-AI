from typing import Dict, Any, Optional
from pydantic import BaseModel


class ComponentStatus(BaseModel):
    name: str
    status: str  # OPERATIONAL, NOT_CONFIGURED, DEGRADED, ERROR
    details: Optional[str] = None
    category: str  # Core, AI, Storage, Analytics


class SystemSettingsStatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    demo_mode: bool
    record_counts: Optional[Dict[str, int]] = None
    components: Dict[str, ComponentStatus]

