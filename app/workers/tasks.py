from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from celery import group
from celery.result import GroupResult, AsyncResult
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.db.models import (
    Asset,
    AssetType,
    CredentialProvider,
    Domain,
    DomainIP,
    FofaAsset,
    HunterAsset,
    SubfinderAsset,
    ScanPlan,
    ScanPlanTool,
    Task,
    TaskLog,
    TaskStatus,
    Vulnerability,
    VulnerabilitySeverity,
)
from app.services.domain_aggregation import DomainAggregationService
from app.db.session import SessionLocal
from app.services.repositories import ApiCredentialRepository
from app.utils.command_builder import build_command, get_tool_command_from_config
from app.workers.celery_app import celery_app
from tools.fofa_provider import FofaProvider
from tools.hunter_provider import HunterProvider
from tools.utils import get_tool_command


def _db() -> Session:
    return SessionLocal()


def extract_root_domain(domain: str) -> str:
    """提取根域名，如 api.example.com -> example.com"""
    parts = domain.lower().strip().split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return domain


def _update_task(task_id: int, **fields: Any) -> None:
    db = _db()
    try:
        obj = db.query(Task).filter(Task.id == task_id).one_or_none()
        if not obj:
            return

        for k, v in fields.items():
            # 關鍵修正：強制把 error 欄位轉成 JSON 字串，避免 dict-like 例外造成 join 錯誤
            if k == 'error' and not isinstance(v, str):
                try:
                    v = json.dumps(v, ensure_ascii=False, default=str)
                except TypeError:
                    v = str(v)
            setattr(obj, k, v)

        obj.updated_at = datetime.utcnow()
        db.add(obj)
        db.commit()
    finally:
        db.close()


def _log_task(task_id: int, phase: str, message: str, level: str = "info") -> None:
    db = _db()
    try:
        log = TaskLog(task_id=task_id, phase=phase, level=level, message=message)
        db.add(log)
        db.commit()
    finally:
        db.close()


