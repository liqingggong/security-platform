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
    FofaAsset,
    HunterAsset,
    ScanPlan,
    ScanPlanTool,
    Task,
    TaskLog,
    TaskStatus,
    Vulnerability,
    VulnerabilitySeverity,
)
from app.db.session import SessionLocal
from app.services.repositories import ApiCredentialRepository
from app.utils.command_builder import build_command, get_tool_command_from_config
from app.workers.celery_app import celery_app
from tools.fofa_provider import FofaProvider
from tools.hunter_provider import HunterProvider
from tools.utils import get_tool_command


def _db() -> Session:
    return SessionLocal()


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
    from sqlalchemy.exc import IntegrityError

    norm_domain = (domain or "").strip().lower() or None
    norm_url = (url or "").strip() or None

    query = db.query(Asset).filter(Asset.tenant_id == tenant_id)
    if norm_domain:
        query = query.filter(Asset.domain == norm_domain, Asset.ip_address == ip_address, Asset.port == port)
    else:
        query = query.filter(Asset.url == norm_url, Asset.ip_address == ip_address, Asset.port == port)

    obj = query.one_or_none()

    if obj is None:
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
        )
        db.add(obj)
        try:
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            obj = query.one_or_none()
            if obj is None:
                raise

    obj.last_seen = datetime.utcnow()

    existing_sources = set(obj.sources or [])
    existing_sources.add(source)
    obj.sources = list(existing_sources)

    if tags:
        existing_tags = set(obj.tags or [])
        existing_tags.update(tags)
        obj.tags = list(existing_tags)

    if data:
        merged = obj.data or {}
        merged.update(data)
        obj.data = merged

    if not obj.product and product:
        obj.product = product

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _aggregate_assets_from_sources(db: Session, *, task: Task) -> int:
    tenant_id = task.tenant_id
    task_id = task.id

    fofa_rows = db.query(FofaAsset).filter(FofaAsset.tenant_id == tenant_id, FofaAsset.task_id == task_id).all()
    hunter_rows = db.query(HunterAsset).filter(HunterAsset.tenant_id == tenant_id, HunterAsset.task_id == task_id).all()

    affected = 0

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
        affected += 1

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
        affected += 1

    return affected


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
            data={"source": source},
            tags=[source],
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
        search_records = provider.search(query=fofa_query, fields=fields, limit=limit)

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
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "fofa", f"FOFA 失敗: {str(e)}", level="error")
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_hunter_pull")
def run_hunter_pull(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

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
        limit = payload.get("limit", 1000)
        search_records = provider.search(query=hunter_query, limit=limit)

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
        _update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        _log_task(task_id, "hunter", f"Hunter 失敗: {str(e)}", level="error")
        return {"error": str(e)}
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
        domains: List[str] = []

        for domain in root_domains:
            variables = {"domain": domain}
            cmd_parts = build_command(command_template, variables, "subfinder")
            if cmd_parts and cmd_parts[0] == "subfinder":
                cmd = tool_base_cmd + cmd_parts[1:]
            else:
                cmd = cmd_parts

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 30)
            if proc.returncode != 0:
                _log_task(task_id, "subfinder", f"subfinder error for {domain}: {proc.stderr}", level="error")
                continue

            # subfinder 輸出通常是 host，每行一個；你說輸出是一列 url，這裡兩者都兼容：
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                all_urls.append(line)
                dom = _extract_domain_from_url(line) or line
                if dom:
                    domains.append(dom)

        # 去重
        domains = sorted({d.strip().lower() for d in domains if d and d.strip()})

        return {"urls": all_urls, "domains": domains, "inserted_count": len(domains)}

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

            if result.get("_kind") == "subfinder":
                aggregated["subfinder"] = result
            elif "search_records" in result:
                # 透過 source 判斷
                first = (result.get("search_records") or [{}])[0]
                if isinstance(first, dict) and first.get("source") == "hunter":
                    aggregated["hunter"] = result
                else:
                    aggregated["fofa"] = result
            elif "xml" in result:
                aggregated["nmap"] = result
            elif "alive" in result:
                aggregated["httpx"] = result
            elif "findings" in result:
                aggregated["nuclei"] = result
                total_vulnerabilities += result.get("inserted_count", 0)

            if "error" in result:
                errors.append(result["error"])

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

        output_data = {
            "results": aggregated,
            "summary": {
                "total_assets_discovered": db.query(Asset).filter(Asset.tenant_id == task.tenant_id, Asset.task_id == task_id).count(),
                "total_vulnerabilities_found": total_vulnerabilities,
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


# # # # # @celery_app.task(name="app.workers.tasks.run_pipeline_legacy")
# def run_pipeline_legacy(task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """舊版同步 pipeline（保留但不再使用）：

    這個版本會在 Celery task 內呼叫 group_result.get()，Celery 會拋出
    RuntimeError(E_WOULDBLOCK)。

    已改用下方的 B 模式非阻塞 pipeline：run_pipeline。
    """
    db = _db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        _log_task(task_id, "pipeline", f"Pipeline 開始執行，task_id={task_id}", level="info")
        _update_task(task_id, status=TaskStatus.RUNNING, started_at=datetime.utcnow(), progress=1)

        tenant_id = task.tenant_id
        payload = payload or {}

        enable = payload.get("enable", {}) or {}
        root_domains = payload.get("root_domains") or []
        ips = payload.get("ips") or []

        # 第一輪：優先使用使用者提供的 query；若沒有，且提供 root_domains/ips，則生成 query（逐個 domain）
        first_round_jobs = []

        if payload.get("fofa_query"):
            first_round_jobs.append(run_fofa_pull.s(task_id, payload))
        if payload.get("hunter_query"):
            first_round_jobs.append(run_hunter_pull.s(task_id, payload))

        # 若沒提供 query，且有 root_domains：逐個 domain 查（A）
        if not payload.get("fofa_query") and root_domains:
            # 逐個 domain，避免 query 太長
            for d in root_domains:
                q_payload = dict(payload)
                q_payload["fofa_query"] = f'domain="{d}"'
                first_round_jobs.append(run_fofa_pull.s(task_id, q_payload))

        if not payload.get("hunter_query") and root_domains:
            for d in root_domains:
                q_payload = dict(payload)
                q_payload["hunter_query"] = f'domain="{d}"'
                first_round_jobs.append(run_hunter_pull.s(task_id, q_payload))

        # 若提供 ips 但沒提供 query，做 ip 查
        if not payload.get("fofa_query") and ips:
            for ip in ips:
                q_payload = dict(payload)
                q_payload["fofa_query"] = f'ip="{ip}"'
                first_round_jobs.append(run_fofa_pull.s(task_id, q_payload))

        if not payload.get("hunter_query") and ips:
            for ip in ips:
                q_payload = dict(payload)
                q_payload["hunter_query"] = f'ip="{ip}"'
                first_round_jobs.append(run_hunter_pull.s(task_id, q_payload))

        if not first_round_jobs:
            return {"error": "no fofa/hunter jobs"}

        # 執行第一輪（並行），等待結果
        first_group = group(*first_round_jobs).apply_async()
        first_group.get(timeout=60 * 60)

        # 第一輪聚合
        _aggregate_assets_from_sources(db, task=task)
        _deduplicate_assets(db, task_id, tenant_id)

        # 若輸入為 domain（root_domains 非空），走 subfinder 擴展 + 第二輪
        if root_domains and (enable.get("subfinder") or True):
            sf_result = run_subfinder.apply(args=(task_id, {"root_domains": root_domains, "plan_tool_configs": payload.get("plan_tool_configs") or {}}))
            sf_payload = sf_result.get() if hasattr(sf_result, "get") else sf_result
            domains = (sf_payload or {}).get("domains") or []

            # 新域名判定：與 assets 比對
            new_domains = _get_domains_for_second_round(db, tenant_id=tenant_id, task_id=task_id, seed_domains=domains)

            # 將新 domain 寫入 assets（domain 欄位，其它空）
            _ensure_domains_in_assets(db, task=task, domains=new_domains, source="subfinder")

            # 第二輪：逐個新域名跑 fofa/hunter
            second_jobs = []
            for d in new_domains:
                fq = dict(payload)
                fq["fofa_query"] = f'domain="{d}"'
                second_jobs.append(run_fofa_pull.s(task_id, fq))

                hq = dict(payload)
                hq["hunter_query"] = f'domain="{d}"'
                second_jobs.append(run_hunter_pull.s(task_id, hq))

            if second_jobs:
                second_group = group(*second_jobs).apply_async()
                second_group.get(timeout=60 * 60)

                _aggregate_assets_from_sources(db, task=task)
                _deduplicate_assets(db, task_id, tenant_id)

        # 後續工具（預設從 assets 讀目標）
        post_results = []
        post_jobs = []
        if enable.get("httpx"):
            post_jobs.append(run_httpx.s(task_id, payload))
        if enable.get("nmap"):
            post_jobs.append(run_nmap.s(task_id, payload))
        if enable.get("nuclei"):
            post_jobs.append(run_nuclei.s(task_id, payload))

        if post_jobs:
            post_group = group(*post_jobs).apply_async()
            post_results = post_group.get(timeout=60 * 60)

        # 最終聚合結果輸出：將所有 group 的結果展平成一個 list[dict]
        all_results: List[Dict[str, Any]] = []
        for group_result in [first_results, second_results, post_results]:
            if isinstance(group_result, list):
                all_results.extend(group_result)
            elif isinstance(group_result, dict):
                all_results.append(group_result)

        return aggregate_pipeline_results(task_id, all_results)

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

        if payload.get("fofa_query"):
            first_jobs.append(run_fofa_pull.s(task_id, payload))
        if payload.get("hunter_query"):
            first_jobs.append(run_hunter_pull.s(task_id, payload))

        # 若未提供 query，且提供 root_domains/ips，則逐個生成 query（A）
        if not payload.get("fofa_query") and root_domains:
            for d in root_domains:
                p = dict(payload)
                p["fofa_query"] = f'domain="{d}"'
                first_jobs.append(run_fofa_pull.s(task_id, p))
        if not payload.get("hunter_query") and root_domains:
            for d in root_domains:
                p = dict(payload)
                p["hunter_query"] = f'domain="{d}"'
                first_jobs.append(run_hunter_pull.s(task_id, p))

        if not payload.get("fofa_query") and ips:
            for ip in ips:
                p = dict(payload)
                p["fofa_query"] = f'ip="{ip}"'
                first_jobs.append(run_fofa_pull.s(task_id, p))
        if not payload.get("hunter_query") and ips:
            for ip in ips:
                p = dict(payload)
                p["hunter_query"] = f'ip="{ip}"'
                first_jobs.append(run_hunter_pull.s(task_id, p))

        if not first_jobs:
            _update_task(task_id, status=TaskStatus.FAILED, error="no fofa/hunter jobs")
            return {"error": "no fofa/hunter jobs"}

        g1 = group(*first_jobs).apply_async()

        # ----------------------------
        # 第二輪：subfinder 擴展後的新 domain 再查（可選）
        # ----------------------------
        g2 = None
        second_jobs = []
        if root_domains and enable.get("subfinder", True):
            # 先直接同步跑 subfinder（避免再套一層 group 回調，降低複雜度）
            sf_out = run_subfinder(task_id, {"root_domains": root_domains, "plan_tool_configs": payload.get("plan_tool_configs") or {}})
            if isinstance(sf_out, dict):
                sf_out["_kind"] = "subfinder"
            else:
                sf_out = {"_kind": "subfinder", "error": "subfinder failed"}

            seed_domains = (sf_out.get("domains") or []) if isinstance(sf_out, dict) else []
            tenant_id = task.tenant_id

            # 新域名判定：與 assets 聚合表比對（你確認：是）
            new_domains = _get_domains_for_second_round(db, tenant_id=tenant_id, task_id=task_id, seed_domains=seed_domains)

            # 把 subfinder 新域名寫入 assets（只填 domain，其它空）
            _ensure_domains_in_assets(db, task=task, domains=new_domains, source="subfinder")

            # 第二輪：對新 domain 逐個查（你確認：A）
            for d in new_domains:
                p1 = dict(payload)
                p1["fofa_query"] = f'domain="{d}"'
                second_jobs.append(run_fofa_pull.s(task_id, p1))

                p2 = dict(payload)
                p2["hunter_query"] = f'domain="{d}"'
                second_jobs.append(run_hunter_pull.s(task_id, p2))

            if second_jobs:
                g2 = group(*second_jobs).apply_async()

        # ----------------------------
        # 後續收集工具（可選）
        # ----------------------------
        post_jobs = []
        if enable.get("httpx"):
            post_jobs.append(run_httpx.s(task_id, payload))
        if enable.get("nmap"):
            post_jobs.append(run_nmap.s(task_id, payload))
        if enable.get("nuclei"):
            post_jobs.append(run_nuclei.s(task_id, payload))

        g3 = None
        if post_jobs:
            g3 = group(*post_jobs).apply_async()

        # ----------------------------
        # 交給 check_and_aggregate 聚合
        # ----------------------------
        child_task_ids = {
            "first": [c.id for c in (getattr(g1, "children", None) or [])],
            "second": [c.id for c in (getattr(g2, "children", None) or [])] if g2 else [],
            "post": [c.id for c in (getattr(g3, "children", None) or [])] if g3 else [],
        }

        _update_task(
            task_id,
            output_data={
                **(task.output_data or {}),
                "child_task_ids": child_task_ids,
                "status": "running",
            },
            progress=10,
        )

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

            if completed != len(rs):
                progress = 10 + int((completed / len(rs)) * 80)
                _update_task(task_id, progress=progress)
                time.sleep(check_interval)
                continue

            results: List[Dict[str, Any]] = []
            for r in rs:
                try:
                    if r.successful():
                        val = r.get(timeout=1)
                        if isinstance(val, dict):
                            results.append(val)
                        elif isinstance(val, list):
                            results.extend([x for x in val if isinstance(x, dict)])
                        else:
                            results.append({"raw": str(val)})
                    else:
                        results.append({"error": str(r.result) if r.result else "Task failed"})
                except Exception as e:
                    results.append({"error": str(e)})

            try:
                affected = _aggregate_assets_from_sources(db, task=task)
                _log_task(task_id, "aggregate", f"聚合完成: 寫入/更新 {affected} 筆", level="info")
            except Exception as e:
                _log_task(task_id, "aggregate", f"聚合失敗({type(e).__name__}): {str(e)}", level="error")

            try:
                ded = _deduplicate_assets(db, task_id, task.tenant_id)
                _log_task(task_id, "deduplicate", f"去重完成(僅聚合表): 刪除 {ded} 筆", level="info")
            except Exception as e:
                _log_task(task_id, "deduplicate", f"去重失敗({type(e).__name__}): {str(e)}", level="error")

            output_data = aggregate_pipeline_results(task_id, results)
            _update_task(task_id, progress=100, output_data=output_data)
            return {"status": "completed", "results_count": len(results)}
        finally:
            db.close()

    _update_task(task_id, status=TaskStatus.FAILED, error="Pipeline execution timeout")
    return {"error": "timeout"}

# # # # @celery_app.task(name="app.workers.tasks.check_and_aggregate_legacy")
# def check_and_aggregate_legacy(task_id: int, group_id: str, step_count: int, child_task_ids: list = None, max_wait: int = 3600):
    return {"status": "noop"}