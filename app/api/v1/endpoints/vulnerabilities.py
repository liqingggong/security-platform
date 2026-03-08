from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.api.deps import get_current_tenant_id, get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.vulnerability import VulnerabilityInDB, VulnerabilityUpdate, VulnerabilityFilter

router = APIRouter()


@router.get("", response_model=List[VulnerabilityInDB])
def list_vulnerabilities(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[models.VulnerabilitySeverity] = None,
    status: Optional[str] = None,
    task_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    cve_id: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    列出當前租戶的所有漏洞
    支持按嚴重程度、狀態、任務ID、資產ID、CVE ID、搜索關鍵字過濾
    """
    query = db.query(models.Vulnerability).filter(models.Vulnerability.tenant_id == tenant_id)

    # 按嚴重程度過濾
    if severity:
        query = query.filter(models.Vulnerability.severity == severity)

    # 按狀態過濾
    if status:
        query = query.filter(models.Vulnerability.status == status)

    # 按任務ID過濾
    if task_id:
        query = query.filter(models.Vulnerability.task_id == task_id)

    # 按資產ID過濾
    if asset_id:
        query = query.filter(models.Vulnerability.asset_id == asset_id)

    # 按CVE ID過濾
    if cve_id:
        query = query.filter(models.Vulnerability.cve_id == cve_id)

    # 搜索關鍵字（在 title 或 description 中搜索）
    if search:
        query = query.filter(
            or_(
                models.Vulnerability.title.contains(search),
                models.Vulnerability.description.contains(search),
            )
        )

    vulnerabilities = (
        query.options(joinedload(models.Vulnerability.asset))
        .order_by(
            models.Vulnerability.severity.desc(),
            models.Vulnerability.discovered_at.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # 将漏洞数据转换为字典，并包含资产信息
    result = []
    for vuln in vulnerabilities:
        vuln_dict = {
            "id": vuln.id,
            "title": vuln.title,
            "description": vuln.description,
            "severity": vuln.severity,
            "cve_id": vuln.cve_id,
            "cwe_id": vuln.cwe_id,
            "cvss_score": vuln.cvss_score,
            "references": vuln.references,
            "raw_data": vuln.raw_data,
            "status": vuln.status,
            "discovered_at": vuln.discovered_at,
            "updated_at": vuln.updated_at,
            "tenant_id": vuln.tenant_id,
            "task_id": vuln.task_id,
            "asset_id": vuln.asset_id,
        }
        # 从关联的资产中提取信息
        if vuln.asset:
            vuln_dict["asset_url"] = vuln.asset.url
            vuln_dict["asset_ip"] = vuln.asset.ip_address
            vuln_dict["asset_domain"] = vuln.asset.domain
            vuln_dict["asset_port"] = vuln.asset.port
        else:
            vuln_dict["asset_url"] = None
            vuln_dict["asset_ip"] = None
            vuln_dict["asset_domain"] = None
            vuln_dict["asset_port"] = None
        result.append(vuln_dict)
    
    return result


@router.get("/{vulnerability_id}", response_model=VulnerabilityInDB)
def get_vulnerability(
    *,
    db: Session = Depends(get_db),
    vulnerability_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取特定漏洞的詳細信息
    """
    vulnerability = (
        db.query(models.Vulnerability)
        .options(joinedload(models.Vulnerability.asset))
        .filter(
            models.Vulnerability.id == vulnerability_id,
            models.Vulnerability.tenant_id == tenant_id,
        )
        .first()
    )

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="漏洞不存在",
        )

    # 构建包含资产信息的响应
    vuln_dict = {
        "id": vulnerability.id,
        "title": vulnerability.title,
        "description": vulnerability.description,
        "severity": vulnerability.severity,
        "cve_id": vulnerability.cve_id,
        "cwe_id": vulnerability.cwe_id,
        "cvss_score": vulnerability.cvss_score,
        "references": vulnerability.references,
        "raw_data": vulnerability.raw_data,
        "status": vulnerability.status,
        "discovered_at": vulnerability.discovered_at,
        "updated_at": vulnerability.updated_at,
        "tenant_id": vulnerability.tenant_id,
        "task_id": vulnerability.task_id,
        "asset_id": vulnerability.asset_id,
    }
    # 从关联的资产中提取信息
    if vulnerability.asset:
        vuln_dict["asset_url"] = vulnerability.asset.url
        vuln_dict["asset_ip"] = vulnerability.asset.ip_address
        vuln_dict["asset_domain"] = vulnerability.asset.domain
        vuln_dict["asset_port"] = vulnerability.asset.port
    else:
        vuln_dict["asset_url"] = None
        vuln_dict["asset_ip"] = None
        vuln_dict["asset_domain"] = None
        vuln_dict["asset_port"] = None
    
    return vuln_dict


@router.patch("/{vulnerability_id}", response_model=VulnerabilityInDB)
def update_vulnerability(
    *,
    db: Session = Depends(get_db),
    vulnerability_id: int,
    vulnerability_in: VulnerabilityUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    更新漏洞狀態
    """
    vulnerability = (
        db.query(models.Vulnerability)
        .filter(
            models.Vulnerability.id == vulnerability_id,
            models.Vulnerability.tenant_id == tenant_id,
        )
        .first()
    )

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="漏洞不存在",
        )

    if vulnerability_in.status:
        vulnerability.status = vulnerability_in.status

    db.commit()
    db.refresh(vulnerability)

    return vulnerability


@router.get("/stats/summary")
def get_vulnerability_stats(
    *,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取漏洞統計信息
    """
    total = (
        db.query(models.Vulnerability)
        .filter(models.Vulnerability.tenant_id == tenant_id)
        .count()
    )

    stats_by_severity = {}
    for severity in models.VulnerabilitySeverity:
        count = (
            db.query(models.Vulnerability)
            .filter(
                models.Vulnerability.tenant_id == tenant_id,
                models.Vulnerability.severity == severity,
            )
            .count()
        )
        stats_by_severity[severity.value] = count

    stats_by_status = {}
    statuses = ["open", "in_progress", "resolved", "false_positive"]
    for stat in statuses:
        count = (
            db.query(models.Vulnerability)
            .filter(
                models.Vulnerability.tenant_id == tenant_id,
                models.Vulnerability.status == stat,
            )
            .count()
        )
        stats_by_status[stat] = count

    return {
        "total": total,
        "by_severity": stats_by_severity,
        "by_status": stats_by_status,
    }

