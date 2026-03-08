from collections import defaultdict
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_current_tenant_id, get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.asset import (
    AssetInDB,
    AssetFilter,
    AssetListResponse,
    AssetEnhanceRequest,
    AssetEnhanceResponse,
)
from app.services.asset_pipeline import AssetPipeline

router = APIRouter()


@router.get("", response_model=AssetListResponse)
def list_assets(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type: Optional[models.AssetType] = None,
    task_id: Optional[int] = None,
    task_ids: Optional[List[int]] = Query(None),
    search: Optional[str] = None,
    view: Optional[str] = Query(
        None, description="視圖：host(域名/IP)、service(端口)、url(URL級)"
    ),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    # DEBUG: Print request parameters
    print(f"[Assets Debug] Request: skip={skip}, limit={limit}, task_id={task_id}, tenant_id={tenant_id}")
    """
    列出當前租戶的所有資產
    支持按類型、任務ID、搜索關鍵字過濾
    """
    query = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id)

    # 按類型過濾
    if type:
        query = query.filter(models.Asset.type == type)

    # 按任務ID過濾（單個或多個）
    # 直接使用 task_id 過濾，確保只顯示該任務的資產
    if task_id:
        query = query.filter(models.Asset.task_id == task_id)
    if task_ids:
        query = query.filter(models.Asset.task_id.in_(task_ids))

    # 搜索關鍵字（在 value / domain / ip_address 中模糊）
    if search:
        query = query.filter(
            or_(
                models.Asset.value.contains(search),
                models.Asset.domain.contains(search),
                models.Asset.ip_address.contains(search),
            )
        )

    # 視圖快捷篩選
    if view == "host":
        # 主機視圖：域名/子域名/IP
        query = query.filter(
            or_(
                models.Asset.type.in_(
                    [models.AssetType.DOMAIN, models.AssetType.SUBDOMAIN, models.AssetType.IP]
                ),
                models.Asset.domain.isnot(None),
                models.Asset.ip_address.isnot(None),
            )
        )
    elif view == "service":
        # 端口/服務視圖
        query = query.filter(
            or_(
                models.Asset.port.isnot(None),
                models.Asset.type == models.AssetType.ENDPOINT,
            )
        )
    elif view == "url":
        # URL 視圖
        query = query.filter(
            or_(
                models.Asset.url.isnot(None),
                models.Asset.type == models.AssetType.URL,
            )
        )

    total = query.count()
    assets = query.order_by(models.Asset.discovered_at.desc()).offset(skip).limit(limit).all()
    # DEBUG: Print response
    print(f"[Assets Debug] Response: total={total}, returned={len(assets)}, skip={skip}, limit={limit}")
    return {"items": assets, "total": total}


