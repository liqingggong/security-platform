from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.db.models import AssetType


class AssetInDB(BaseModel):
    id: int
    type: AssetType
    value: str
    # 規範化字段，方便前端聚合顯示
    domain: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    product: Optional[str] = None
    url: Optional[str] = None
    data: Dict[str, Any]
    tags: List[str]
    sources: List[str] = []  # 資產來源列表（fofa, hunter, subfinder 等）
    # CDN and aggregation fields
    is_cdn: bool = False
    cdn_provider: Optional[str] = None
    original_domain: Optional[str] = None
    is_aggregated: bool = False
    aggregated_count: int = 1
    technologies: List[str] = []
    discovered_at: datetime
    last_seen: datetime
    tenant_id: int
    task_id: Optional[int]

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    items: List[AssetInDB]
    total: int


class AssetFilter(BaseModel):
    type: Optional[AssetType] = None
    task_id: Optional[int] = None
    search: Optional[str] = None  # 搜索 value 字段
    tags: Optional[List[str]] = None


class AssetEnhanceRequest(BaseModel):
    """Request schema for batch asset enhancement.

    Attributes:
        task_ids: Optional list of task IDs to filter assets. If None, enhances all tenant assets.
        enable_cdn_detection: Whether to enable CDN detection in the pipeline.
        enable_protocol_inference: Whether to enable protocol inference in the pipeline.
        enable_fingerprint: Whether to enable fingerprint enhancement in the pipeline.
        enable_dedup: Whether to enable deduplication in the pipeline.
    """

    task_ids: Optional[List[int]] = None
    enable_cdn_detection: bool = True
    enable_protocol_inference: bool = True
    enable_fingerprint: bool = True
    enable_dedup: bool = True


class AssetEnhanceResponse(BaseModel):
    """Response schema for batch asset enhancement.

    Attributes:
        processed: Total number of assets processed.
        enhanced: Number of assets that were enhanced (had improvements applied).
        report: Detailed report of the enhancement operation.
    """

    processed: int
    enhanced: int
    report: Dict[str, Any]

