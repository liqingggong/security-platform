from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FingerprintRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    target: str = "url"
    pattern: str
    # 使用 meta 作為內部字段名，對外別名仍為 metadata
    meta: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    class Config:
        allow_population_by_field_name = True


class FingerprintRuleCreate(FingerprintRuleBase):
    pass


class FingerprintRuleUpdate(BaseModel):
    description: Optional[str] = None
    enabled: Optional[bool] = None
    target: Optional[str] = None
    pattern: Optional[str] = None
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

    class Config:
        allow_population_by_field_name = True


class FingerprintRuleInDB(FingerprintRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        allow_population_by_field_name = True


