# 领域驱动资产聚合系统实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现新的领域驱动资产聚合系统，用 Domain → IP → Endpoint 三层架构替代现有的扁平 Asset 表

**Architecture:** 创建新的 domains/domain_ips/domain_endpoints 三张表，实现查询时聚合逻辑，保留各来源原始数据，支持任务级隔离

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, React, TypeScript

---

## 阶段1：数据库迁移（零停机）

### Task 1.1: 创建 Alembic 迁移脚本

**Files:**
- Create: `alembic/versions/20260308_add_domain_driven_tables.py`

**Step 1: 生成迁移文件**

```bash
cd /Users/liqinggong/Documents/Information_gathering_and_scanning_tools/security_platform
source .venv/bin/activate
alembic revision -m "add domain driven aggregation tables"
```

**Step 2: 编写迁移脚本**

```python
"""add domain driven aggregation tables

Revision ID: xxxxxxxxxxxx
Revises: previous_revision
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'xxxxxxxxxxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 domains 表
    op.create_table(
        'domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('root_domain', sa.String(255), nullable=True),
        sa.Column('discovered_by', sa.String(50), nullable=False, server_default='subfinder'),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('scan_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('ip_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('endpoint_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'task_id', 'name')
    )

    op.create_index('idx_domains_task', 'domains', ['tenant_id', 'task_id'])
    op.create_index('idx_domains_root', 'domains', ['tenant_id', 'root_domain'])
    op.create_index('idx_domains_status', 'domains', ['tenant_id', 'scan_status'])

    # 创建 domain_ips 表
    op.create_table(
        'domain_ips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('protocol', sa.String(20), nullable=True),
        sa.Column('sources', postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column('discovered_by', postgresql.JSONB(), nullable=True),
        sa.Column('product', sa.String(255), nullable=True),
        sa.Column('product_version', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('banner', sa.Text(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'domain_id', 'ip_address', 'port')
    )

    op.create_index('idx_domain_ips_domain', 'domain_ips', ['domain_id'])
    op.create_index('idx_domain_ips_ip', 'domain_ips', ['ip_address'])
    op.create_index('idx_domain_ips_sources', 'domain_ips', ['sources'], postgresql_using='gin')

    # 创建 domain_endpoints 表
    op.create_table(
        'domain_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('domain_ip_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(2048), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='GET'),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(255), nullable=True),
        sa.Column('content_length', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('technologies', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('discovered_by', sa.String(50), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('response_body_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['domain_ip_id'], ['domain_ips.id'], ondelete='CASCADE')
    )

    op.create_index('idx_endpoints_ip', 'domain_endpoints', ['domain_ip_id'])
    op.create_index('idx_endpoints_path', 'domain_endpoints', ['path'])


def downgrade():
    op.drop_table('domain_endpoints')
    op.drop_table('domain_ips')
    op.drop_table('domains')
```

**Step 3: 执行迁移**

```bash
alembic upgrade head
```

Expected: 成功创建三张新表

**Step 4: Commit**

```bash
git add alembic/versions/20260308_add_domain_driven_tables.py
git commit -m "db(migration): add domains, domain_ips, domain_endpoints tables

- Create new domain-driven aggregation tables
- Add indexes for performance
- Zero downtime migration"
```

---

### Task 1.2: 添加 SQLAlchemy 模型

**Files:**
- Modify: `app/db/models.py`

**Step 1: 在 models.py 底部添加新模型**

```python
# ============================================
# Domain-Driven Aggregation Models
# ============================================

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # e.g., api.example.com
    root_domain = Column(String(255), nullable=True)  # e.g., example.com

    discovered_by = Column(String(50), default="subfinder")
    discovered_at = Column(DateTime, default=datetime.utcnow)

    scan_status = Column(String(20), default="pending")  # pending, scanning, completed, failed

    # Statistics (updated after aggregation)
    ip_count = Column(Integer, default=0)
    endpoint_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="domains")
    task = relationship("Task", back_populates="domains")
    ips = relationship("DomainIP", back_populates="domain", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "name"),
    )


class DomainIP(Base):
    __tablename__ = "domain_ips"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)

    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), nullable=True)

    sources = Column(JSON, default=list)  # ['fofa', 'hunter']
    discovered_by = Column(JSON, default=dict)  # {fofa: {first_seen, count}, ...}

    # Technical fingerprint
    product = Column(String(255), nullable=True)
    product_version = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    banner = Column(Text, nullable=True)

    raw_data = Column(JSON, default=dict)  # Raw response from sources

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    task = relationship("Task")
    domain = relationship("Domain", back_populates="ips")
    endpoints = relationship("DomainEndpoint", back_populates="domain_ip", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "domain_id", "ip_address", "port"),
    )


class DomainEndpoint(Base):
    __tablename__ = "domain_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    domain_ip_id = Column(Integer, ForeignKey("domain_ips.id"), nullable=False, index=True)

    path = Column(String(2048), nullable=False)
    method = Column(String(10), default="GET")

    status_code = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    content_length = Column(Integer, nullable=True)

    title = Column(String(512), nullable=True)
    technologies = Column(JSON, default=list)

    discovered_by = Column(String(50), nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    response_body_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    domain_ip = relationship("DomainIP", back_populates="endpoints")
```