def _normalize_endpoint_from_link(link: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
    if not link:
        return None, None, None, None
    parsed = urlsplit(link)
    domain = parsed.hostname
    port = parsed.port
    protocol = parsed.scheme or None
    return domain, None, port, protocol


def _extract_domain_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlsplit(url)
        return parsed.hostname
    except Exception:
        return None


def _apply_fingerprints(db: Session, asset: Asset, url: str, title: Optional[str] = None) -> None:
    rules = db.query(models.FingerprintRule).filter(models.FingerprintRule.enabled.is_(True)).all()
    if not rules:
        return

    hits = asset.data.get("fingerprints", []) if asset.data else []
    url_str = url or asset.url or asset.value
    title_str = title or ""

    for rule in rules:
        try:
            regex = re.compile(rule.pattern, re.IGNORECASE)
        except re.error:
            continue

        target_ok = False
        if rule.target == "url":
            target_ok = bool(url_str and regex.search(url_str))
        elif rule.target == "title":
            target_ok = bool(title_str and regex.search(title_str))

        if target_ok:
            hits.append({"rule_id": rule.id, "name": rule.name, "target": rule.target, "pattern": rule.pattern})

    if hits != asset.data.get("fingerprints"):
        data = asset.data or {}
        data["fingerprints"] = hits
        asset.data = data
        db.add(asset)
        db.commit()
        db.refresh(asset)


def _upsert_source_asset(
    db: Session,
    *,
    model,
    tenant_id: int,
    task_id: Optional[int],
    asset_type: AssetType,
    value: str,
    domain: Optional[str] = None,
    ip_address: Optional[str] = None,
    port: Optional[int] = None,
    protocol: Optional[str] = None,
    product: Optional[str] = None,
    url: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    from sqlalchemy.exc import IntegrityError

    obj = (
        db.query(model)
        .filter(
            model.tenant_id == tenant_id,
            model.task_id == task_id,
            model.type == asset_type,
            model.value == value,
        )
        .one_or_none()
    )

    if obj is None:
        obj = model(
            tenant_id=tenant_id,
            task_id=task_id,
            type=asset_type,
            value=value,
            domain=domain,
            ip_address=ip_address,
            port=port,
            protocol=protocol,
            product=product,
            url=url,
            data=data or {},
            tags=tags or [],
        )
        db.add(obj)
        try:
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            obj = (
                db.query(model)
                .filter(
                    model.tenant_id == tenant_id,
                    model.task_id == task_id,
                    model.type == asset_type,
                    model.value == value,
                )
                .one_or_none()
            )
            if obj is None:
                raise

    obj.last_seen = datetime.utcnow()
    obj.domain = obj.domain or domain
    obj.ip_address = obj.ip_address or ip_address
    obj.port = obj.port or port
    obj.protocol = obj.protocol or protocol
    obj.product = obj.product or product
    obj.url = obj.url or url

    if data:
        merged = obj.data or {}
        merged.update(data)
        obj.data = merged

    if tags:
        existing_tags = set(obj.tags or [])
        existing_tags.update(tags)
        obj.tags = list(existing_tags)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _aggregate_subfinder_assets(db: Session, *, task: Task) -> int:
    """
    从 SubfinderAsset 表聚合数据到 Asset 表
    处理 Subfinder 发现的所有 URL 和域名
    """
    tenant_id = task.tenant_id
    task_id = task.id

    subfinder_assets = db.query(SubfinderAsset).filter(
        SubfinderAsset.tenant_id == tenant_id,
        SubfinderAsset.task_id == task_id
    ).all()

    aggregated_count = 0
    processed_urls = set()

    for sa in subfinder_assets:
        url = sa.url
        if not url or url in processed_urls:
            continue

        processed_urls.add(url)

        # 聚合到 Asset 表
        try:
            _upsert_aggregated_asset(
                db,
                tenant_id=tenant_id,
                task_id=task_id,
                url=url,
                domain=sa.domain,
                ip_address=None,
                port=None,
                product=None,
                protocol=None,
                source="subfinder",
                data={"subfinder_data": sa.data or {}},
                tags=["subfinder"],
            )
            aggregated_count += 1
        except Exception as e:
            _log_task(task_id, "subfinder", f"聚合 SubfinderAsset 失败 {url}: {str(e)}", level="warning")

    return aggregated_count


def _upsert_aggregated_asset(
    db: Session,
    *,
    tenant_id: int,
    task_id: Optional[int],
    url: Optional[str],
    domain: Optional[str],
    ip_address: Optional[str],
    port: Optional[int],
    product: Optional[str],
    protocol: Optional[str],
    source: str,
    data: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Asset:
    """
    智能聚合资产到 Asset 表
    支持多来源数据合并，保留所有来源的信息
    """
    from sqlalchemy.exc import IntegrityError

    norm_domain = (domain or "").strip().lower() or None
    norm_url = (url or "").strip() or None
    current_time = datetime.utcnow()

    query = db.query(Asset).filter(Asset.tenant_id == tenant_id)
    if norm_domain:
        query = query.filter(Asset.domain == norm_domain, Asset.ip_address == ip_address, Asset.port == port)
    else:
        query = query.filter(Asset.url == norm_url, Asset.ip_address == ip_address, Asset.port == port)

    obj = query.first()

    if obj is None:
        # 新建资产
        obj = Asset(
            tenant_id=tenant_id,
            task_id=task_id,
            url=norm_url,
            domain=norm_domain,
            ip_address=ip_address,
            port=port,
            product=product,
            protocol=protocol,
            type=AssetType.ENDPOINT,
            value=norm_url or norm_domain or (ip_address or ""),
            sources=[source],
            data=data or {},
            tags=tags or [],
            # 初始化 discovered_by
            discovered_by={
                source: {
                    "first_seen": current_time.isoformat(),
                    "count": 1
                }
            },
            # 初始化 source_urls
            source_urls={
                source: [norm_url] if norm_url else []
            },
        )
        db.add(obj)
        try:
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            obj = query.first()
            if obj is None:
                raise
    else:
        # 资产已存在，智能合并
        obj.last_seen = current_time

        # 更新 sources 列表
        existing_sources = set(obj.sources or [])
        existing_sources.add(source)
        obj.sources = list(existing_sources)

        # 更新 discovered_by（记录每个来源的贡献）
        discovered_by = obj.discovered_by or {}
        if source not in discovered_by:
            discovered_by[source] = {
                "first_seen": current_time.isoformat(),
                "count": 1
            }
        else:
            discovered_by[source]["count"] = (discovered_by[source].get("count", 0) + 1)
        obj.discovered_by = discovered_by

        # 更新 source_urls（合并所有来源发现的 URL）
        source_urls = obj.source_urls or {}
        if source not in source_urls:
            source_urls[source] = []
        if norm_url and norm_url not in source_urls[source]:
            source_urls[source].append(norm_url)
        obj.source_urls = source_urls

        # 智能合并 IP 地址（记录所有来源的 IP）
        # 注意：这里简化处理，实际可能需要更复杂的 IP 合并逻辑
        if ip_address and not obj.ip_address:
            obj.ip_address = ip_address

        # 智能合并产品信息（记录所有来源的产品）
        if product:
            # 将产品信息保存到 data 中，保留多来源
            if not obj.data:
                obj.data = {}
            product_sources = obj.data.get("product_sources", {})
            product_sources[source] = product
            obj.data["product_sources"] = product_sources

            # 选择一个产品作为主显示（优先使用有端口的来源）
            if not obj.product or (port and not obj.port):
                obj.product = product

        # 合并 protocol（优先使用有协议的）
        if protocol and not obj.protocol:
            obj.protocol = protocol

        # 合并 tags
        if tags:
            existing_tags = set(obj.tags or [])
            existing_tags.update(tags)
            obj.tags = list(existing_tags)

        # 合并 data 字段
        if data:
            merged = obj.data or {}
            merged.update(data)
            obj.data = merged

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _aggregate_assets_from_sources(db: Session, *, task: Task) -> int:
    """
    聚合來源資產表（FofaAsset/HunterAsset）到聚合表（Asset）
    
    返回：
    - 處理的來源資產行數（用於日誌）
    
    注意：
    - 一個搜索記錄可能寫入多條來源資產（IP + ENDPOINT），所以處理的行數可能大於搜索記錄數
    - 聚合時會自動去重，所以聚合後的唯一資產數可能小於處理的行數
    """
    tenant_id = task.tenant_id
    task_id = task.id

    fofa_rows = db.query(FofaAsset).filter(FofaAsset.tenant_id == tenant_id, FofaAsset.task_id == task_id).all()
    hunter_rows = db.query(HunterAsset).filter(HunterAsset.tenant_id == tenant_id, HunterAsset.task_id == task_id).all()

    # 記錄聚合前的唯一資產數
    before_count = db.query(Asset).filter(
        Asset.tenant_id == tenant_id,
        Asset.task_id == task_id
    ).count()

    processed_rows = 0

    for row in fofa_rows:
        if not (row.url or row.domain or row.ip_address):
            continue
        _upsert_aggregated_asset(
            db,
            tenant_id=tenant_id,
            task_id=task_id,
            url=row.url,
            domain=row.domain,
            ip_address=row.ip_address,
            port=row.port,
            product=row.product,
            protocol=row.protocol,
            source="fofa",
            data=row.data or {},
            tags=["fofa"],
        )
        processed_rows += 1

    for row in hunter_rows:
        if not (row.url or row.domain or row.ip_address):
            continue
        _upsert_aggregated_asset(
            db,
            tenant_id=tenant_id,
            task_id=task_id,
            url=row.url,
            domain=row.domain,
            ip_address=row.ip_address,
            port=row.port,
            product=row.product,
            protocol=row.protocol,
            source="hunter",
            data=row.data or {},
            tags=["hunter"],
        )
        processed_rows += 1

    # 記錄聚合後的唯一資產數
    after_count = db.query(Asset).filter(
        Asset.tenant_id == tenant_id,
        Asset.task_id == task_id
    ).count()
    
    # 返回新增/更新的唯一資產數（更準確的指標）
    unique_assets_affected = after_count - before_count
    
    return unique_assets_affected


def _deduplicate_assets(db: Session, task_id: int, tenant_id: int) -> int:
    assets = db.query(Asset).filter(Asset.tenant_id == tenant_id, Asset.task_id == task_id).all()

    seen = {}
    duplicates = []

    for a in assets:
        if a.domain:
            key = ("d", (a.domain or "").strip().lower(), (a.ip_address or "").strip(), a.port or 0)
        else:
            key = ("u", (a.url or "").strip(), (a.ip_address or "").strip(), a.port or 0)

        if key in seen:
            duplicates.append(a)
        else:
            seen[key] = a

    deleted = 0
    for d in duplicates:
        db.delete(d)
        deleted += 1

    if deleted:
        db.commit()

    return deleted


def _ensure_domains_in_assets(db: Session, *, task: Task, domains: List[str], source: str) -> int:
    tenant_id = task.tenant_id
    task_id = task.id

    added = 0
    for d in domains:
        dom = (d or "").strip().lower()
        if not dom:
            continue

        exists = (
            db.query(Asset.id)
            .filter(Asset.tenant_id == tenant_id, Asset.domain == dom)
            .first()
        )
        if exists:
            continue

        _upsert_aggregated_asset(
            db,
            tenant_id=tenant_id,
            task_id=task_id,
            url=None,
            domain=dom,
            ip_address=None,
            port=None,
            product=None,
            protocol=None,
            source=source,
            data={"source": source, "status": "pending_scan", "discovered_by_subfinder": True},
            tags=[source, "pending_scan"],
        )
        added += 1

    return added


def _get_domains_for_second_round(db: Session, *, tenant_id: int, task_id: int, seed_domains: List[str]) -> List[str]:
    seed = {(d or "").strip().lower() for d in seed_domains if d and d.strip()}
    if not seed:
        return []

    # 新域名判定：與 assets 聚合表比對。只要 assets 已存在該 domain，就不算新。
    # 這裡我們只返回「目前 assets 里還不存在的 domain」，由外部呼叫者負責寫入 assets。
    # 但為避免 race，仍保留外部寫入時的 upsert。

    candidates = list(seed)
    existing = (
        db.query(Asset.domain)
        .filter(Asset.tenant_id == tenant_id, Asset.domain.in_(candidates))
        .all()
    )
    existing_set = {(r[0] or "").strip().lower() for r in existing if r and r[0]}

    return [d for d in candidates if d not in existing_set]


@celery_app.task(name="app.workers.tasks.run_fofa_pull")
def run_fofa_pull(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # 檢查任務是否已被取消
        if task.status == TaskStatus.CANCELLED:
            _log_task(task_id, "fofa", "任務已被取消，停止執行", level="info")
            return {"error": "Task cancelled", "status": "cancelled"}

        tenant_id = task.tenant_id
        fofa_query = payload.get("fofa_query")
        if not fofa_query:
            return {"error": "fofa_query is required"}

        _log_task(task_id, "fofa", f"開始 FOFA 拉取: query={fofa_query}")

        repo = ApiCredentialRepository(db)
        credential = repo.get_active(tenant_id, CredentialProvider.FOFA)
        if not credential:
            _update_task(task_id, status=TaskStatus.FAILED, error="未找到 FOFA 憑證，請先在憑證管理中配置")
            return {"error": "FOFA credential not found"}

        provider = FofaProvider(email=credential.api_email or "", api_key=credential.api_key)

        fields = payload.get("fields", ["ip", "port", "link", "product"])
        limit = payload.get("limit", 1000)
        delay = payload.get("delay", 2.0)

        search_records = []
        try:
            search_records = provider.search(query=fofa_query, fields=fields, limit=limit, delay=delay)
        except Exception as e:
            error_msg = str(e)
            if "没有权限搜索product字段" in error_msg or "820001" in error_msg:
                _log_task(task_id, "fofa", f"FOFA API 不支持 product 字段，重新查询不包含 product", level="warning")
                fields = [f for f in fields if f != "product"]
                search_records = provider.search(query=fofa_query, fields=fields, limit=limit, delay=delay)
            else:
                raise

        inserted = []
        for r in search_records:
            record_data = {
                "ip": r.ip or "",
                "port": r.port or 0,
                "link": r.link or "",
                "product": r.product or "",
                "source": "fofa",
            }

            if r.ip:
                _upsert_source_asset(
                    db,
                    model=FofaAsset,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    asset_type=AssetType.IP,
                    value=r.ip,
                    ip_address=r.ip,
                    port=r.port or 0,
                    product=r.product or "",
                    url=r.link or None,
                    data={"fofa_data": record_data},
                    tags=["fofa"],
                )

            if r.link:
                domain, ip_from_link, port_from_link, protocol_from_link = _normalize_endpoint_from_link(r.link)
                _upsert_source_asset(
                    db,
                    model=FofaAsset,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    asset_type=AssetType.ENDPOINT,
                    value=r.link,
                    domain=domain,
                    ip_address=ip_from_link or r.ip,
                    port=port_from_link or (r.port or 0),
                    protocol=protocol_from_link,
                    product=r.product or "",
                    url=r.link,
                    data={"fofa_data": record_data},
                    tags=["fofa"],
                )

            inserted.append(record_data)

        _log_task(task_id, "fofa", f"FOFA 完成: {len(inserted)}")
        return {"search_records": inserted, "inserted_count": len(inserted)}

    except Exception as e:
        # 網絡錯誤（DNS 解析失敗、連接超時等）不應導致整個任務失敗
        # 只記錄錯誤日誌，返回錯誤信息，讓聚合階段處理
        error_msg = str(e)
        _log_task(task_id, "fofa", f"FOFA 失敗: {error_msg}", level="error")
        # 不更新任務狀態為 FAILED，讓聚合階段根據整體情況決定
        return {"error": error_msg, "inserted_count": 0}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_hunter_pull")
def run_hunter_pull(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # 檢查任務是否已被取消
        if task.status == TaskStatus.CANCELLED:
            _log_task(task_id, "hunter", "任務已被取消，停止執行", level="info")
            return {"error": "Task cancelled", "status": "cancelled"}

        tenant_id = task.tenant_id
        hunter_query = payload.get("hunter_query")
        if not hunter_query:
            return {"error": "hunter_query is required"}

        _log_task(task_id, "hunter", f"開始 Hunter 拉取: query={hunter_query}")

        repo = ApiCredentialRepository(db)
        credential = repo.get_active(tenant_id, CredentialProvider.HUNTER)
        if not credential:
            _update_task(task_id, status=TaskStatus.FAILED, error="未找到 Hunter 憑證")
            return {"error": "Hunter credential not found"}

        provider = HunterProvider(api_key=credential.api_key)
        limit = payload.get("limit", 100)
        delay = payload.get("delay", 2.0)
        import time
        if delay > 0:
            time.sleep(delay)
        search_records = provider.search(query=hunter_query, limit=limit)

        _log_task(task_id, "hunter", f"Hunter API 返回记录数: {len(search_records)}", level="info")
        if not search_records:
            _log_task(task_id, "hunter", f"Hunter 查询无结果: query={hunter_query}", level="warning")

        inserted = []
        for r in search_records:
            record_data = {
                "ip": r.ip or "",
                "port": r.port or 0,
                "link": r.link or "",
                "product": r.product or "",
                "source": "hunter",
            }

            if r.ip:
                _upsert_source_asset(
                    db,
                    model=HunterAsset,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    asset_type=AssetType.IP,
                    value=r.ip,
                    ip_address=r.ip,
                    port=r.port or 0,
                    product=r.product or "",
                    url=r.link or None,
                    data={"hunter_data": record_data},
                    tags=["hunter"],
                )

            if r.link:
                domain, ip_from_link, port_from_link, protocol_from_link = _normalize_endpoint_from_link(r.link)
                _upsert_source_asset(
                    db,
                    model=HunterAsset,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    asset_type=AssetType.ENDPOINT,
                    value=r.link,
                    domain=domain,
                    ip_address=ip_from_link or r.ip,
                    port=port_from_link or (r.port or 0),
                    protocol=protocol_from_link,
                    product=r.product or "",
                    url=r.link,
                    data={"hunter_data": record_data},
                    tags=["hunter"],
                )

            inserted.append(record_data)

        _log_task(task_id, "hunter", f"Hunter 完成: {len(inserted)}")
        return {"search_records": inserted, "inserted_count": len(inserted)}

    except Exception as e:
        # 網絡錯誤（DNS 解析失敗、連接超時等）不應導致整個任務失敗
        # 只記錄錯誤日誌，返回錯誤信息，讓聚合階段處理
        error_msg = str(e)
        _log_task(task_id, "hunter", f"Hunter 失敗: {error_msg}", level="error")
        # 不更新任務狀態為 FAILED，讓聚合階段根據整體情況決定
        return {"error": error_msg, "inserted_count": 0}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_subfinder")
def run_subfinder(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """subfinder：輸入 domain，輸出 url list；同時回傳解析出的 domains。"""
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        # 檢查任務是否已被取消
        if task.status == TaskStatus.CANCELLED:
            _log_task(task_id, "subfinder", "任務已被取消，停止執行", level="info")
            return {"error": "Task cancelled", "status": "cancelled"}

        tenant_id = task.tenant_id
        root_domains = payload.get("root_domains", [])
        _log_task(task_id, "subfinder", f"開始 subfinder，root_domains={root_domains}")

        tool = db.query(models.Tool).filter(models.Tool.name == "subfinder", models.Tool.tenant_id == tenant_id).first()
        plan_cfg = (payload.get("plan_tool_configs") or {}).get("subfinder", {})

        default_template = "subfinder -d {domain} -silent"
        command_template = get_tool_command_from_config(
            "subfinder",
            tool_config={"command_template": tool.command_template} if tool else None,
            plan_tool_config=plan_cfg,
            default_template=default_template,
        )

        tool_path = tool.file_path if tool else None
        tool_base_cmd = get_tool_command("subfinder", tool_path)

        all_urls: List[str] = []
        url_to_domain: Dict[str, str] = {}

        for root_domain in root_domains:
            variables = {"domain": root_domain}
            cmd_parts = build_command(command_template, variables, "subfinder")
            if cmd_parts and cmd_parts[0] == "subfinder":
                cmd = tool_base_cmd + cmd_parts[1:]
            else:
                cmd = cmd_parts

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 30)
            if proc.returncode != 0:
                _log_task(task_id, "subfinder", f"subfinder error for {root_domain}: {proc.stderr}", level="error")
                continue

            # subfinder 輸出通常是 host，每行一個；你說輸出是一列 url，這裡兩者都兼容：
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                all_urls.append(line)
                dom = _extract_domain_from_url(line) or line
                if dom:
                    url_to_domain[line] = dom

        # 去重并保存到 SubfinderAsset 表
        from sqlalchemy.exc import IntegrityError
        inserted_count = 0
        for url in set(all_urls):
            domain = url_to_domain.get(url, _extract_domain_from_url(url))
            if not domain:
                continue

            # 判断 URL 类型
            asset_type = AssetType.ENDPOINT
            if url.startswith("http://") or url.startswith("https://"):
                asset_type = AssetType.URL
            elif "." in url:
                asset_type = AssetType.SUBDOMAIN

            # 查找对应的 root_domain
            found_root_domain = None
            for rd in root_domains:
                if domain == rd or domain.endswith(f".{rd}"):
                    found_root_domain = rd
                    break

            try:
                subfinder_asset = SubfinderAsset(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    type=asset_type,
                    value=url,
                    url=url,
                    domain=domain,
                    root_domain=found_root_domain,
                    discovered_urls=[url],
                    data={"subfinder_raw": url},
                    tags=["subfinder"],
                )
                db.add(subfinder_asset)
                db.commit()
                inserted_count += 1
            except IntegrityError:
                db.rollback()

        # 提取唯一的域名列表
        domains = sorted({d.strip().lower() for d in url_to_domain.values() if d and d.strip()})

        return {
            "_kind": "subfinder",  # 添加 _kind 字段，用于聚合阶段识别
            "urls": list(set(all_urls)),  # subfinder 工具实际检索到的所有数据（去重）
            "domains": domains,  # 去重后的域名列表
            "inserted_count": inserted_count  # 保存到 SubfinderAsset 表的记录数
        }

    except Exception as e:
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "subfinder", f"subfinder 失敗: {str(e)}", level="error")
        return {"error": str(e)}
    finally:
        db.close()



@celery_app.task(name="app.workers.tasks.run_nmap")
def run_nmap(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """nmap：預設從聚合表 assets 讀取 ip 目標，也可 payload.ips 手動指定。"""
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        tenant_id = task.tenant_id
        plan_cfg = (payload.get("plan_tool_configs") or {}).get("nmap", {})

        ips = payload.get("ips") or []
        if not ips:
            ips = [r[0] for r in db.query(Asset.ip_address).filter(Asset.tenant_id == tenant_id, Asset.task_id == task_id, Asset.ip_address.isnot(None)).all() if r and r[0]]

        ports = plan_cfg.get("ports") or payload.get("ports", "1-1000")
        _log_task(task_id, "port_scan", f"開始 nmap，ips={len(ips)}, ports={ports}")

        if not ips:
            return {"error": "No IPs provided", "inserted_count": 0}

        tool = db.query(models.Tool).filter(models.Tool.name == "nmap", models.Tool.tenant_id == tenant_id).first()
        default_template = "nmap -sV -p {ports} -oX - {targets}"
        tool_config = {"command_template": tool.command_template} if tool and tool.command_template else None
        command_template = get_tool_command_from_config("nmap", tool_config=tool_config, plan_tool_config=plan_cfg, default_template=default_template)

        tool_path = tool.file_path if tool else None
        tool_base_cmd = get_tool_command("nmap", tool_path)

        variables = {"ports": str(ports), "targets": " ".join(ips)}
        cmd_parts = build_command(command_template, variables, "nmap")
        cmd = tool_base_cmd + cmd_parts[1:] if cmd_parts and cmd_parts[0] == "nmap" else cmd_parts

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 120)
        if proc.returncode != 0:
            _log_task(task_id, "port_scan", f"nmap 失敗: {proc.stderr}", level="error")
            return {"error": proc.stderr, "inserted_count": 0}

        inserted_count = 0
        try:
            root = ET.fromstring(proc.stdout)
            for host in root.findall("host"):
                address_elem = host.find("address")
                if address_elem is None:
                    continue
                ip = address_elem.get("addr")
                if not ip:
                    continue

                for port_el in host.findall(".//port"):
                    port_id = port_el.get("portid")
                    protocol = port_el.get("protocol", "tcp")
                    state = port_el.find("state")
                    service = port_el.find("service")

                    if state is None or state.get("state") != "open":
                        continue

                    port_num = int(port_id) if port_id and port_id.isdigit() else None
                    product = None
                    if service is not None:
                        product = service.get("product") or service.get("name") or None

                    _upsert_aggregated_asset(
                        db,
                        tenant_id=tenant_id,
                        task_id=task_id,
                        url=None,
                        domain=None,
                        ip_address=ip,
                        port=port_num,
                        product=product,
                        protocol=protocol,
                        source="nmap",
                        data={"source": "nmap"},
                        tags=["nmap"],
                    )
                    inserted_count += 1

        except ET.ParseError as e:
            return {"error": f"Failed to parse nmap XML: {str(e)}", "inserted_count": 0}

        _log_task(task_id, "port_scan", f"nmap 完成: 插入 {inserted_count}")
        return {"xml": proc.stdout, "inserted_count": inserted_count}

    except Exception as e:
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "port_scan", f"nmap 失敗: {str(e)}", level="error")
        return {"error": str(e), "inserted_count": 0}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_httpx")
def run_httpx(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """httpx：預設從 assets 讀取 url/host 目標，也可 payload.targets 手動指定。"""
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        tenant_id = task.tenant_id
        plan_cfg = (payload.get("plan_tool_configs") or {}).get("httpx", {})

        targets = payload.get("targets") or []
        if not targets:
            # 優先 url，其次 domain，再其次 ip:port
            urls = [r[0] for r in db.query(Asset.url).filter(Asset.tenant_id == tenant_id, Asset.task_id == task_id, Asset.url.isnot(None)).all() if r and r[0]]
            domains = [r[0] for r in db.query(Asset.domain).filter(Asset.tenant_id == tenant_id, Asset.task_id == task_id, Asset.domain.isnot(None)).all() if r and r[0]]
            targets = list(dict.fromkeys(urls + domains))

        _log_task(task_id, "httpx", f"開始 httpx，targets={len(targets)}")
        if not targets:
            return {"alive": [], "inserted_count": 0}

        tool = db.query(models.Tool).filter(models.Tool.name == "httpx", models.Tool.tenant_id == tenant_id).first()
        default_template = "httpx -json -silent -no-color"
        tool_config = {"command_template": tool.command_template} if tool and tool.command_template else None
        command_template = get_tool_command_from_config("httpx", tool_config=tool_config, plan_tool_config=plan_cfg, default_template=default_template)

        tool_path = tool.file_path if tool else None
        tool_base_cmd = get_tool_command("httpx", tool_path)

        cmd_parts = build_command(command_template, {}, "httpx")
        cmd = tool_base_cmd + cmd_parts[1:] if cmd_parts and cmd_parts[0] == "httpx" else cmd_parts

        proc = subprocess.run(
            cmd,
            input="\n".join(targets) + "\n",
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )

        alive_targets = []
        inserted_count = 0

        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    result = json.loads(line)
                    url = result.get("url", result.get("input", ""))
                    if not url:
                        continue
                    alive_targets.append(url)

                    domain, ip_from_link, port_from_link, protocol_from_link = _normalize_endpoint_from_link(url)
                    asset = _upsert_aggregated_asset(
                        db,
                        tenant_id=tenant_id,
                        task_id=task_id,
                        url=url,
                        domain=domain,
                        ip_address=ip_from_link,
                        port=port_from_link,
                        product=None,
                        protocol=protocol_from_link,
                        source="httpx",
                        data={
                            "status_code": result.get("status_code"),
                            "title": result.get("title"),
                            "content_length": result.get("content_length"),
                            "source": "httpx",
                        },
                        tags=["httpx", "alive"],
                    )
                    inserted_count += 1
                    _apply_fingerprints(db=db, asset=asset, url=url, title=result.get("title"))

                except Exception:
                    continue

        _log_task(task_id, "httpx", f"httpx 完成: 存活 {inserted_count}")
        return {"alive": alive_targets, "inserted_count": inserted_count}

    except Exception as e:
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "httpx", f"httpx 失敗: {str(e)}", level="error")
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_nuclei")
def run_nuclei(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        tenant_id = task.tenant_id
        plan_cfg = (payload.get("plan_tool_configs") or {}).get("nuclei", {})

        targets = plan_cfg.get("targets") or payload.get("targets") or []
        if not targets:
            urls = [r[0] for r in db.query(Asset.url).filter(Asset.tenant_id == tenant_id, Asset.task_id == task_id, Asset.url.isnot(None)).all() if r and r[0]]
            targets = urls

        _log_task(task_id, "vuln_scan", f"開始 nuclei，targets={len(targets)}")

        if not targets:
            return {"findings": [], "inserted_count": 0}

        tool = db.query(models.Tool).filter(models.Tool.name == "nuclei", models.Tool.tenant_id == tenant_id).first()

        default_template = "nuclei -jsonl -silent"
        tool_config = {"command_template": tool.command_template} if tool and tool.command_template else None
        command_template = get_tool_command_from_config("nuclei", tool_config=tool_config, plan_tool_config=plan_cfg, default_template=default_template)

        tool_path = tool.file_path if tool else None
        tool_base_cmd = get_tool_command("nuclei", tool_path)

        variables = {"targets": " ".join(targets)}
        cmd_parts = build_command(command_template, variables, "nuclei")
        cmd = tool_base_cmd + cmd_parts[1:] if cmd_parts and cmd_parts[0] == "nuclei" else cmd_parts

        proc = subprocess.run(
            cmd,
            input="\n".join(targets) + "\n",
            capture_output=True,
            text=True,
            timeout=60 * 180,
        )

        if proc.returncode != 0:
            _log_task(task_id, "vuln_scan", f"nuclei 失敗: {proc.stderr}", level="error")
            return {"error": proc.stderr, "findings": []}

        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
            "info": VulnerabilitySeverity.INFO,
        }

        findings: List[Any] = []
        inserted_count = 0

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                finding = json.loads(line)
                findings.append(finding)

                target = finding.get("matched-at", finding.get("host", ""))
                title = finding.get("info", {}).get("name", finding.get("name", "Unknown Vulnerability"))
                description = finding.get("info", {}).get("description", "")
                severity_str = finding.get("info", {}).get("severity", "info").lower()
                severity_val = severity_map.get(severity_str, VulnerabilitySeverity.INFO)

                asset = None
                if target:
                    asset = (
                        db.query(Asset)
                        .filter(
                            Asset.tenant_id == tenant_id,
                            or_(
                                Asset.url == target,
                                Asset.value == target,
                                Asset.value.contains(target.split("://")[-1].split("/")[0]),
                            ),
                        )
                        .first()
                    )

                vulnerability = Vulnerability(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    asset_id=asset.id if asset else None,
                    title=title,
                    description=description,
                    severity=severity_val,
                    cve_id=(finding.get("info", {}) or {}).get("cve-id", [None])[0] if (finding.get("info", {}) or {}).get("cve-id") else None,
                    references=(finding.get("info", {}) or {}).get("reference", []),
                    raw_data=finding,
                    status="open",
                )
                db.add(vulnerability)
                inserted_count += 1

            except Exception:
                continue

        db.commit()
        _log_task(task_id, "vuln_scan", f"nuclei 完成: 新增漏洞 {inserted_count}")
        return {"findings": findings, "inserted_count": inserted_count}

    except Exception as e:
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "vuln_scan", f"nuclei 失敗: {str(e)}", level="error")
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.aggregate_pipeline_results")
def aggregate_pipeline_results(task_id: int, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        aggregated: Dict[str, Any] = {
            "fofa": None,
            "hunter": None,
            "subfinder": None,
            "nmap": None,
            "httpx": None,
            "nuclei": None,
        }

        total_vulnerabilities = 0
        errors = []

        for result in results:
            if not isinstance(result, dict):
                continue

            # 识别 subfinder 结果：通过 _kind 字段或 domains+urls 字段组合
            if result.get("_kind") == "subfinder" or ("domains" in result and "urls" in result):
                aggregated["subfinder"] = result
            elif "search_records" in result:
                # 透過 source 判斷
                first = (result.get("search_records") or [{}])[0]
                if isinstance(first, dict) and first.get("source") == "hunter":
                    # 如果有多个 Hunter 结果，合并它们（累加 inserted_count）
                    if aggregated["hunter"] is None:
                        aggregated["hunter"] = result
                    else:
                        # 合并多个 Hunter 结果
                        existing_count = aggregated["hunter"].get("inserted_count", 0)
                        new_count = result.get("inserted_count", 0)
                        aggregated["hunter"]["inserted_count"] = existing_count + new_count
                        # 合并 search_records
                        existing_records = aggregated["hunter"].get("search_records", [])
                        new_records = result.get("search_records", [])
                        aggregated["hunter"]["search_records"] = existing_records + new_records
                else:
                    # 如果有多个 FOFA 结果，合并它们（累加 inserted_count）
                    if aggregated["fofa"] is None:
                        aggregated["fofa"] = result
                    else:
                        # 合并多个 FOFA 结果
                        existing_count = aggregated["fofa"].get("inserted_count", 0)
                        new_count = result.get("inserted_count", 0)
                        aggregated["fofa"]["inserted_count"] = existing_count + new_count
                        # 合并 search_records
                        existing_records = aggregated["fofa"].get("search_records", [])
                        new_records = result.get("search_records", [])
                        aggregated["fofa"]["search_records"] = existing_records + new_records
            elif "xml" in result:
                aggregated["nmap"] = result
            elif "alive" in result:
                aggregated["httpx"] = result
            elif "findings" in result:
                aggregated["nuclei"] = result
                total_vulnerabilities += result.get("inserted_count", 0)

            if "error" in result:
                # 確保 error 是字符串，避免 join 時出現類型錯誤
                err_val = result["error"]
                if isinstance(err_val, str):
                    errors.append(err_val)
                elif isinstance(err_val, dict):
                    errors.append(json.dumps(err_val, ensure_ascii=False, default=str))
                else:
                    errors.append(str(err_val))

        # 聚合來源表 -> 聚合表 assets
        tenant_id = task.tenant_id
        _log_task(task_id, "aggregate", "開始聚合來源資產", level="info")
        try:
            affected = _aggregate_assets_from_sources(db, task=task)
            _log_task(task_id, "aggregate", f"聚合完成: 寫入/更新 {affected} 筆聚合資產", level="info")
        except Exception as e:
            _log_task(task_id, "aggregate", f"聚合失敗({type(e).__name__}): {str(e)}", level="error")

        # 只刪聚合表重複
        try:
            deduplicated_count = _deduplicate_assets(db, task_id, tenant_id)
            _log_task(task_id, "deduplicate", f"去重完成(僅聚合表): 刪除 {deduplicated_count} 個重複資產", level="info")
        except Exception as e:
            _log_task(task_id, "deduplicate", f"去重失敗({type(e).__name__}): {str(e)}", level="error")

        # 提取各工具的统计信息
        # 注意：需要统计所有轮次的结果，不仅仅是第一轮
        # 方法1：从 results 中统计（包含所有轮次的结果）
        fofa_records = 0
        hunter_records = 0
        
        # 统计所有 FOFA/Hunter 结果（包括第一轮和第二轮）
        # 注意：需要正确识别每个结果的 source，确保统计准确
        _log_task(task_id, "aggregate", f"開始統計，results 數量: {len(results)}", level="info")
        for idx, result in enumerate(results):
            if isinstance(result, dict) and "search_records" in result:
                search_records_list = result.get("search_records", [])
                if not search_records_list:
                    continue
                
                # 检查第一个记录（通常所有记录都有相同的 source）
                first_record = search_records_list[0] if isinstance(search_records_list, list) else {}
                if isinstance(first_record, dict):
                    source = first_record.get("source", "")
                    inserted = result.get("inserted_count", 0)
                    
                    _log_task(task_id, "aggregate", f"結果 {idx+1}: source={source}, inserted_count={inserted}", level="info")
                    
                    if source == "fofa":
                        fofa_records += inserted
                        _log_task(task_id, "aggregate", f"FOFA 統計: +{inserted}, 累計={fofa_records}", level="info")
                    elif source == "hunter":
                        hunter_records += inserted
                        _log_task(task_id, "aggregate", f"Hunter 統計: +{inserted}, 累計={hunter_records}", level="info")
                    else:
                        # 如果没有 source 字段，尝试从 aggregated 字典中判断
                        # 因为 aggregated 字典在构建时已经根据 source 分类了
                        if inserted > 0:
                            # 检查 aggregated 字典，看这个结果是否已经被分类
                            # 通过比较 inserted_count 和 search_records 来判断
                            if aggregated.get("fofa") and aggregated["fofa"].get("inserted_count") == inserted:
                                fofa_records += inserted
                                _log_task(task_id, "aggregate", f"FOFA 統計（從 aggregated）: +{inserted}, 累計={fofa_records}", level="info")
                            elif aggregated.get("hunter") and aggregated["hunter"].get("inserted_count") == inserted:
                                hunter_records += inserted
                                _log_task(task_id, "aggregate", f"Hunter 統計（從 aggregated）: +{inserted}, 累計={hunter_records}", level="info")
                            else:
                                # 如果无法确定，记录警告但不统计，避免错误
                                _log_task(task_id, "aggregate", f"警告：發現搜索結果但無法確定 source，inserted_count={inserted}，跳過統計", level="warning")
        
        _log_task(task_id, "aggregate", f"方法1統計完成: FOFA={fofa_records}, Hunter={hunter_records}", level="info")
        
        # 方法2：如果方法1没统计到，从 aggregated 中获取（作为备用）
        if fofa_records == 0 and aggregated.get("fofa"):
            fofa_records = aggregated.get("fofa", {}).get("inserted_count", 0)
        if hunter_records == 0 and aggregated.get("hunter"):
            hunter_records = aggregated.get("hunter", {}).get("inserted_count", 0)
        
        # 方法3：直接从数据库统计（最准确的方式）
        # 注意：inserted_count 是搜索记录数，但实际写入的来源资产表记录数可能更多
        # 因为一个搜索记录可能写入多条来源资产（IP + ENDPOINT）
        tenant_id = task.tenant_id
        task_id = task.id
        
        # 统计实际写入的来源资产表记录数
        fofa_count_from_db = db.query(FofaAsset).filter(
            FofaAsset.tenant_id == tenant_id,
            FofaAsset.task_id == task_id
        ).count()
        hunter_count_from_db = db.query(HunterAsset).filter(
            HunterAsset.tenant_id == tenant_id,
            HunterAsset.task_id == task_id
        ).count()
        
        # 注意：统计应该使用搜索记录数（inserted_count），而不是来源资产表的行数
        # 因为一个搜索记录可能写入多条来源资产（IP + ENDPOINT），所以来源资产表的行数会大于搜索记录数
        # 用户期望看到的是"检索到的数据数量"（搜索记录数），而不是"写入的来源资产行数"
        
        # 如果从 results 中没有统计到，尝试从 aggregated 中获取（可能只包含第一轮的结果）
        if fofa_records == 0:
            if aggregated.get("fofa"):
                fofa_records = aggregated.get("fofa", {}).get("inserted_count", 0)
            elif fofa_count_from_db > 0:
                # 如果 aggregated 中也没有，但数据库中有，说明可能有问题
                # 这种情况下，我们无法准确知道搜索记录数，只能记录警告
                _log_task(task_id, "aggregate", f"警告：FOFA 统计为 0，但数据库中有 {fofa_count_from_db} 条来源资产，可能存在统计逻辑问题", level="warning")
                # 不设置 fofa_records，保持为 0，让用户知道统计有问题
            
        if hunter_records == 0:
            if aggregated.get("hunter"):
                hunter_records = aggregated.get("hunter", {}).get("inserted_count", 0)
            elif hunter_count_from_db > 0:
                # 如果 aggregated 中也没有，但数据库中有，说明可能有问题
                _log_task(task_id, "aggregate", f"警告：Hunter 统计为 0，但数据库中有 {hunter_count_from_db} 条来源资产，可能存在统计逻辑问题", level="warning")
                # 不设置 hunter_records，保持为 0，让用户知道统计有问题
        
        # Subfinder 统计：
        # - subfinder_records: subfinder 工具实际检索到的数据条数（urls 的数量，可能有重复）
        # - subfinder_subdomains: 去重后的子域名数量（domains 的数量）
        subfinder_result = aggregated.get("subfinder", {})
        subfinder_urls_list = subfinder_result.get("urls", []) if subfinder_result else []
        subfinder_domains_list = subfinder_result.get("domains", []) if subfinder_result else []
        subfinder_records = len(subfinder_urls_list)  # subfinder 记录数（工具实际检索到的数据条数）
        subfinder_subdomains = len(subfinder_domains_list)  # 子域名数量（去重后的域名数量）
        
        nmap_ips = aggregated.get("nmap", {}).get("inserted_count", 0) if aggregated.get("nmap") else 0
        httpx_alive = aggregated.get("httpx", {}).get("inserted_count", 0) if aggregated.get("httpx") else 0
        nuclei_findings = aggregated.get("nuclei", {}).get("inserted_count", 0) if aggregated.get("nuclei") else 0
        
        output_data = {
            "results": aggregated,
            "summary": {
                # 查询该任务发现的资产：使用 last_seen 时间范围来判断
                # 如果资产的 last_seen 在任务开始时间之后，就认为是该任务发现的
                "total_assets_discovered": db.query(Asset).filter(
                    Asset.tenant_id == task.tenant_id,
                    Asset.last_seen >= (task.started_at or task.created_at)
                ).count(),
                "total_vulnerabilities_found": total_vulnerabilities,
                "fofa_records": fofa_records,
                "hunter_records": hunter_records,
                "subfinder_subdomains": subfinder_subdomains,
                "subfinder_records": subfinder_records,  # subfinder 记录数
                "nmap_ips": nmap_ips,
                "httpx_alive": httpx_alive,
                "nuclei_findings": nuclei_findings,
            },
            "errors": errors if errors else None,
        }

        if task.status == TaskStatus.RUNNING:
            _update_task(task_id, status=TaskStatus.COMPLETED, completed_at=datetime.utcnow(), progress=100, output_data=output_data)

        return output_data

    except Exception as e:
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        return {"error": str(e)}
    finally:
        db.close()
@celery_app.task(name="app.workers.tasks.run_pipeline")
def run_pipeline(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """B 模式：非同步 group + check_and_aggregate 聚合

    你的最終流程（已按你確認的規則落地）：
    1) 第一輪：按輸入（fofa_query / hunter_query / ips / root_domains）跑 FOFA/Hunter -> 分表落庫 -> 聚合到 assets
    2) 若輸入包含 root_domains（domain 類輸入）：
       - subfinder 擴展（輸出 URL/host 列表） -> 解析 domain
       - 與 assets 聚合表比對（你確認：是），取「新 domain」
       - 將新 domain 寫入 assets（只填 domain，其它欄位空，sources=subfinder）
       - 第二輪：對每個新 domain（你確認：A，逐個）跑 FOFA/Hunter -> 再聚合到 assets
    3) 後續工具（httpx/nmap/nuclei）為資料收集：預設從 assets 讀目標，也可手動輸入目標
    """
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # 檢查任務是否已被取消
        if task.status == TaskStatus.CANCELLED:
            _log_task(task_id, "pipeline", "任務已被取消，停止執行", level="info")
            return {"error": "Task cancelled", "status": "cancelled"}

        payload = payload or {}
        enable = payload.get("enable", {}) or {}
        root_domains = payload.get("root_domains") or []
        ips = payload.get("ips") or []

        _log_task(task_id, "pipeline", f"Pipeline 開始執行，task_id={task_id}", level="info")
        _update_task(task_id, status=TaskStatus.RUNNING, started_at=datetime.utcnow(), progress=1)

        # ----------------------------
        # 第一輪：FOFA/Hunter jobs
        # ----------------------------
        first_jobs = []

        # FOFA 任務：檢查 enable 配置，預設啟用
        if enable.get("fofa", True):
            if payload.get("fofa_query"):
                first_jobs.append(run_fofa_pull.s(task_id, payload))
            
            # 若未提供 query，且提供 root_domains/ips，則逐個生成 query（A）
            if not payload.get("fofa_query") and root_domains:
                for d in root_domains:
                    p = dict(payload)
                    p["fofa_query"] = f'domain="{d}"'
                    first_jobs.append(run_fofa_pull.s(task_id, p))
            
            if not payload.get("fofa_query") and ips:
                for ip in ips:
                    p = dict(payload)
                    p["fofa_query"] = f'ip="{ip}"'
                    first_jobs.append(run_fofa_pull.s(task_id, p))

        # Hunter 任務：檢查 enable 配置，預設啟用
        if enable.get("hunter", True):
            if payload.get("hunter_query"):
                first_jobs.append(run_hunter_pull.s(task_id, payload))
            
            # 若未提供 query，且提供 root_domains/ips，則逐個生成 query（A）
            if not payload.get("hunter_query") and root_domains:
                for d in root_domains:
                    p = dict(payload)
                    p["hunter_query"] = f'domain="{d}"'
                    first_jobs.append(run_hunter_pull.s(task_id, p))
            
            if not payload.get("hunter_query") and ips:
                for ip in ips:
                    p = dict(payload)
                    p["hunter_query"] = f'ip="{ip}"'
                    first_jobs.append(run_hunter_pull.s(task_id, p))

        if not first_jobs:
            _update_task(task_id, status=TaskStatus.FAILED, error="no fofa/hunter jobs")
            return {"error": "no fofa/hunter jobs"}

        # 如果啟用 subfinder，將其加入第一輪 jobs
        if root_domains and enable.get("subfinder", True):
            subfinder_payload = {"root_domains": root_domains, "plan_tool_configs": payload.get("plan_tool_configs") or {}}
            first_jobs.append(run_subfinder.s(task_id, subfinder_payload))

        # 記錄第一輪任務信息
        fofa_jobs = [job for job in first_jobs if 'run_fofa_pull' in str(job)]
        hunter_jobs = [job for job in first_jobs if 'run_hunter_pull' in str(job)]
        subfinder_jobs = [job for job in first_jobs if 'run_subfinder' in str(job)]
        fofa_count = len(fofa_jobs)
        hunter_count = len(hunter_jobs)
        subfinder_count = len(subfinder_jobs)
        _log_task(task_id, "pipeline", f"第一輪任務準備提交: FOFA={fofa_count}, Hunter={hunter_count}, Subfinder={subfinder_count}, 總計={len(first_jobs)}", level="info")

        # 使用 group().apply_async() 提交任務組
        # 注意：group 中的任務會根據 task_routes 自動路由到對應的隊列
        # 為了確保任務正確提交，我們分別提交每個任務並收集 ID
        first_child_ids = []
        try:
            # 方法1：使用 group().apply_async()（推薦方式）
            g1 = group(*first_jobs).apply_async()
            _log_task(task_id, "pipeline", "任務組已提交到 Celery (使用 group)", level="info")
            
            # 獲取第一輪子任務 ID：GroupResult.children 是標準 API
            first_child_ids = [c.id for c in g1.children] if g1.children else []
            
            # 如果 group 方式沒有獲取到 ID，嘗試直接提交每個任務
            if not first_child_ids or len(first_child_ids) != len(first_jobs):
                _log_task(task_id, "pipeline", f"警告：group 方式獲取的任務ID數量不匹配 (期望: {len(first_jobs)}, 實際: {len(first_child_ids)})，嘗試直接提交", level="warning")
                first_child_ids = []
                for job in first_jobs:
                    try:
                        result = job.apply_async()
                        first_child_ids.append(result.id)
                    except Exception as e:
                        _log_task(task_id, "pipeline", f"直接提交任務時出錯: {str(e)}", level="error")
        except Exception as e:
            _log_task(task_id, "pipeline", f"提交任務組時出錯: {str(e)}，嘗試直接提交每個任務", level="error")
            # 如果 group 方式失敗，嘗試直接提交每個任務
            first_child_ids = []
            for job in first_jobs:
                try:
                    result = job.apply_async()
                    first_child_ids.append(result.id)
                except Exception as e2:
                    _log_task(task_id, "pipeline", f"直接提交任務時出錯: {str(e2)}", level="error")
        
        if not first_child_ids:
            _log_task(task_id, "pipeline", "錯誤：無法提交任何任務", level="error")
            _update_task(task_id, status=TaskStatus.FAILED, error="無法提交任務到 Celery")
            return {"error": "Failed to submit tasks to Celery"}
        
        if not first_child_ids:
            _log_task(task_id, "pipeline", "錯誤：第一輪任務ID為空，任務可能未正確提交", level="error")
        else:
            _log_task(task_id, "pipeline", f"第一輪任務已提交: {len(first_child_ids)} 個任務", level="info")
            
            # 立即檢查每個任務的狀態，確認任務是否真的被提交到隊列
            # 分別檢查 FOFA、Hunter 和 Subfinder 任務
            for i, cid in enumerate(first_child_ids):
                try:
                    r = AsyncResult(cid, app=celery_app)
                    # 根據任務在列表中的位置判斷類型
                    if i < fofa_count:
                        job_type = "FOFA"
                    elif i < fofa_count + hunter_count:
                        job_type = "Hunter"
                    else:
                        job_type = "Subfinder"
                    _log_task(task_id, "pipeline", f"任務 {i+1}/{len(first_child_ids)} ({job_type}) 狀態: {r.state}, ID: {cid[:8]}...", level="info")
                    
                    # 如果 Hunter 任務狀態異常，記錄詳細信息（降低為 info 級別，因為 PENDING 是正常初始狀態）
                    if job_type == "Hunter" and r.state == 'PENDING':
                        # 只在提交後立即檢查時記錄，這是正常狀態
                        _log_task(task_id, "pipeline", f"Hunter 任務 {cid[:8]}... 已提交，當前狀態: PENDING（正常初始狀態）", level="info")
                except Exception as e:
                    _log_task(task_id, "pipeline", f"檢查任務 {cid} 狀態時出錯: {str(e)}", level="warning")

        # ----------------------------
        # 第二輪：subfinder 擴展後的新 domain 再查（可選）
        # 注意：第二輪將在 check_and_aggregate 中根據 subfinder 結果自動觸發
        # ----------------------------
        g2 = None
        second_jobs = []
        second_child_ids = []

        # ----------------------------
        # 後續收集工具（可選）
        # ----------------------------
        post_jobs = []
        post_child_ids = []
        if enable.get("httpx"):
            post_jobs.append(run_httpx.s(task_id, payload))
        if enable.get("nmap"):
            post_jobs.append(run_nmap.s(task_id, payload))
        if enable.get("nuclei"):
            post_jobs.append(run_nuclei.s(task_id, payload))

        g3 = None
        if post_jobs:
            g3 = group(*post_jobs).apply_async()
            post_child_ids = [c.id for c in g3.children] if g3.children else []

        # ----------------------------
        # 立即保存子任務 ID 到數據庫，以便取消功能可以正確工作
        # ----------------------------
        child_task_ids = {
            "first": first_child_ids,
            "second": second_child_ids,
            "post": post_child_ids,
        }
        
        # 立即更新數據庫，保存子任務 ID
        _update_task(
            task_id,
            output_data={
                **(task.output_data or {}),
                "child_task_ids": child_task_ids,
                "status": "running",
            },
            progress=10,
        )
        
        # 再次檢查任務是否已被取消（在提交任務後）
        db.refresh(task)
        if task.status == TaskStatus.CANCELLED:
            _log_task(task_id, "pipeline", "任務在提交後被取消，停止執行", level="info")
            # 取消所有已提交的子任務
            for cid in first_child_ids + post_child_ids:
                try:
                    r = AsyncResult(cid, app=celery_app)
                    state = r.state
                    if state == 'PENDING':
                        r.revoke(terminate=False)
                    elif state in ['STARTED', 'RETRY']:
                        r.revoke(terminate=True)
                except:
                    pass
            return {"error": "Task cancelled", "status": "cancelled"}

        check_and_aggregate.delay(task_id, child_task_ids)
        return {"status": "started", "child_task_ids": child_task_ids}
    finally:
        db.close()


from celery.result import AsyncResult


@celery_app.task(name="app.workers.tasks.check_and_aggregate")
def check_and_aggregate(task_id: int, child_task_ids: Dict[str, List[str]], max_wait: int = 3600) -> Dict[str, Any]:
    """B 模式聚合器：不依賴 GroupResult.restore，直接輪詢子任務 AsyncResult。"""
    import time

    start = time.time()
    check_interval = 5

    all_ids: List[str] = []
    for ids in (child_task_ids or {}).values():
        if isinstance(ids, list):
            all_ids.extend([x for x in ids if isinstance(x, str)])

    if not all_ids:
        _update_task(task_id, status=TaskStatus.FAILED, error="No child_task_ids to aggregate")
        return {"error": "no child_task_ids"}

    while time.time() - start < max_wait:
        db = _db()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"error": "Task not found"}

            rs = [AsyncResult(cid, app=celery_app) for cid in all_ids]
            completed = sum(1 for r in rs if r.ready())

            # 檢查任務是否已被取消
            if task.status == TaskStatus.CANCELLED:
                _log_task(task_id, "aggregate", "任務已被取消，停止聚合", level="info")
                # 取消所有子任務
                # 使用更智能的撤销逻辑：先检查任务状态，避免触发等待中的任务
                for cid in all_ids:
                    try:
                        r = AsyncResult(cid, app=celery_app)
                        state = r.state
                        if state == 'PENDING':
                            # 如果任务还在等待，使用 terminate=False 避免触发执行
                            r.revoke(terminate=False)
                        elif state in ['STARTED', 'RETRY']:
                            # 如果任务正在执行，使用 terminate=True 强制终止
                            r.revoke(terminate=True)
                        # 如果任务已经完成（SUCCESS/FAILURE），不需要撤销
                    except Exception as e:
                        _log_task(task_id, "aggregate", f"撤销子任務 {cid} 時出錯: {str(e)}", level="warning")
                return {"error": "Task cancelled", "status": "cancelled"}

            if completed != len(rs):
                progress = 10 + int((completed / len(rs)) * 80)
                _update_task(task_id, progress=progress)
                time.sleep(check_interval)
                continue

            results: List[Dict[str, Any]] = []
            for r in rs:
                try:
                    if r.successful():
                        # 使用 result 属性而不是 get() 方法，避免阻塞错误
                        # 如果任务成功，result 属性应该包含返回值
                        val = r.result
                        if isinstance(val, dict):
                            results.append(val)
                        elif isinstance(val, list):
                            results.extend([x for x in val if isinstance(x, dict)])
                        elif val is not None:
                            results.append({"raw": str(val)})
                    else:
                        # 任务失败，记录错误但继续处理
                        error_info = r.result if hasattr(r, 'result') else None
                        if error_info:
                            if isinstance(error_info, dict):
                                results.append({"error": str(error_info)})
                            else:
                                results.append({"error": str(error_info)})
                        else:
                            results.append({"error": "Task failed without result"})
                except Exception as e:
                    # 如果获取结果时出错，记录错误但继续
                    error_msg = str(e)
                    # 检查是否是 "Never call result.get()" 错误，如果是，尝试其他方式获取结果
                    if "Never call result.get()" in error_msg:
                        # 尝试直接访问 result 属性
                        try:
                            if hasattr(r, 'result') and r.result is not None:
                                val = r.result
                                if isinstance(val, dict):
                                    results.append(val)
                                elif isinstance(val, list):
                                    results.extend([x for x in val if isinstance(x, dict)])
                                else:
                                    results.append({"raw": str(val)})
                            else:
                                results.append({"error": "Cannot retrieve result (blocking call detected)"})
                        except:
                            results.append({"error": error_msg})
                    else:
                        results.append({"error": error_msg})

            # 步驟2：第一輪聚合 - 只聚合 FOFA/Hunter 結果到 assets 表（不包括 subfinder）
            # 分離 FOFA/Hunter 結果和 subfinder 結果
            fofa_hunter_results = []
            subfinder_result = None
            for r in results:
                if isinstance(r, dict):
                    # 識別 subfinder 結果
                    if r.get("_kind") == "subfinder" or ("domains" in r and "urls" in r):
                        subfinder_result = r
                    else:
                        # FOFA/Hunter 結果（有 search_records 字段）
                        if "search_records" in r:
                            fofa_hunter_results.append(r)
            
            # 只聚合 FOFA/Hunter 結果
            try:
                # 記錄聚合前的來源資產數（用於日誌說明）
                tenant_id = task.tenant_id
                task_id_local = task.id
                fofa_before = db.query(FofaAsset).filter(FofaAsset.tenant_id == tenant_id, FofaAsset.task_id == task_id_local).count()
                hunter_before = db.query(HunterAsset).filter(HunterAsset.tenant_id == tenant_id, HunterAsset.task_id == task_id_local).count()

                affected = _aggregate_assets_from_sources(db, task=task)
                _log_task(task_id, "aggregate", f"第一輪聚合完成（FOFA/Hunter）: 處理 {fofa_before + hunter_before} 條來源資產（FOFA: {fofa_before}, Hunter: {hunter_before}），聚合後新增/更新 {affected} 筆唯一資產", level="info")
            except Exception as e:
                _log_task(task_id, "aggregate", f"第一輪聚合失敗({type(e).__name__}): {str(e)}", level="error")

            # 聚合 SubfinderAsset 数据 - 创建 Domain 记录
            try:
                subfinder_before = db.query(SubfinderAsset).filter(SubfinderAsset.tenant_id == tenant_id, SubfinderAsset.task_id == task_id_local).count()

                # 新逻辑：从 subfinder_result 创建 Domain 记录
                service = DomainAggregationService(db)
                created_domains = 0

                if subfinder_result and not subfinder_result.get("error"):
                    seed_domains = subfinder_result.get("domains", [])
                    for domain_name in seed_domains:
                        domain_name = domain_name.strip().lower()
                        if not domain_name:
                            continue

                        # 提取根域名
                        root_domain = extract_root_domain(domain_name)

                        # 检查是否已存在（同一任务内）
                        existing = db.query(Domain).filter(
                            Domain.tenant_id == tenant_id,
                            Domain.task_id == task_id_local,
                            Domain.name == domain_name,
                        ).first()

                        if existing:
                            continue

                        # 创建 Domain 记录
                        try:
                            service.create_domain(
                                tenant_id=tenant_id,
                                task_id=task_id_local,
                                name=domain_name,
                                root_domain=root_domain,
                                discovered_by="subfinder",
                            )
                            created_domains += 1
                        except Exception:
                            db.rollback()
                            continue

                _log_task(task_id, "aggregate", f"Subfinder 域名处理完成: {subfinder_before} 条来源资产，创建 {created_domains} 条 Domain 记录", level="info")
            except Exception as e:
                _log_task(task_id, "aggregate", f"Subfinder 处理失敗({type(e).__name__}): {str(e)}", level="error")

            try:
                ded = _deduplicate_assets(db, task_id, task.tenant_id)
                _log_task(task_id, "deduplicate", f"第一輪去重完成(僅聚合表): 刪除 {ded} 筆", level="info")
            except Exception as e:
                _log_task(task_id, "deduplicate", f"第一輪去重失敗({type(e).__name__}): {str(e)}", level="error")

            # 步驟4：第二次聚合 - 將 FOFA/Hunter 聚合結果（assets 表中的域名）和 subfinder 結果進行聚合
            # 如果輸入的是域名且有 subfinder 結果，進行第二次聚合
            second_round_ids = []
            if subfinder_result and not subfinder_result.get("error"):
                # 提取 subfinder 發現的域名
                seed_domains = subfinder_result.get("domains", [])
                if seed_domains:
                    tenant_id = task.tenant_id
                    
                    # 步驟4：第二次聚合 - 將 FOFA/Hunter 聚合結果和 subfinder 結果進行聚合（通過域名）
                    # 獲取 assets 表中已存在的域名（來自 FOFA/Hunter）
                    existing_domains_in_assets = set()
                    existing_assets = db.query(Asset.domain).filter(
                        Asset.tenant_id == tenant_id,
                        Asset.domain.isnot(None),
                        Asset.domain != ""
                    ).all()
                    existing_domains_in_assets = {r[0].strip().lower() for r in existing_assets if r and r[0]}
                    
                    # 將 subfinder 發現的域名寫入 assets，並更新 sources（通過域名聚合）
                    # 即使域名已存在，也要更新 sources，添加 "subfinder"
                    subfinder_domains_lower = {d.strip().lower() for d in seed_domains if d and d.strip()}
                    updated_count = 0
                    for domain in subfinder_domains_lower:
                        # 查找該域名在 assets 表中的記錄（可能有多條，因為可能有不同的 ip/port 組合）
                        domain_assets = db.query(Asset).filter(
                            Asset.tenant_id == tenant_id,
                            Asset.domain == domain
                        ).all()
                        
                        if domain_assets:
                            # 域名已存在，更新 sources 和 discovered_by，添加 "subfinder"
                            current_time = datetime.utcnow()
                            for asset in domain_assets:
                                existing_sources = set(asset.sources or [])
                                source_added = False
                                if "subfinder" not in existing_sources:
                                    existing_sources.add("subfinder")
                                    asset.sources = list(existing_sources)
                                    source_added = True

                                # 同时更新 discovered_by 字段
                                discovered_by = asset.discovered_by or {}
                                if "subfinder" not in discovered_by:
                                    discovered_by["subfinder"] = {
                                        "first_seen": current_time.isoformat(),
                                        "count": 1
                                    }
                                    source_added = True
                                else:
                                    # 更新计数
                                    discovered_by["subfinder"]["count"] = discovered_by["subfinder"].get("count", 0) + 1
                                    source_added = True

                                if source_added:
                                    asset.discovered_by = discovered_by
                                    asset.last_seen = current_time
                                    updated_count += 1
                        else:
                            # 域名不存在，創建新記錄（只填 domain，其他字段為空）
                            # 注意：這裡創建的資產只有 domain，沒有 url/ip/port，這是正常的
                            # 這些資產會在第二輪查詢後被 FOFA/Hunter 結果更新
                            _ensure_domains_in_assets(db, task=task, domains=[domain], source="subfinder")
                            updated_count += 1
                    
                    db.commit()
                    _log_task(task_id, "aggregate", f"第二次聚合完成（Subfinder 域名已聚合到 assets）: {len(subfinder_domains_lower)} 個域名，更新 {updated_count} 筆", level="info")
                    
                    # 步驟5：提取 subfinder 獨有的域名（FOFA/Hunter 沒有發現的）
                    # 找出 subfinder 發現但 FOFA/Hunter 沒有發現的域名
                    new_domains = [d for d in seed_domains if d and d.strip() and d.strip().lower() not in existing_domains_in_assets]
                    
                    if new_domains:
                        _log_task(task_id, "pipeline", f"Subfinder 發現 {len(new_domains)} 個獨有域名（FOFA/Hunter 未發現），觸發第二輪查詢", level="info")
                        
                        # 獲取原始 payload 配置
                        original_payload = task.input_data or {}
                        enable = original_payload.get("enable", {}) or {}
                        
                        # 第二輪：對新 domain 逐個查 FOFA/Hunter
                        second_jobs = []
                        for d in new_domains:
                            # FOFA 任務：檢查 enable 配置，預設啟用
                            if enable.get("fofa", True):
                                p1 = dict(original_payload)
                                p1["fofa_query"] = f'domain="{d}"'
                                second_jobs.append(run_fofa_pull.s(task_id, p1))
                            
                            # Hunter 任務：檢查 enable 配置，預設啟用
                            if enable.get("hunter", True):
                                p2 = dict(original_payload)
                                p2["hunter_query"] = f'domain="{d}"'
                                second_jobs.append(run_hunter_pull.s(task_id, p2))
                        
                        if second_jobs:
                            # 使用 celery_app 显式提交任务，确保任务被正确提交到队列
                            g2 = group(*second_jobs).apply_async()
                            second_round_ids = [c.id for c in g2.children] if g2.children else []
                            _log_task(task_id, "pipeline", f"第二輪查詢已啟動: {len(second_jobs)} 個任務，任務IDs: {second_round_ids[:5]}...", level="info")
                            
                            # 验证任务是否真的被提交
                            if not second_round_ids:
                                _log_task(task_id, "pipeline", "錯誤：第二輪任務ID為空，任務未正確提交，跳過第二輪查詢", level="error")
                            else:
                                # 立即检查任务状态
                                try:
                                    test_result = AsyncResult(second_round_ids[0], app=celery_app)
                                    _log_task(task_id, "pipeline", f"第一個任務狀態檢查: {test_result.state} (ID: {second_round_ids[0]})", level="info")
                                except Exception as e:
                                    _log_task(task_id, "pipeline", f"檢查任務狀態失敗: {str(e)}", level="warning")
                            
                            # 只有在任務ID不為空時才等待
                            if second_round_ids:
                                # 等待第二輪完成
                                second_start = time.time()
                                max_wait_seconds = 600  # 最多等待10分鐘
                                check_interval_second = 1  # 每1秒檢查一次
                                last_log_time = 0
                                max_pending_time = 60  # 如果所有任務都是 PENDING 超過60秒，提前結束
                                pending_start_time = None
                                
                                while time.time() - second_start < max_wait_seconds:
                                    # 檢查任務是否已被取消
                                    db.refresh(task)
                                    if task.status == TaskStatus.CANCELLED:
                                        _log_task(task_id, "pipeline", "任務已被取消，停止第二輪查詢", level="info")
                                        # 取消所有第二輪任務
                                        # 使用更智能的撤销逻辑：先检查任务状态，避免触发等待中的任务
                                        for cid in second_round_ids:
                                            try:
                                                r = AsyncResult(cid, app=celery_app)
                                                state = r.state
                                                if state == 'PENDING':
                                                    # 如果任务还在等待，使用 terminate=False 避免触发执行
                                                    r.revoke(terminate=False)
                                                elif state in ['STARTED', 'RETRY']:
                                                    # 如果任务正在执行，使用 terminate=True 强制终止
                                                    r.revoke(terminate=True)
                                                # 如果任务已经完成（SUCCESS/FAILURE），不需要撤销
                                            except Exception as e:
                                                _log_task(task_id, "pipeline", f"撤销第二輪任務 {cid} 時出錯: {str(e)}", level="warning")
                                        break
                                    
                                    second_rs = [AsyncResult(cid, app=celery_app) for cid in second_round_ids]
                                    second_completed = sum(1 for r in second_rs if r.ready())
                                    second_failed = sum(1 for r in second_rs if r.failed())
                                    
                                    # 檢查任務狀態（更詳細的診斷）
                                    elapsed = int(time.time() - second_start)
                                    
                                    # 檢查任務是否真的存在
                                    active_count = 0
                                    pending_count = 0
                                    for r in second_rs:
                                        try:
                                            state = r.state
                                            if state == 'PENDING':
                                                pending_count += 1
                                            elif state in ['STARTED', 'RETRY']:
                                                active_count += 1
                                        except Exception as e:
                                            _log_task(task_id, "pipeline", f"檢查任務狀態時出錯: {str(e)}", level="warning")
                                    
                                    # 如果所有任務都是 PENDING，記錄開始時間
                                    if pending_count == len(second_rs) and second_completed == 0:
                                        if pending_start_time is None:
                                            pending_start_time = time.time()
                                        elif time.time() - pending_start_time > max_pending_time:
                                            _log_task(task_id, "pipeline", 
                                                f"錯誤：所有第二輪任務仍在 PENDING 狀態（已等待 {int(time.time() - pending_start_time)} 秒），"
                                                f"可能是 Celery worker 未運行或任務隊列有問題，提前結束等待", 
                                                level="error")
                                            # 提前結束等待，處理已有結果
                                            break
                                    else:
                                        # 有任務開始執行，重置 pending_start_time
                                        pending_start_time = None
                                    
                                    # 每10秒記錄一次詳細狀態，避免日志過多
                                    if elapsed - last_log_time >= 10:
                                        _log_task(task_id, "pipeline", 
                                            f"第二輪查詢狀態: {second_completed + second_failed}/{len(second_rs)} 完成，"
                                            f"執行中: {active_count}，等待中: {pending_count}，"
                                            f"已等待 {elapsed} 秒", 
                                            level="info")
                                        last_log_time = elapsed
                                
                                    # 記錄進度（簡化，避免日志過多）
                                    if second_completed + second_failed < len(second_rs) and elapsed % 30 == 0:
                                        _log_task(task_id, "pipeline", 
                                            f"第二輪查詢進行中: {second_completed + second_failed}/{len(second_rs)} 完成（已等待 {elapsed} 秒）", 
                                            level="info")
                                    
                                    if second_completed + second_failed == len(second_rs):
                                        # 所有任務都已完成（成功或失敗）
                                        # 收集第二輪結果
                                        second_results = []
                                        for r in second_rs:
                                            try:
                                                if r.successful():
                                                    # 使用 r.result 而不是 r.get()，避免在 task 内部阻塞
                                                    val = r.result
                                                    if isinstance(val, dict):
                                                        second_results.append(val)
                                                    elif isinstance(val, list):
                                                        second_results.extend([x for x in val if isinstance(x, dict)])
                                                elif r.failed():
                                                    error_msg = str(r.result) if r.result else "Task failed"
                                                    second_results.append({"error": error_msg})
                                                    _log_task(task_id, "pipeline", f"第二輪任務失敗: {error_msg}", level="error")
                                            except Exception as e:
                                                error_msg = str(e)
                                                second_results.append({"error": error_msg})
                                                _log_task(task_id, "pipeline", f"第二輪結果收集錯誤: {error_msg}", level="error")
                                        
                                        # 將第二輪結果加入總結果
                                        results.extend(second_results)
                                        
                                        # 第二輪聚合 - 创建 DomainIP 记录
                                        try:
                                            affected2 = _aggregate_assets_from_sources(db, task=task)
                                            _log_task(task_id, "aggregate", f"第二輪来源表聚合完成: 寫入/更新 {affected2} 筆", level="info")

                                            # 新逻辑：从 FofaAsset/HunterAsset 创建 DomainIP 记录
                                            service = DomainAggregationService(db)

                                            # 获取该任务下的所有 domains
                                            domains = db.query(Domain).filter(
                                                Domain.tenant_id == tenant_id,
                                                Domain.task_id == task_id,
                                            ).all()

                                            created_ips = 0
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
                                                        created_ips += 1

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
                                                        created_ips += 1

                                                # 更新 Domain 统计
                                                service.update_domain_stats(domain.id)

                                                # 更新 Domain 状态
                                                domain.scan_status = "completed"

                                            db.commit()
                                            _log_task(task_id, "aggregate", f"DomainIP 记录创建完成: {created_ips} 条", level="info")

                                        except Exception as e:
                                            _log_task(task_id, "aggregate", f"第二輪 DomainIP 创建失敗({type(e).__name__}): {str(e)}", level="error")
                                        
                                        try:
                                            ded2 = _deduplicate_assets(db, task_id, task.tenant_id)
                                            _log_task(task_id, "deduplicate", f"第二輪去重完成: 刪除 {ded2} 筆", level="info")
                                        except Exception as e:
                                            _log_task(task_id, "deduplicate", f"第二輪去重失敗({type(e).__name__}): {str(e)}", level="error")
                                        
                                        _log_task(task_id, "pipeline", f"第二輪查詢完成: {len(second_results)} 個結果", level="info")
                                        break
                                    
                                    time.sleep(check_interval_second)
                                else:
                                    # 超時處理
                                    _log_task(task_id, "pipeline", 
                                        f"第二輪查詢超時（等待超過 {max_wait_seconds} 秒），強制結束並處理已有結果", 
                                        level="warning")
                                    
                                # 強制取消所有未完成的任務
                                # 使用更智能的撤销逻辑：先检查任务状态，避免触发等待中的任务
                                for cid in second_round_ids:
                                    try:
                                        r = AsyncResult(cid, app=celery_app)
                                        if not r.ready():
                                            state = r.state
                                            if state == 'PENDING':
                                                # 如果任务还在等待，使用 terminate=False 避免触发执行
                                                r.revoke(terminate=False)
                                            elif state in ['STARTED', 'RETRY']:
                                                # 如果任务正在执行，使用 terminate=True 强制终止
                                                r.revoke(terminate=True)
                                            _log_task(task_id, "pipeline", f"強制取消任務: {cid} (狀態: {state})", level="warning")
                                    except Exception as e:
                                        _log_task(task_id, "pipeline", f"取消任務失敗 {cid}: {str(e)}", level="error")
                                    
                                    # 收集已完成的结果
                                    second_results = []
                                    for cid in second_round_ids:
                                        try:
                                            r = AsyncResult(cid, app=celery_app)
                                            if r.ready():
                                                if r.successful():
                                                    val = r.result
                                                    if isinstance(val, dict):
                                                        second_results.append(val)
                                                    elif isinstance(val, list):
                                                        second_results.extend([x for x in val if isinstance(x, dict)])
                                                elif r.failed():
                                                    error_msg = str(r.result) if r.result else "Task failed"
                                                    second_results.append({"error": error_msg})
                                            else:
                                                # 任務未完成，記錄為超時錯誤
                                                second_results.append({"error": "Task timeout (not completed within time limit)"})
                                        except Exception as e:
                                            second_results.append({"error": f"Failed to get result: {str(e)}"})
                                    
                                    if second_results:
                                        results.extend(second_results)
                                        try:
                                            affected2 = _aggregate_assets_from_sources(db, task=task)
                                            _log_task(task_id, "aggregate", f"第二輪聚合完成（超時後）: 寫入/更新 {affected2} 筆", level="info")
                                        except Exception as e:
                                            _log_task(task_id, "aggregate", f"第二輪聚合失敗（超時後）({type(e).__name__}): {str(e)}", level="error")

            output_data = aggregate_pipeline_results(task_id, results)
            _update_task(task_id, progress=100, output_data=output_data)
            return {"status": "completed", "results_count": len(results), "second_round_tasks": len(second_round_ids)}
        finally:
            db.close()

    _update_task(task_id, status=TaskStatus.FAILED, error="Pipeline execution timeout")
    return {"error": "timeout"}