@router.get("/aggregate")
def aggregate_assets(
    *,
    db: Session = Depends(get_db),
    view: str = Query(..., description="host/service/url"),
    task_ids: Optional[List[int]] = Query(None),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    资产聚合视图：
    - host: 按 domain+ip 聚合，返回开放端口数、资产数
    - service: 端口级列表
    - url: URL 级列表
    """
    query = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id)
    if task_ids:
        # 使用任務的開始時間範圍來查詢資產，而不是直接使用 task_id
        tasks = db.query(models.Task).filter(
            models.Task.id.in_(task_ids),
            models.Task.tenant_id == tenant_id
        ).all()
        if tasks:
            # 取最早的開始時間作為查詢起點
            min_start_time = min(t.started_at or t.created_at for t in tasks)
            query = query.filter(models.Asset.last_seen >= min_start_time)
        else:
            # 任務不存在，返回空結果
            query = query.filter(models.Asset.id == -1)  # 永遠不匹配的條件

    assets = query.all()

    if view == "host":
        host_map: Dict[str, Dict[str, Any]] = {}
        for a in assets:
            host_key = f"{a.domain or ''}|{a.ip_address or ''}" or a.value
            item = host_map.setdefault(
                host_key,
                {
                    "domain": a.domain,
                    "ip_address": a.ip_address,
                    "assets": 0,
                    "open_ports": set(),
                    "vulnerability_count": 0,
                },
            )
            item["assets"] += 1
            if a.port:
                item["open_ports"].add(a.port)
            if a.vulnerabilities:
                item["vulnerability_count"] += len(a.vulnerabilities)

        # 格式化输出
        result = []
        for _, v in host_map.items():
            result.append(
                {
                    "domain": v["domain"],
                    "ip_address": v["ip_address"],
                    "asset_count": v["assets"],
                    "open_port_count": len(v["open_ports"]),
                    "vulnerability_count": v["vulnerability_count"],
                }
            )
        return result

    if view == "service":
        services = []
        for a in assets:
            if a.port:
                services.append(
                    {
                        "domain": a.domain,
                        "ip_address": a.ip_address,
                        "port": a.port,
                        "protocol": a.protocol,
                        "product": a.product,
                        "asset_id": a.id,
                        "task_id": a.task_id,
                    }
                )
        return services

    if view == "url":
        urls = []
        for a in assets:
            if a.url:
                urls.append(
                    {
                        "url": a.url,
                        "domain": a.domain,
                        "ip_address": a.ip_address,
                        "port": a.port,
                        "asset_id": a.id,
                        "task_id": a.task_id,
                    }
                )
        return urls

    raise HTTPException(status_code=400, detail="view must be one of host/service/url")


@router.get("/{asset_id}", response_model=AssetInDB)
def get_asset(
    *,
    db: Session = Depends(get_db),
    asset_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取特定資產的詳細信息
    """
    asset = (
        db.query(models.Asset)
        .filter(models.Asset.id == asset_id, models.Asset.tenant_id == tenant_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="資產不存在",
        )

    return asset


@router.get("/stats/summary")
def get_asset_stats(
    *,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取資產統計信息
    """
    total = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id).count()
    
    stats_by_type = {}
    for asset_type in models.AssetType:
        count = (
            db.query(models.Asset)
            .filter(models.Asset.tenant_id == tenant_id, models.Asset.type == asset_type)
            .count()
        )
        stats_by_type[asset_type.value] = count

    return {
        "total": total,
        "by_type": stats_by_type,
    }


@router.post("/enhance", response_model=AssetEnhanceResponse)
def enhance_assets(
    *,
    db: Session = Depends(get_db),
    request: AssetEnhanceRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    Batch enhance assets through the asset processing pipeline.

    This endpoint processes assets through CDN detection, protocol inference,
    fingerprint enhancement, and optional deduplication.

    Args:
        request: Enhancement configuration including optional task_ids filter
                and pipeline feature toggles.

    Returns:
        AssetEnhanceResponse with processing statistics and detailed report.
    """
    # Build base query for tenant's assets
    query = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id)

    # Filter by task_ids if provided
    if request.task_ids:
        query = query.filter(models.Asset.task_id.in_(request.task_ids))

    # Fetch assets from database
    assets = query.all()

    if not assets:
        return AssetEnhanceResponse(
            processed=0,
            enhanced=0,
            report={
                "message": "No assets found for enhancement",
                "input_count": 0,
                "output_count": 0,
                "cdn_detected": 0,
                "protocol_enhanced": 0,
                "fingerprint_enhanced": 0,
                "dedup_removed": 0,
                "errors": [],
            },
        )

    # Convert SQLAlchemy models to dictionaries for pipeline processing
    asset_dicts = []
    asset_id_map = {}  # Map to track original asset IDs

    for asset in assets:
        asset_dict = {
            "id": asset.id,
            "type": asset.type.value if asset.type else None,
            "value": asset.value,
            "domain": asset.domain,
            "ip_address": asset.ip_address,
            "port": asset.port,
            "protocol": asset.protocol,
            "product": asset.product,
            "url": asset.url,
            "data": asset.data or {},
            "tags": asset.tags or [],
            "sources": asset.sources or [],
            "is_cdn": asset.is_cdn,
            "cdn_provider": asset.cdn_provider,
            "original_domain": asset.original_domain,
            "discovered_at": asset.discovered_at.isoformat() if asset.discovered_at else None,
            "last_seen": asset.last_seen.isoformat() if asset.last_seen else None,
            "tenant_id": asset.tenant_id,
            "task_id": asset.task_id,
        }
        asset_dicts.append(asset_dict)
        asset_id_map[asset.id] = asset

    # Process assets through the pipeline
    pipeline = AssetPipeline()

    # Configure pipeline based on request flags
    # Note: The pipeline processes all steps but we can control dedup
    enhanced_assets = pipeline.process_batch(asset_dicts, enable_dedup=request.enable_dedup)

    # Update database with enhanced data
    enhanced_count = 0
    for enhanced in enhanced_assets:
        asset_id = enhanced.get("id")
        if asset_id and asset_id in asset_id_map:
            asset = asset_id_map[asset_id]

            # Track if any enhancements were made
            was_enhanced = False

            # Update CDN fields
            if enhanced.get("is_cdn") != asset.is_cdn:
                asset.is_cdn = enhanced.get("is_cdn", False)
                was_enhanced = True
            if enhanced.get("cdn_provider") != asset.cdn_provider:
                asset.cdn_provider = enhanced.get("cdn_provider")
                was_enhanced = True
            if enhanced.get("original_domain") != asset.original_domain:
                asset.original_domain = enhanced.get("original_domain")
                was_enhanced = True

            # Update protocol
            if enhanced.get("protocol") != asset.protocol:
                asset.protocol = enhanced.get("protocol")
                was_enhanced = True

            # Update product
            if enhanced.get("product") != asset.product:
                asset.product = enhanced.get("product")
                was_enhanced = True

            # Update data with technologies if present
            technologies = enhanced.get("technologies", [])
            if technologies:
                if asset.data is None:
                    asset.data = {}
                asset.data["technologies"] = technologies
                was_enhanced = True

            if was_enhanced:
                enhanced_count += 1

    # Commit all changes
    db.commit()

    # Get pipeline stats
    stats = pipeline.get_last_stats()

    # Build response report
    report = {
        "message": "Asset enhancement completed successfully",
        "input_count": stats.get("input_count", 0),
        "output_count": stats.get("output_count", 0),
        "cdn_detected": stats.get("cdn_detected", 0),
        "protocol_enhanced": stats.get("protocol_enhanced", 0),
        "fingerprint_enhanced": stats.get("fingerprint_enhanced", 0),
        "dedup_removed": stats.get("dedup_removed", 0),
        "errors": stats.get("errors", []),
    }

    return AssetEnhanceResponse(
        processed=stats.get("input_count", 0),
        enhanced=enhanced_count,
        report=report,
    )


@router.get("/stats/quality")
def get_asset_quality_stats(
    *,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    print(f"[Assets Quality Debug] Request: tenant_id={tenant_id}")
    """
    Get asset quality statistics.

    Returns coverage metrics for:
    - Total asset count
    - Protocol coverage (count and rate)
    - Fingerprint/technology coverage (count and rate)
    - CDN detection (count and rate)
    - Multi-source assets (aggregated from multiple sources)

    Returns:
        Dictionary containing quality statistics.
    """
    # Base query for tenant's assets
    base_query = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id)

    # Total count
    total = base_query.count()

    if total == 0:
        return {
            "total": 0,
            "protocol": {"count": 0, "rate": 0.0},
            "fingerprint": {"count": 0, "rate": 0.0},
            "cdn": {"count": 0, "rate": 0.0},
            "multi_source": {"count": 0, "rate": 0.0},
        }

    # Protocol coverage (assets with protocol field set)
    protocol_count = base_query.filter(models.Asset.protocol.isnot(None)).count()
    protocol_rate = round(protocol_count / total * 100, 2)

    # Fingerprint coverage (assets with product field or technologies in data)
    fingerprint_query = base_query.filter(
        or_(
            models.Asset.product.isnot(None),
            models.Asset.data.contains({"technologies": []}),
        )
    )
    fingerprint_count = fingerprint_query.count()
    fingerprint_rate = round(fingerprint_count / total * 100, 2)

    # CDN detection count
    cdn_count = base_query.filter(models.Asset.is_cdn == True).count()
    cdn_rate = round(cdn_count / total * 100, 2)

    # Multi-source assets (assets with more than one source)
    # We need to check the sources JSON field length
    from sqlalchemy import func

    multi_source_count = (
        base_query.filter(
            func.json_array_length(models.Asset.sources) > 1
        ).count()
    )
    multi_source_rate = round(multi_source_count / total * 100, 2)

    return {
        "total": total,
        "protocol": {
            "count": protocol_count,
            "rate": protocol_rate,
        },
        "fingerprint": {
            "count": fingerprint_count,
            "rate": fingerprint_rate,
        },
        "cdn": {
            "count": cdn_count,
            "rate": cdn_rate,
        },
        "multi_source": {
            "count": multi_source_count,
            "rate": multi_source_rate,
        },
    }
    print(f"[Assets Quality Debug] Response: total={total}")