**Step 2: 更新 Tenant 关系**

```python
# 在 Tenant 类中添加
class Tenant(Base):
    # ... existing columns ...

    # Add new relationships
    domains = relationship("Domain", back_populates="tenant")
```

**Step 3: 更新 Task 关系**

```python
# 在 Task 类中添加
class Task(Base):
    # ... existing columns ...

    # Add new relationships
    domains = relationship("Domain", back_populates="task")
```

**Step 4: Commit**

```bash
git add app/db/models.py
git commit -m "feat(models): add Domain, DomainIP, DomainEndpoint models

- SQLAlchemy models for domain-driven aggregation
- Define relationships between new entities
- Add JSON columns for flexible data storage"
```

---

## 阶段2：核心服务实现

### Task 2.1: 创建 DomainAggregationService

**Files:**
- Create: `app/services/domain_aggregation.py`

**Step 1: 创建服务文件**

```python
"""Domain-driven asset aggregation service."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.models import Domain, DomainIP, DomainEndpoint


class DomainAggregationService:
    """
    域名资产聚合服务

    将分散的 DomainIP 记录聚合为统一的展示视图
    支持查询时聚合，保留原始数据可追溯
    """

    def __init__(self, db: Session):
        self.db = db

    def get_domain_with_assets(self, domain_id: int) -> Dict[str, Any]:
        """
        获取域名及其聚合后的资产视图

        Args:
            domain_id: Domain ID

        Returns:
            包含域名信息和聚合后IP列表的字典
        """
        domain = self.db.query(Domain).get(domain_id)
        if not domain:
            return None

        # 获取该域名下所有IP
        ips = self.db.query(DomainIP).filter(
            DomainIP.domain_id == domain_id
        ).all()

        # 按 IP+Port 分组聚合
        ip_groups: Dict[tuple, Dict[str, Any]] = {}

        for ip in ips:
            key = (ip.ip_address, ip.port)

            if key not in ip_groups:
                ip_groups[key] = {
                    "id": ip.id,
                    "ip": ip.ip_address,
                    "port": ip.port,
                    "protocol": ip.protocol,
                    "sources": set(),
                    "products": {},
                    "banners": {},
                    "first_seen": ip.created_at,
                    "endpoint_count": 0,
                }

            # 合并来源
            if ip.sources:
                ip_groups[key]["sources"].update(ip.sources)

            # 合并产品信息
            if ip.sources:
                for source in ip.sources:
                    if ip.product:
                        ip_groups[key]["products"][source] = ip.product
                    if ip.banner:
                        ip_groups[key]["banners"][source] = ip.banner

        # 获取每个IP的端点数量
        for key, data in ip_groups.items():
            ip_id = data["id"]
            endpoint_count = self.db.query(DomainEndpoint).filter(
                DomainEndpoint.domain_ip_id == ip_id
            ).count()
            data["endpoint_count"] = endpoint_count

        # 转换为列表并排序
        aggregated_ips = [
            {
                **data,
                "sources": sorted(list(data["sources"])),
            }
            for data in ip_groups.values()
        ]
        aggregated_ips.sort(key=lambda x: (x["ip"], x["port"]))

        # 计算总来源数
        all_sources = set()
        for ip in ips:
            if ip.sources:
                all_sources.update(ip.sources)

        return {
            "id": domain.id,
            "name": domain.name,
            "root_domain": domain.root_domain,
            "scan_status": domain.scan_status,
            "discovered_by": domain.discovered_by,
            "discovered_at": domain.discovered_at,
            "ip_count": len(ip_groups),
            "endpoint_count": sum(ip["endpoint_count"] for ip in aggregated_ips),
            "source_count": len(all_sources),
            "sources": sorted(list(all_sources)),
            "ips": aggregated_ips,
            "created_at": domain.created_at,
            "updated_at": domain.updated_at,
        }

    def list_domains(
        self,
        tenant_id: int,
        task_id: Optional[int] = None,
        root_domain: Optional[str] = None,
        scan_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Domain], int]:
        """
        列出域名列表

        Returns:
            (domains list, total count)
        """
        query = self.db.query(Domain).filter(Domain.tenant_id == tenant_id)

        if task_id:
            query = query.filter(Domain.task_id == task_id)
        if root_domain:
            query = query.filter(Domain.root_domain == root_domain)
        if scan_status:
            query = query.filter(Domain.scan_status == scan_status)

        total = query.count()
        domains = query.order_by(Domain.created_at.desc()).offset(skip).limit(limit).all()

        return domains, total

    def get_unique_domains(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取租户下唯一的域名列表（跨任务去重）

        取每个域名最新任务的数据
        """
        # 子查询：获取每个域名最新的记录
        subquery = self.db.query(
            Domain.name,
            func.max(Domain.created_at).label('latest')
        ).filter(
            Domain.tenant_id == tenant_id
        ).group_by(
            Domain.name
        ).subquery()

        # 获取最新记录
        latest_domains = self.db.query(Domain).join(
            subquery,
            and_(
                Domain.name == subquery.c.name,
                Domain.created_at == subquery.c.latest
            )
        ).order_by(Domain.name).offset(skip).limit(limit).all()

        return [
            self.get_domain_with_assets(d.id)
            for d in latest_domains
        ]

    def create_domain(
        self,
        tenant_id: int,
        task_id: int,
        name: str,
        root_domain: Optional[str] = None,
        discovered_by: str = "subfinder",
    ) -> Domain:
        """创建新域名记录"""
        domain = Domain(
            tenant_id=tenant_id,
            task_id=task_id,
            name=name.lower().strip(),
            root_domain=root_domain.lower().strip() if root_domain else None,
            discovered_by=discovered_by,
            scan_status="pending",
        )
        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def create_or_update_domain_ip(
        self,
        tenant_id: int,
        task_id: int,
        domain_id: int,
        ip_address: str,
        port: int,
        protocol: Optional[str] = None,
        source: str = "",
        product: Optional[str] = None,
        banner: Optional[str] = None,
        raw_data: Optional[Dict] = None,
    ) -> DomainIP:
        """
        创建或更新 DomainIP 记录

        如果同一 domain + ip + port 已存在，则合并来源信息
        """
        existing = self.db.query(DomainIP).filter(
            DomainIP.tenant_id == tenant_id,
            DomainIP.domain_id == domain_id,
            DomainIP.ip_address == ip_address,
            DomainIP.port == port,
        ).first()

        current_time = datetime.utcnow()

        if existing:
            # 更新现有记录
            existing.sources = list(set((existing.sources or []) + [source]))

            discovered_by = existing.discovered_by or {}
            if source not in discovered_by:
                discovered_by[source] = {
                    "first_seen": current_time.isoformat(),
                    "count": 1,
                }
            else:
                discovered_by[source]["count"] = discovered_by[source].get("count", 0) + 1
            existing.discovered_by = discovered_by

            if product:
                existing.product = product
            if banner:
                existing.banner = banner
            if protocol:
                existing.protocol = protocol
            if raw_data:
                existing_raw = existing.raw_data or {}
                existing_raw[source] = raw_data
                existing.raw_data = existing_raw

            existing.updated_at = current_time
            self.db.commit()
            self.db.refresh(existing)
            return existing

        else:
            # 创建新记录
            domain_ip = DomainIP(
                tenant_id=tenant_id,
                task_id=task_id,
                domain_id=domain_id,
                ip_address=ip_address,
                port=port,
                protocol=protocol,
                sources=[source],
                discovered_by={
                    source: {
                        "first_seen": current_time.isoformat(),
                        "count": 1,
                    }
                },
                product=product,
                banner=banner,
                raw_data={source: raw_data} if raw_data else {},
            )
            self.db.add(domain_ip)
            self.db.commit()
            self.db.refresh(domain_ip)
            return domain_ip

    def update_domain_stats(self, domain_id: int) -> None:
        """更新域名的统计信息"""
        domain = self.db.query(Domain).get(domain_id)
        if not domain:
            return

        ip_count = self.db.query(DomainIP).filter(
            DomainIP.domain_id == domain_id
        ).count()

        endpoint_count = self.db.query(DomainEndpoint).join(
            DomainIP
        ).filter(
            DomainIP.domain_id == domain_id
        ).count()

        # 计算来源数
        ips = self.db.query(DomainIP).filter(
            DomainIP.domain_id == domain_id
        ).all()

        all_sources = set()
        for ip in ips:
            if ip.sources:
                all_sources.update(ip.sources)

        domain.ip_count = ip_count
        domain.endpoint_count = endpoint_count
        domain.source_count = len(all_sources)
        domain.updated_at = datetime.utcnow()

        self.db.commit()
```

