from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ScanPlanToolConfig(BaseModel):
    tool_name: str
    enabled: bool = True
    config: Dict[str, Any] = {}


class ScanPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    options: Dict[str, Any] = {}


class ScanPlanCreate(ScanPlanBase):
    tools: List[ScanPlanToolConfig] = []


class ScanPlanUpdate(BaseModel):
    description: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    tools: Optional[List[ScanPlanToolConfig]] = None


class ScanPlanInDB(ScanPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tools: Optional[List[ScanPlanToolConfig]] = None  # 扫描方案中的工具配置

    class Config:
        from_attributes = True


class TaskLogInDB(BaseModel):
    id: int
    task_id: int
    phase: str
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


