"""Domain-driven asset aggregation API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_db, get_current_user
from app.db.models import User, Domain
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
            "sources": detail.get("sources", []) if detail else [],
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
