"""Pydantic schemas for domain-driven aggregation."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


# ============================================
# Domain Schemas
# ============================================

class DomainBase(BaseModel):
    name: str
    root_domain: Optional[str] = None


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    scan_status: Optional[str] = None
    ip_count: Optional[int] = None
    endpoint_count: Optional[int] = None
    source_count: Optional[int] = None


class DomainInDB(DomainBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    task_id: int
    discovered_by: str
    discovered_at: datetime
    scan_status: str
    ip_count: int
    endpoint_count: int
    source_count: int
    created_at: datetime
    updated_at: datetime


class DomainListItem(BaseModel):
    """域名列表项（简化）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    root_domain: Optional[str]
    scan_status: str
    ip_count: int
    endpoint_count: int
    sources: List[str]
    discovered_at: datetime


# ============================================
# DomainIP Schemas
# ============================================

class DomainIPBase(BaseModel):
    ip_address: str
    port: int
    protocol: Optional[str] = None


class DomainIPCreate(DomainIPBase):
    source: str
    product: Optional[str] = None
    banner: Optional[str] = None


class DomainIPInDB(DomainIPBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    task_id: int
    domain_id: int
    sources: List[str]
    discovered_by: Dict[str, Any]
    product: Optional[str]
    banner: Optional[str]
    created_at: datetime
    updated_at: datetime


class AggregatedIP(BaseModel):
    """聚合后的IP视图"""
    id: int
    ip: str
    port: int
    protocol: Optional[str]
    sources: List[str]
    products: Dict[str, str]
    banners: Optional[Dict[str, str]]
    endpoint_count: int
    first_seen: datetime


# ============================================
# DomainEndpoint Schemas
# ============================================

class DomainEndpointBase(BaseModel):
    path: str
    method: str = "GET"


class DomainEndpointCreate(DomainEndpointBase):
    pass


class DomainEndpointInDB(DomainEndpointBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    domain_ip_id: int
    status_code: Optional[int]
    content_type: Optional[str]
    content_length: Optional[int]
    title: Optional[str]
    technologies: List[str]
    discovered_by: Optional[str]
    discovered_at: datetime


# ============================================
# API Response Schemas
# ============================================

class DomainDetailResponse(BaseModel):
    """域名详情响应（包含聚合后的IP）"""
    id: int
    name: str
    root_domain: Optional[str]
    scan_status: str
    discovered_by: str
    discovered_at: datetime
    ip_count: int
    endpoint_count: int
    source_count: int
    sources: List[str]
    ips: List[AggregatedIP]
    created_at: datetime
    updated_at: datetime


class DomainListResponse(BaseModel):
    """域名列表响应"""
    items: List[DomainListItem]
    total: int


class EndpointListResponse(BaseModel):
    """端点列表响应"""
    items: List[DomainEndpointInDB]
    total: int