**Step 2: Commit**

```bash
git add app/services/domain_aggregation.py
git commit -m "feat(service): add DomainAggregationService

- Query-time aggregation logic
- Cross-task unique domain listing
- Create/update with source merging"
```

---

### Task 2.2: 创建 Pydantic Schemas

**Files:**
- Create: `app/schemas/domain.py`

**Step 1: 创建 schema 文件**

```python
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
```

**Step 2: Commit**

```bash
git add app/schemas/domain.py
git commit -m "feat(schemas): add Pydantic schemas for domain aggregation

- Domain, DomainIP, DomainEndpoint schemas
- Aggregated view schemas for API responses"
```

---

## 阶段3：API 端点实现

### Task 3.1: 创建 Domains API

**Files:**
- Create: `app/api/v1/endpoints/domains.py`

**Step 1: 创建 API 文件**

```python
"""Domain-driven asset aggregation API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_db, get_current_user
from app.db.models import User
from app.schemas.domain import (
    DomainListResponse,
    DomainDetailResponse,
    EndpointListResponse,
)
from app.services.domain_aggregation import DomainAggregationService

router = APIRouter()


@router.get("/", response_model=DomainListResponse)
def list_domains(
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    root_domain: Optional[str] = Query(None, description="Filter by root domain"),
    scan_status: Optional[str] = Query(None, description="Filter by scan status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: User = Depends(get_current_user),
):
    """List domains with filters."""
    service = DomainAggregationService(db)

    domains, total = service.list_domains(
        tenant_id=tenant_id,
        task_id=task_id,
        root_domain=root_domain,
        scan_status=scan_status,
        skip=skip,
        limit=limit,
    )

    # Convert to list items with aggregated sources
    items = []
    for domain in domains:
        detail = service.get_domain_with_assets(domain.id)
        items.append({
            "id": domain.id,
            "name": domain.name,
            "root_domain": domain.root_domain,
            "scan_status": domain.scan_status,
            "ip_count": domain.ip_count,
            "endpoint_count": domain.endpoint_count,
            "sources": detail.get("sources", []),
            "discovered_at": domain.discovered_at,
        })

    return {
        "items": items,
        "total": total,
    }


@router.get("/unique", response_model=list[DomainDetailResponse])
def list_unique_domains(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: User = Depends(get_current_user),
):
    """List unique domains across all tasks (latest version per domain)."""
    service = DomainAggregationService(db)
    return service.get_unique_domains(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{domain_id}", response_model=DomainDetailResponse)
def get_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: User = Depends(get_current_user),
):
    """Get domain details with aggregated IPs."""
    service = DomainAggregationService(db)

    # Check ownership
    from app.db.models import Domain
    domain = db.query(Domain).filter(
        Domain.id == domain_id,
        Domain.tenant_id == tenant_id,
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    result = service.get_domain_with_assets(domain_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    return result


@router.get("/{domain_id}/ips", response_model=list[dict])
def get_domain_ips(
    domain_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: User = Depends(get_current_user),
):
    """Get aggregated IPs for a domain."""
    service = DomainAggregationService(db)

    # Check ownership
    from app.db.models import Domain
    domain = db.query(Domain).filter(
        Domain.id == domain_id,
        Domain.tenant_id == tenant_id,
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    result = service.get_domain_with_assets(domain_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    return result.get("ips", [])


@router.get("/ips/{ip_id}/endpoints", response_model=EndpointListResponse)
def get_ip_endpoints(
    ip_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: User = Depends(get_current_user),
):
    """Get endpoints for a specific DomainIP."""
    from app.db.models import DomainIP, DomainEndpoint

    # Check ownership
    ip = db.query(DomainIP).filter(
        DomainIP.id == ip_id,
        DomainIP.tenant_id == tenant_id,
    ).first()

    if not ip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP not found",
        )

    endpoints = db.query(DomainEndpoint).filter(
        DomainEndpoint.domain_ip_id == ip_id,
    ).offset(skip).limit(limit).all()

    total = db.query(DomainEndpoint).filter(
        DomainEndpoint.domain_ip_id == ip_id,
    ).count()

    return {
        "items": endpoints,
        "total": total,
    }
```

