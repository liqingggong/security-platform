#!/usr/bin/env python3
"""
Migrate existing Asset data to new domain-driven schema.

Run: python scripts/migrate_to_domain_driven.py
"""

import sys
from datetime import datetime
from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '/Users/liqinggong/Documents/Information_gathering_and_scanning_tools/security_platform')

from app.core.config import settings
from app.db.models import (
    Asset, Domain, DomainIP, DomainEndpoint,
    SubfinderAsset, FofaAsset, HunterAsset, Task
)
from app.services.domain_aggregation import DomainAggregationService


def extract_root_domain(domain: str) -> str:
    """Extract root domain."""
    if not domain:
        return ""
    parts = domain.lower().strip().split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return domain


def migrate_task_domains(db, task_id: int, tenant_id: int) -> tuple[int, int]:
    """Migrate data for a single task. Returns (domain_count, ip_count)."""
    print(f"  Migrating task {task_id}...")

    service = DomainAggregationService(db)
    domain_map = {}  # name -> Domain
    created_domains = 0
    created_ips = 0

    # Get subfinder assets for this task
    subfinder_assets = db.query(SubfinderAsset).filter(
        SubfinderAsset.tenant_id == tenant_id,
        SubfinderAsset.task_id == task_id
    ).all()

    # Create Domain records from subfinder
    for sf in subfinder_assets:
        domain_name = (sf.domain or "").lower().strip()
        if not domain_name or domain_name in domain_map:
            continue

        root = extract_root_domain(domain_name)

        # Check if already exists
        existing = db.query(Domain).filter(
            Domain.tenant_id == tenant_id,
            Domain.task_id == task_id,
            Domain.name == domain_name,
        ).first()

        if existing:
            domain_map[domain_name] = existing
            continue

        try:
            domain = service.create_domain(
                tenant_id=tenant_id,
                task_id=task_id,
                name=domain_name,
                root_domain=root,
                discovered_by="subfinder",
            )
            domain_map[domain_name] = domain
            created_domains += 1
        except Exception as e:
            print(f"    Warning: Failed to create domain {domain_name}: {e}")
            db.rollback()
            continue

    # Also create domains from FofaAsset/HunterAsset that might not be in subfinder
    for AssetClass in [FofaAsset, HunterAsset]:
        assets = db.query(AssetClass).filter(
            AssetClass.tenant_id == tenant_id,
            AssetClass.task_id == task_id,
        ).all()

        for asset in assets:
            if not asset.domain:
                continue
            domain_name = asset.domain.lower().strip()
            if domain_name in domain_map:
                continue

            root = extract_root_domain(domain_name)

            # Check if already exists
            existing = db.query(Domain).filter(
                Domain.tenant_id == tenant_id,
                Domain.task_id == task_id,
                Domain.name == domain_name,
            ).first()

            if existing:
                domain_map[domain_name] = existing
                continue

            try:
                domain = service.create_domain(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    name=domain_name,
                    root_domain=root,
                    discovered_by="fofa" if AssetClass == FofaAsset else "hunter",
                )
                domain_map[domain_name] = domain
                created_domains += 1
            except Exception as e:
                print(f"    Warning: Failed to create domain {domain_name}: {e}")
                db.rollback()
                continue

    # Create DomainIP records from FofaAsset/HunterAsset
    for AssetClass, source_name in [(FofaAsset, "fofa"), (HunterAsset, "hunter")]:
        assets = db.query(AssetClass).filter(
            AssetClass.tenant_id == tenant_id,
            AssetClass.task_id == task_id,
        ).all()

        for asset in assets:
            if not asset.domain or not asset.ip_address or not asset.port:
                continue

            domain = domain_map.get(asset.domain.lower().strip())
            if not domain:
                continue

            try:
                service.create_or_update_domain_ip(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    domain_id=domain.id,
                    ip_address=asset.ip_address,
                    port=asset.port,
                    protocol=asset.protocol,
                    source=source_name,
                    product=asset.product,
                    banner=asset.data.get("banner") if asset.data else None,
                    raw_data=asset.data,
                )
                created_ips += 1
            except Exception as e:
                print(f"    Warning: Failed to create IP for {asset.domain}: {e}")
                db.rollback()
                continue

    # Update domain stats
    for domain in domain_map.values():
        try:
            service.update_domain_stats(domain.id)
            domain.scan_status = "completed"
            db.commit()
        except Exception as e:
            print(f"    Warning: Failed to update stats for {domain.name}: {e}")
            db.rollback()

    print(f"    Created {created_domains} domains, {created_ips} IPs")
    return created_domains, created_ips


def main():
    print("Starting migration to domain-driven schema...")
    print(f"Database: {settings.database_url}")
    print()

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get all unique task IDs from existing data
        task_ids = db.query(distinct(Asset.task_id)).filter(
            Asset.task_id.isnot(None)
        ).all()

        print(f"Found {len(task_ids)} tasks to migrate")
        print()

        total_domains = 0
        total_ips = 0

        for (task_id,) in task_ids:
            # Get tenant_id for this task
            asset = db.query(Asset).filter(Asset.task_id == task_id).first()
            if not asset:
                continue

            domains, ips = migrate_task_domains(db, task_id, asset.tenant_id)
            total_domains += domains
            total_ips += ips

        print()
        print("=" * 50)
        print("Migration completed!")
        print(f"Total domains created: {total_domains}")
        print(f"Total IPs created: {total_ips}")
        print("=" * 50)

    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
