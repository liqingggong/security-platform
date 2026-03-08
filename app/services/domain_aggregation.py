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

    def get_domain_with_assets(self, domain_id: int) -> Optional[Dict[str, Any]]:
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
        from sqlalchemy.exc import IntegrityError

        existing = self.db.query(DomainIP).filter(
            DomainIP.tenant_id == tenant_id,
            DomainIP.domain_id == domain_id,
            DomainIP.ip_address == ip_address,
            DomainIP.port == port,
        ).first()

        current_time = datetime.utcnow()

        if existing:
            # 更新现有记录
            if source not in (existing.sources or []):
                existing.sources = list((existing.sources or []) + [source])

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
                sources=[source] if source else [],
                discovered_by={
                    source: {
                        "first_seen": current_time.isoformat(),
                        "count": 1,
                    }
                } if source else {},
                product=product,
                banner=banner,
                raw_data={source: raw_data} if raw_data and source else {},
            )
            self.db.add(domain_ip)
            try:
                self.db.commit()
                self.db.refresh(domain_ip)
                return domain_ip
            except IntegrityError:
                self.db.rollback()
                # 可能并发创建，尝试再次获取
                existing = self.db.query(DomainIP).filter(
                    DomainIP.tenant_id == tenant_id,
                    DomainIP.domain_id == domain_id,
                    DomainIP.ip_address == ip_address,
                    DomainIP.port == port,
                ).first()
                if existing:
                    return existing
                raise

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