**Step 2: 注册路由**

Modify: `app/api/v1/api.py`

```python
from app.api.v1.endpoints import domains

# Add router
api_router.include_router(domains.router, prefix="/domains", tags=["domains"])
```

**Step 3: Commit**

```bash
git add app/api/v1/endpoints/domains.py app/api/v1/api.py
git commit -m "feat(api): add domain-driven aggregation endpoints

- GET /domains - list domains with filters
- GET /domains/unique - cross-task unique domains
- GET /domains/{id} - domain detail with aggregated IPs
- GET /domains/{id}/ips - aggregated IPs
- GET /domains/ips/{ip_id}/endpoints - IP endpoints"
```

---

## 阶段4：任务执行流程修改

### Task 4.1: 修改 Subfinder 结果处理

**Files:**
- Modify: `app/workers/tasks.py:1761-1840`

**Step 1: 替换 Subfinder 聚合逻辑**

将现有的 `_aggregate_subfinder_assets` 调用替换为新的 Domain 创建逻辑：

```python
# 聚合 Subfinder 数据
from app.services.domain_aggregation import DomainAggregationService

try:
    subfinder_before = db.query(SubfinderAsset).filter(
        SubfinderAsset.tenant_id == tenant_id,
        SubfinderAsset.task_id == task_id_local
    ).count()

    # 新逻辑：创建 Domain 记录
    service = DomainAggregationService(db)

    if subfinder_result and not subfinder_result.get("error"):
        seed_domains = subfinder_result.get("domains", [])
        created_domains = 0

        for domain_name in seed_domains:
            domain_name = domain_name.strip().lower()
            if not domain_name:
                continue

            # 提取根域名
            root_domain = extract_root_domain(domain_name)

            # 创建 Domain 记录
            try:
                domain = service.create_domain(
                    tenant_id=tenant_id,
                    task_id=task_id_local,
                    name=domain_name,
                    root_domain=root_domain,
                    discovered_by="subfinder",
                )
                created_domains += 1
            except IntegrityError:
                # 同一任务中重复的域名，跳过
                db.rollback()
                continue

        _log_task(task_id, "aggregate", f"Subfinder 域名处理完成: {len(seed_domains)} 个域名，创建 {created_domains} 条 Domain 记录", level="info")

except Exception as e:
    _log_task(task_id, "aggregate", f"Subfinder 处理失败({type(e).__name__}): {str(e)}", level="error")
```

**Step 2: 添加根域名提取函数**

在 `app/workers/tasks.py` 中添加：

```python
def extract_root_domain(domain: str) -> str:
    """提取根域名，如 api.example.com -> example.com"""
    parts = domain.lower().strip().split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return domain
```

**Step 3: Commit**

```bash
git add app/workers/tasks.py
git commit -m "feat(tasks): update subfinder processing to create Domain records

- Replace _aggregate_subfinder_assets with Domain creation
- Extract root domain for organization
- Create Domain record per discovered subdomain"
```

---

### Task 4.2: 修改 FOFA/Hunter 结果处理

**Files:**
- Modify: `app/workers/tasks.py:1836-1898`

**Step 1: 修改第二轮查询结果处理**

将 `_aggregate_assets_from_sources` 替换为新的 DomainIP 创建逻辑：

```python
# 第二轮聚合完成后，将结果写入 domain_ips
try:
    affected2 = _aggregate_assets_from_sources(db, task=task)
    _log_task(task_id, "aggregate", f"第二輪聚合完成: 寫入/更新 {affected2} 筆", level="info")

    # 新逻辑：将第二轮结果写入 domain_ips
    service = DomainAggregationService(db)

    # 获取该任务下的所有 domains
    domains = db.query(Domain).filter(
        Domain.tenant_id == tenant_id,
        Domain.task_id == task_id,
    ).all()

    for domain in domains:
        # 查询该 domain 对应的 FofaAsset 和 HunterAsset
        fofa_assets = db.query(FofaAsset).filter(
            FofaAsset.tenant_id == tenant_id,
            FofaAsset.task_id == task_id,
            FofaAsset.domain == domain.name,
        ).all()

        hunter_assets = db.query(HunterAsset).filter(
            HunterAsset.tenant_id == tenant_id,
            HunterAsset.task_id == task_id,
            HunterAsset.domain == domain.name,
        ).all()

        # 创建/更新 DomainIP 记录
        for asset in fofa_assets:
            if asset.ip_address and asset.port:
                service.create_or_update_domain_ip(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    domain_id=domain.id,
                    ip_address=asset.ip_address,
                    port=asset.port,
                    protocol=asset.protocol,
                    source="fofa",
                    product=asset.product,
                    banner=asset.data.get("banner") if asset.data else None,
                    raw_data=asset.data,
                )

        for asset in hunter_assets:
            if asset.ip_address and asset.port:
                service.create_or_update_domain_ip(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    domain_id=domain.id,
                    ip_address=asset.ip_address,
                    port=asset.port,
                    protocol=asset.protocol,
                    source="hunter",
                    product=asset.product,
                    banner=asset.data.get("banner") if asset.data else None,
                    raw_data=asset.data,
                )

        # 更新 Domain 统计
        service.update_domain_stats(domain.id)

        # 更新 Domain 状态
        domain.scan_status = "completed"
        db.commit()

    _log_task(task_id, "aggregate", f"DomainIP 记录创建完成", level="info")

except Exception as e:
    _log_task(task_id, "aggregate", f"第二輪聚合失敗({type(e).__name__}): {str(e)}", level="error")
```

**Step 2: Commit**

```bash
git add app/workers/tasks.py
git commit -m "feat(tasks): update FOFA/Hunter processing to create DomainIP records

- Replace _aggregate_assets_from_sources with DomainIP creation
- Create/merge DomainIP records from FofaAsset/HunterAsset
- Update Domain statistics after aggregation"
```

---

## 阶段5：前端适配

### Task 5.1: 创建 Domain API 客户端

**Files:**
- Create: `frontend/src/utils/domainApi.ts`

**Step 1: 创建 API 客户端**

```typescript
import { apiClient } from './api'

export interface Domain {
  id: number
  name: string
  root_domain?: string
  scan_status: 'pending' | 'scanning' | 'completed' | 'failed'
  ip_count: number
  endpoint_count: number
  sources: string[]
  discovered_at: string
}

export interface AggregatedIP {
  id: number
  ip: string
  port: number
  protocol?: string
  sources: string[]
  products: Record<string, string>
  banners?: Record<string, string>
  endpoint_count: number
  first_seen: string
}

export interface DomainDetail {
  id: number
  name: string
  root_domain?: string
  scan_status: string
  discovered_by: string
  discovered_at: string
  ip_count: number
  endpoint_count: number
  source_count: number
  sources: string[]
  ips: AggregatedIP[]
  created_at: string
  updated_at: string
}

export const domainsAPI = {
  list: (params?: {
    task_id?: number
    root_domain?: string
    scan_status?: string
    skip?: number
    limit?: number
  }) => apiClient.get('/domains/', { params }),

  getUnique: (params?: { skip?: number; limit?: number }) =>
    apiClient.get('/domains/unique', { params }),

  get: (id: number) => apiClient.get<DomainDetail>(`/domains/${id}`),

  getIPs: (domainId: number) => apiClient.get<AggregatedIP[]>(`/domains/${domainId}/ips`),

  getEndpoints: (ipId: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get(`/domains/ips/${ipId}/endpoints`, { params }),
}
```

**Step 2: Commit**

```bash
git add frontend/src/utils/domainApi.ts
git commit -m "feat(frontend): add Domain API client

- Domain list/get API methods
- AggregatedIP type definitions
- Unique domains listing"
```

---

### Task 5.2: 创建 Domains 页面

**Files:**
- Create: `frontend/src/pages/Domains.tsx`

**Step 1: 创建基础页面框架**

```tsx
import React, { useState, useEffect } from 'react'
import { Table, Card, Tag, Badge, Space, Button, Input, Select } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { domainsAPI, Domain } from '../utils/domainApi'

const Domains: React.FC = () => {
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    task_id: undefined as number | undefined,
    root_domain: '',
    scan_status: undefined as string | undefined,
  })

  const loadDomains = async (skip = 0, limit = 50) => {
    setLoading(true)
    try {
      const res = await domainsAPI.list({
        ...filters,
        skip,
        limit,
      })
      setDomains(res.data.items)
      setTotal(res.data.total)
    } catch (error) {
      console.error('Failed to load domains:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDomains()
  }, [filters])

  const columns: ColumnsType<Domain> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '域名',
      dataIndex: 'name',
      render: (name: string, record: Domain) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontWeight: 'bold' }}>{name}</span>
          {record.root_domain && (
            <Tag size="small" color="default">{record.root_domain}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'scan_status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'default', text: '等待中' },
          scanning: { color: 'processing', text: '扫描中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '失败' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Badge status={config.color as any} text={config.text} />
      },
    },
    {
      title: '来源',
      dataIndex: 'sources',
      width: 150,
      render: (sources: string[]) => (
        <Space size={4}>
          {sources.map((s) => (
            <Tag key={s} color="blue" size="small">{s}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'IP数',
      dataIndex: 'ip_count',
      width: 80,
    },
    {
      title: '端点数',
      dataIndex: 'endpoint_count',
      width: 80,
    },
    {
      title: '发现时间',
      dataIndex: 'discovered_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record: Domain) => (
        <Button type="link" onClick={() => showDomainDetail(record)}>
          详情
        </Button>
      ),
    },
  ]

  const showDomainDetail = (domain: Domain) => {
    // TODO: 实现详情弹窗或跳转
    console.log('Show detail for domain:', domain)
  }

  return (
    <Card title="域名资产">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="根域名"
          value={filters.root_domain}
          onChange={(e) => setFilters({ ...filters, root_domain: e.target.value })}
          onSearch={() => loadDomains()}
          style={{ width: 200 }}
        />
        <Select
          placeholder="状态"
          allowClear
          value={filters.scan_status}
          onChange={(value) => setFilters({ ...filters, scan_status: value })}
          style={{ width: 120 }}
          options={[
            { value: 'pending', label: '等待中' },
            { value: 'scanning', label: '扫描中' },
            { value: 'completed', label: '已完成' },
            { value: 'failed', label: '失败' },
          ]}
        />
        <Button type="primary" onClick={() => loadDomains()}>
          查询
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={domains}
        rowKey="id"
        loading={loading}
        pagination={{
          total,
          pageSize: 50,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        onChange={(pagination) => {
          loadDomains(
            (pagination.current! - 1) * pagination.pageSize!,
            pagination.pageSize!
          )
        }}
      />
    </Card>
  )
}

export default Domains
```

**Step 2: 添加路由**

Modify: `frontend/src/App.tsx` 或路由配置文件

```tsx
import Domains from './pages/Domains'

// Add route
<Route path="/domains" element={<Domains />} />
```

**Step 3: 添加导航菜单**

Modify: `frontend/src/components/Layout/Menu.tsx`

```tsx
{
  key: '/domains',
  icon: <GlobalOutlined />,
  label: '域名资产',
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/Domains.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add Domains management page

- Domain list with filters
- Aggregated sources display
- IP/Endpoint counts"
```

---

## 阶段6：数据迁移（可选）

### Task 6.1: 创建历史数据迁移脚本

**Files:**
- Create: `scripts/migrate_to_domain_driven.py`

**Step 1: 创建迁移脚本**

```python
#!/usr/bin/env python3
"""
Migrate existing Asset data to new domain-driven schema.

Run: python scripts/migrate_to_domain_driven.py
"""

import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '/Users/liqinggong/Documents/Information_gathering_and_scanning_tools/security_platform')

from app.core.config import settings
from app.db.models import (
    Asset, Domain, DomainIP,
    SubfinderAsset, FofaAsset, HunterAsset
)


def extract_root_domain(domain: str) -> str:
    """Extract root domain."""
    parts = domain.lower().strip().split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return domain


def migrate_task_domains(db, task_id: int, tenant_id: int):
    """Migrate data for a single task."""
    print(f"Migrating task {task_id}...")

    # Get subfinder assets for this task
    subfinder_assets = db.query(SubfinderAsset).filter(
        SubfinderAsset.task_id == task_id,
        SubfinderAsset.tenant_id == tenant_id,
    ).all()

    domain_map = {}  # name -> Domain

    # Create Domain records from subfinder
    for sf in subfinder_assets:
        domain_name = sf.domain.lower().strip()
        if not domain_name or domain_name in domain_map:
            continue

        root = extract_root_domain(domain_name)

        domain = Domain(
            tenant_id=tenant_id,
            task_id=task_id,
            name=domain_name,
            root_domain=root,
            discovered_by="subfinder",
            discovered_at=sf.created_at or datetime.utcnow(),
            scan_status="completed",
        )
        db.add(domain)
        db.flush()  # Get domain.id
        domain_map[domain_name] = domain

    # Also create domains from FofaAsset/HunterAsset that might not be in subfinder
    fofa_assets = db.query(FofaAsset).filter(
        FofaAsset.task_id == task_id,
        FofaAsset.tenant_id == tenant_id,
    ).all()

    for fa in fofa_assets:
        if not fa.domain:
            continue
        domain_name = fa.domain.lower().strip()
        if domain_name in domain_map:
            continue

        root = extract_root_domain(domain_name)

        domain = Domain(
            tenant_id=tenant_id,
            task_id=task_id,
            name=domain_name,
            root_domain=root,
            discovered_by="fofa",
            discovered_at=fa.created_at or datetime.utcnow(),
            scan_status="completed",
        )
        db.add(domain)
        db.flush()
        domain_map[domain_name] = domain

    # Create DomainIP records from FofaAsset/HunterAsset
    ip_records = {}  # (domain_id, ip, port) -> DomainIP

    for fa in fofa_assets:
        if not fa.domain or not fa.ip_address or not fa.port:
            continue

        domain = domain_map.get(fa.domain.lower().strip())
        if not domain:
            continue

        key = (domain.id, fa.ip_address, fa.port)
        if key not in ip_records:
            ip_records[key] = DomainIP(
                tenant_id=tenant_id,
                task_id=task_id,
                domain_id=domain.id,
                ip_address=fa.ip_address,
                port=fa.port,
                protocol=fa.protocol,
                sources=["fofa"],
                discovered_by={
                    "fofa": {
                        "first_seen": fa.created_at.isoformat() if fa.created_at else datetime.utcnow().isoformat(),
                        "count": 1,
                    }
                },
                product=fa.product,
                raw_data=fa.data,
                created_at=fa.created_at or datetime.utcnow(),
            )

    hunter_assets = db.query(HunterAsset).filter(
        HunterAsset.task_id == task_id,
        HunterAsset.tenant_id == tenant_id,
    ).all()

    for ha in hunter_assets:
        if not ha.domain or not ha.ip_address or not ha.port:
            continue

        domain = domain_map.get(ha.domain.lower().strip())
        if not domain:
            continue

        key = (domain.id, ha.ip_address, ha.port)
        if key in ip_records:
            # Merge with existing
            existing = ip_records[key]
            if "hunter" not in existing.sources:
                existing.sources.append("hunter")
            existing.discovered_by = existing.discovered_by or {}
            existing.discovered_by["hunter"] = {
                "first_seen": ha.created_at.isoformat() if ha.created_at else datetime.utcnow().isoformat(),
                "count": 1,
            }
        else:
            ip_records[key] = DomainIP(
                tenant_id=tenant_id,
                task_id=task_id,
                domain_id=domain.id,
                ip_address=ha.ip_address,
                port=ha.port,
                protocol=ha.protocol,
                sources=["hunter"],
                discovered_by={
                    "hunter": {
                        "first_seen": ha.created_at.isoformat() if ha.created_at else datetime.utcnow().isoformat(),
                        "count": 1,
                    }
                },
                product=ha.product,
                raw_data=ha.data,
                created_at=ha.created_at or datetime.utcnow(),
            )

    # Add all DomainIP records
    for ip in ip_records.values():
        db.add(ip)

    # Update domain stats
    for domain in domain_map.values():
        ip_count = len([ip for ip in ip_records.values() if ip.domain_id == domain.id])
        domain.ip_count = ip_count
        domain.source_count = len(set([
            source for ip in ip_records.values()
            if ip.domain_id == domain.id
            for source in (ip.sources or [])
        ]))

    db.commit()
    print(f"  Created {len(domain_map)} domains, {len(ip_records)} IPs")


def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get all unique task IDs from existing data
        from sqlalchemy import distinct

        task_ids = db.query(distinct(Asset.task_id)).filter(
            Asset.task_id.isnot(None)
        ).all()

        print(f"Found {len(task_ids)} tasks to migrate")

        for (task_id,) in task_ids:
            # Get tenant_id for this task
            asset = db.query(Asset).filter(Asset.task_id == task_id).first()
            if not asset:
                continue

            migrate_task_domains(db, task_id, asset.tenant_id)

        print("Migration completed!")

    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/migrate_to_domain_driven.py
git commit -m "feat(migration): add historical data migration script

- Migrate existing Asset data to new domain-driven schema
- Create Domain records from SubfinderAsset
- Create DomainIP records from FofaAsset/HunterAsset
- Merge sources when IP+Port exists in multiple sources"
```

---

## 实施顺序建议

```
阶段1: 数据库迁移（零停机）
  └── Task 1.1: 创建 Alembic 迁移脚本
  └── Task 1.2: 添加 SQLAlchemy 模型

阶段2: 核心服务实现
  └── Task 2.1: 创建 DomainAggregationService
  └── Task 2.2: 创建 Pydantic Schemas

阶段3: API 端点实现
  └── Task 3.1: 创建 Domains API

阶段4: 任务执行流程修改
  └── Task 4.1: 修改 Subfinder 结果处理
  └── Task 4.2: 修改 FOFA/Hunter 结果处理

阶段5: 前端适配
  └── Task 5.1: 创建 Domain API 客户端
  └── Task 5.2: 创建 Domains 页面

阶段6: 数据迁移（可选）
  └── Task 6.1: 创建历史数据迁移脚本
```

---

**计划完成！**

保存路径：`docs/plans/2026-03-08-domain-driven-aggregation-implementation.md`

**执行方式选择：**

1. **Subagent-Driven（本会话）** - 我为每个任务分派子代理，在任务之间进行审查，快速迭代

2. **并行会话（独立）** - 在新的会话中使用 executing-plans 技能，批量执行并设置检查点

**选择哪种方式？**
