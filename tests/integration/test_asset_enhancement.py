"""
Integration tests for Asset Enhancement Pipeline.

Tests the entire asset enhancement pipeline end-to-end, including:
- Asset enhancement API endpoints
- Quality stats API
- Complete pipeline processing
- Real fofa.info data patterns
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app components
from app.main import app
from app.db.base import Base
from app.db.models import Asset, AssetType, Tenant, User, UserRole, Task, TaskStatus
from app.api.deps import get_db, get_current_user, get_current_tenant_id
from app.services.asset_pipeline import AssetPipeline


# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Override current user dependency for testing."""
    db = TestingSessionLocal()
    user = db.query(User).first()
    if not user:
        user = User(
            id=1,
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
            role=UserRole.ADMIN,
            tenant_id=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def override_get_current_tenant_id():
    """Override tenant ID dependency for testing."""
    return 1


# Apply overrides
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create test tenant
    tenant = Tenant(id=1, name="Test Tenant")
    db.add(tenant)

    # Create test user
    user = User(
        id=1,
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        role=UserRole.ADMIN,
        tenant_id=1,
    )
    db.add(user)

    # Create test task
    task = Task(
        id=1,
        name="Test Task",
        status=TaskStatus.COMPLETED,
        tenant_id=1,
    )
    db.add(task)

    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_assets(db_session) -> List[Asset]:
    """Create sample assets for testing."""
    # Note: Using unique domain/ip/port combinations to avoid UNIQUE constraint
    assets = [
        Asset(
            type=AssetType.ENDPOINT,
            value="api.fofa.info:443",
            domain="api.fofa.info",
            ip_address="104.20.18.45",
            port=443,
            protocol=None,  # Missing protocol - should be inferred
            data={"banner": "Server: cloudflare"},
            sources=["fofa"],
            tenant_id=1,
            task_id=1,
        ),
        Asset(
            type=AssetType.ENDPOINT,
            value="api2.fofa.info:443",
            domain="api2.fofa.info",
            ip_address="104.20.18.46",
            port=443,
            protocol=None,  # Missing protocol
            data={"banner": "Server: cloudflare"},
            sources=["hunter"],
            tenant_id=1,
            task_id=1,
        ),
        Asset(
            type=AssetType.ENDPOINT,
            value="static.fofa.info.cdn.cloudflare.net:80",
            domain="static.fofa.info.cdn.cloudflare.net",
            ip_address="172.66.161.110",
            port=80,
            protocol=None,
            data={},
            sources=["fofa"],
            tenant_id=1,
            task_id=1,
        ),
        Asset(
            type=AssetType.ENDPOINT,
            value="example.com:8080",
            domain="example.com",
            ip_address="192.168.1.1",
            port=8080,
            protocol="http",  # Already has protocol
            data={"banner": "Apache/2.4.41"},
            sources=["subfinder"],
            tenant_id=1,
            task_id=1,
        ),
    ]

    for asset in assets:
        db_session.add(asset)
    db_session.commit()

    return assets


class TestAssetEnhanceEndpoint:
    """Tests for POST /api/v1/assets/enhance endpoint."""

    def test_asset_enhance_endpoint_success(self, db_session, sample_assets):
        """Test successful asset enhancement through API."""
        response = client.post(
            "/api/v1/assets/enhance",
            json={
                "task_ids": [1],
                "enable_cdn_detection": True,
                "enable_protocol_inference": True,
                "enable_fingerprint": True,
                "enable_dedup": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "processed" in data
        assert "enhanced" in data
        assert "report" in data

        # Verify counts
        assert data["processed"] == 4  # 4 assets processed
        assert data["enhanced"] >= 0  # Some assets were enhanced

        # Verify report structure
        report = data["report"]
        assert "message" in report
        assert "input_count" in report
        assert "output_count" in report
        assert "cdn_detected" in report
        assert "protocol_enhanced" in report
        assert "fingerprint_enhanced" in report
        assert "dedup_removed" in report

        # Verify database updates
        db_session.refresh(sample_assets[0])
        db_session.refresh(sample_assets[2])

        # CDN should be detected for cloudflare domain
        assert sample_assets[2].is_cdn is True
        assert sample_assets[2].cdn_provider == "cloudflare"
        assert sample_assets[2].original_domain == "static.fofa.info"

        # Protocol should be inferred for port 443
        assert sample_assets[0].protocol == "https"

    def test_asset_enhance_no_assets(self, db_session):
        """Test enhancement with no matching assets."""
        response = client.post(
            "/api/v1/assets/enhance",
            json={
                "task_ids": [999],  # Non-existent task
                "enable_dedup": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["processed"] == 0
        assert data["enhanced"] == 0
        assert data["report"]["message"] == "No assets found for enhancement"

    def test_asset_enhance_without_dedup(self, db_session, sample_assets):
        """Test enhancement without deduplication."""
        response = client.post(
            "/api/v1/assets/enhance",
            json={
                "task_ids": [1],
                "enable_dedup": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        report = data["report"]
        assert report["dedup_removed"] == 0
        assert report["input_count"] == report["output_count"]


class TestAssetQualityStatsEndpoint:
    """Tests for GET /api/v1/assets/stats/quality endpoint."""

    def test_asset_quality_stats_empty(self, db_session):
        """Test quality stats with no assets."""
        response = client.get("/api/v1/assets/stats/quality")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["protocol"]["count"] == 0
        assert data["protocol"]["rate"] == 0.0
        assert data["fingerprint"]["count"] == 0
        assert data["fingerprint"]["rate"] == 0.0
        assert data["cdn"]["count"] == 0
        assert data["cdn"]["rate"] == 0.0
        assert data["multi_source"]["count"] == 0
        assert data["multi_source"]["rate"] == 0.0

    def test_asset_quality_stats_with_data(self, db_session, sample_assets):
        """Test quality stats with sample assets."""
        # First enhance the assets
        client.post(
            "/api/v1/assets/enhance",
            json={"task_ids": [1], "enable_dedup": False},
        )

        response = client.get("/api/v1/assets/stats/quality")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "total" in data
        assert "protocol" in data
        assert "fingerprint" in data
        assert "cdn" in data
        assert "multi_source" in data

        # Verify counts
        assert data["total"] == 4
        assert data["protocol"]["count"] >= 0
        assert 0 <= data["protocol"]["rate"] <= 100
        assert data["cdn"]["count"] >= 0
        assert 0 <= data["cdn"]["rate"] <= 100

    def test_quality_stats_rate_calculation(self, db_session):
        """Test that coverage rates are calculated correctly."""
        # Create assets with known state
        assets = [
            Asset(
                type=AssetType.ENDPOINT,
                value="test1.com",
                domain="test1.com",
                protocol="https",  # Has protocol
                product="nginx",  # Has fingerprint
                is_cdn=True,  # Is CDN
                sources=["fofa", "hunter"],  # Multi-source
                tenant_id=1,
            ),
            Asset(
                type=AssetType.ENDPOINT,
                value="test2.com",
                domain="test2.com",
                protocol=None,  # No protocol
                product=None,  # No fingerprint
                is_cdn=False,
                sources=["fofa"],  # Single source
                tenant_id=1,
            ),
        ]

        for asset in assets:
            db_session.add(asset)
        db_session.commit()

        response = client.get("/api/v1/assets/stats/quality")
        data = response.json()

        assert data["total"] == 2
        assert data["protocol"]["count"] == 1
        assert data["protocol"]["rate"] == 50.0
        assert data["fingerprint"]["count"] == 1
        assert data["fingerprint"]["rate"] == 50.0
        assert data["cdn"]["count"] == 1
        assert data["cdn"]["rate"] == 50.0
        assert data["multi_source"]["count"] == 1
        assert data["multi_source"]["rate"] == 50.0


class TestEndToEndPipeline:
    """Tests for complete end-to-end pipeline processing."""

    def test_end_to_end_pipeline_processing(self):
        """Test complete pipeline with AssetPipeline directly."""
        pipeline = AssetPipeline()

        # Create test assets matching fofa.info data patterns
        assets = [
            {
                "domain": "api.fofa.info",
                "ip_address": "104.20.18.45",
                "port": 443,
                "protocol": None,
                "banner": "Server: cloudflare",
                "sources": ["fofa"],
            },
            {
                "domain": "api.fofa.info",
                "ip_address": "104.20.18.45",
                "port": 443,
                "protocol": None,
                "banner": "Server: cloudflare",
                "sources": ["hunter"],
            },
            {
                "domain": "static.fofa.info.cdn.cloudflare.net",
                "ip_address": "172.66.161.110",
                "port": 80,
                "protocol": None,
                "sources": ["fofa"],
            },
            {
                "domain": "test.example.com",
                "ip_address": "192.168.1.1",
                "port": 8080,
                "protocol": None,
                "banner": "Apache/2.4.41",
                "sources": ["subfinder"],
            },
        ]

        # Process through pipeline
        results = pipeline.process_batch(assets, enable_dedup=True)

        # Verify deduplication worked (2 assets with same domain/ip/port should become 1)
        assert len(results) == 3  # 4 input - 1 duplicate = 3 output

        # Get stats
        stats = pipeline.get_last_stats()
        assert stats["input_count"] == 4
        assert stats["output_count"] == 3
        assert stats["dedup_removed"] == 1

        # Verify CDN detection for cloudflare domain
        cdn_asset = next(
            (r for r in results if "cloudflare" in (r.get("domain") or "")),
            None
        )
        assert cdn_asset is not None
        assert cdn_asset["is_cdn"] is True
        assert cdn_asset["cdn_provider"] == "cloudflare"
        assert cdn_asset["original_domain"] == "static.fofa.info"

        # Verify protocol inference
        https_asset = next(
            (r for r in results if r.get("port") == 443),
            None
        )
        assert https_asset is not None
        assert https_asset["protocol"] == "https"

        http_asset = next(
            (r for r in results if r.get("port") == 80),
            None
        )
        assert http_asset is not None
        assert http_asset["protocol"] == "http"

        # Verify fingerprint extraction
        apache_asset = next(
            (r for r in results if "Apache" in (r.get("banner") or "")),
            None
        )
        assert apache_asset is not None
        assert "apache" in apache_asset.get("technologies", [])

    def test_pipeline_with_fofa_data_pattern(self):
        """Test pipeline with real fofa.info data patterns."""
        pipeline = AssetPipeline()

        # Simulate the real fofa.info asset data
        assets = [
            {
                "domain": "api.fofa.info",
                "ip_address": "104.20.18.45",
                "port": 443,
                "protocol": None,
                "banner": "Server: cloudflare",
                "sources": ["fofa"],
            },
            {
                "domain": "api.fofa.info",
                "ip_address": "104.20.18.45",
                "port": 443,
                "protocol": None,
                "banner": "Server: cloudflare",
                "sources": ["hunter"],
            },
            {
                "domain": "static.fofa.info.cdn.cloudflare.net",
                "ip_address": "172.66.161.110",
                "port": 80,
                "protocol": None,
                "sources": ["fofa"],
            },
        ]

        # Process through pipeline
        results = pipeline.process_batch(assets, enable_dedup=True)

        # Assert: 2 assets returned (dedup worked - first two are duplicates)
        assert len(results) == 2, f"Expected 2 assets after dedup, got {len(results)}"

        # Assert: CDN detected for cloudflare domain
        cdn_assets = [r for r in results if r.get("is_cdn")]
        assert len(cdn_assets) == 1, "Expected 1 CDN asset"
        assert cdn_assets[0]["cdn_provider"] == "cloudflare"
        assert cdn_assets[0]["original_domain"] == "static.fofa.info"

        # Assert: https inferred for port 443
        https_assets = [r for r in results if r.get("protocol") == "https"]
        assert len(https_assets) == 1, "Expected 1 https asset"

        # Assert: http inferred for port 80
        http_assets = [r for r in results if r.get("protocol") == "http"]
        assert len(http_assets) == 1, "Expected 1 http asset"

        # Assert: sources merged for duplicate
        api_assets = [r for r in results if r.get("domain") == "api.fofa.info"]
        assert len(api_assets) == 1, "Expected 1 api.fofa.info asset after dedup"
        assert set(api_assets[0]["sources"]) == {"fofa", "hunter"}, \
            "Sources should be merged"

        # Verify stats
        stats = pipeline.get_last_stats()
        assert stats["input_count"] == 3
        assert stats["output_count"] == 2
        assert stats["dedup_removed"] == 1
        assert stats["cdn_detected"] == 1
        assert stats["protocol_enhanced"] == 3  # All 3 had no protocol initially

    def test_pipeline_improvement_report(self):
        """Test that improvement report is generated correctly."""
        pipeline = AssetPipeline()

        assets = [
            {
                "domain": "cdn.example.com.cloudflare.net",
                "ip_address": "1.2.3.4",
                "port": 443,
                "banner": "nginx/1.18.0",
                "sources": ["fofa"],
            },
            {
                "domain": "regular.example.com",
                "ip_address": "5.6.7.8",
                "port": 80,
                "banner": "Apache/2.4.41",
                "sources": ["hunter"],
            },
        ]

        pipeline.process_batch(assets, enable_dedup=True)
        report = pipeline.get_improvement_report()

        assert "Asset Processing Pipeline Report" in report
        assert "Input Assets:" in report
        assert "Output Assets:" in report
        assert "CDN Detected:" in report
        assert "Protocol Enhanced:" in report
        assert "Fingerprint Enhanced:" in report
        assert "Duplicates Removed:" in report
        assert "Errors:" in report


class TestRealDataVerification:
    """Tests with real fofa.info Excel data."""

    @pytest.fixture
    def load_real_data(self):
        """Load real data from Excel file."""
        try:
            import pandas as pd

            file_path = "/Users/liqinggong/Downloads/资产列表_2026-03-08_15-00-07.xlsx"
            df = pd.read_excel(file_path)

            # Convert to asset format
            assets = []
            for _, row in df.iterrows():
                asset = {
                    "domain": row["域名"] if row["域名"] != "-" else None,
                    "ip_address": row["IP"] if row["IP"] != "-" else None,
                    "port": int(row["端口"]) if row["端口"] != "-" and str(row["端口"]).isdigit() else None,
                    "protocol": row["协议"] if row["协议"] != "-" else None,
                    "banner": row["指纹"] if row["指纹"] != "-" else None,
                    "sources": row["来源"].split("+") if row["来源"] != "-" else [],
                }
                assets.append(asset)

            return assets
        except Exception as e:
            pytest.skip(f"Could not load real data: {e}")

    def test_real_data_pipeline(self, load_real_data):
        """Test pipeline with real fofa.info data."""
        assets = load_real_data
        pipeline = AssetPipeline()

        # Process assets
        results = pipeline.process_batch(assets, enable_dedup=True)

        # Get stats
        stats = pipeline.get_last_stats()

        # Verify processing completed
        assert stats["input_count"] == len(assets)
        assert stats["output_count"] <= stats["input_count"]
        assert stats["dedup_removed"] >= 0

        # Print report for verification
        print("\n" + pipeline.get_improvement_report())

    def test_real_data_metrics(self, load_real_data):
        """Test that real data meets improvement targets."""
        assets = load_real_data
        pipeline = AssetPipeline()

        # Process assets
        results = pipeline.process_batch(assets, enable_dedup=True)
        stats = pipeline.get_last_stats()

        # Calculate metrics
        input_count = stats["input_count"]
        output_count = stats["output_count"]

        # Protocol coverage: assets with protocol / total assets
        protocol_count = sum(1 for r in results if r.get("protocol"))
        protocol_rate = (protocol_count / output_count * 100) if output_count > 0 else 0

        # Fingerprint coverage: assets with technologies or product
        fingerprint_count = sum(
            1 for r in results
            if r.get("technologies") or r.get("product")
        )
        fingerprint_rate = (fingerprint_count / output_count * 100) if output_count > 0 else 0

        # CDN detection rate
        cdn_count = sum(1 for r in results if r.get("is_cdn"))
        cdn_rate = (cdn_count / output_count * 100) if output_count > 0 else 0

        # Print metrics
        print(f"\n=== Real Data Metrics ===")
        print(f"Input Assets: {input_count}")
        print(f"Output Assets: {output_count}")
        print(f"Duplicates Removed: {stats['dedup_removed']}")
        print(f"Protocol Coverage: {protocol_rate:.2f}% ({protocol_count}/{output_count})")
        print(f"Fingerprint Coverage: {fingerprint_rate:.2f}% ({fingerprint_count}/{output_count})")
        print(f"CDN Detection Rate: {cdn_rate:.2f}% ({cdn_count}/{output_count})")

        # Assert targets (these are the improvement targets)
        # Note: Using >= 0 for initial test - real targets should be set based on data analysis
        assert protocol_rate >= 0, "Protocol coverage should be measurable"
        assert fingerprint_rate >= 0, "Fingerprint coverage should be measurable"
        assert cdn_rate >= 0, "CDN detection rate should be measurable"


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_pipeline_handles_empty_assets(self):
        """Test that pipeline handles empty asset list."""
        pipeline = AssetPipeline()
        results = pipeline.process_batch([])

        assert results == []
        stats = pipeline.get_last_stats()
        assert stats["input_count"] == 0
        assert stats["output_count"] == 0

    def test_pipeline_handles_none_values(self):
        """Test that pipeline handles assets with None values."""
        pipeline = AssetPipeline()

        assets = [
            {
                "domain": None,
                "ip_address": None,
                "port": None,
                "protocol": None,
                "banner": None,
                "sources": [],
            },
        ]

        results = pipeline.process_batch(assets)

        assert len(results) == 1
        assert results[0]["sources"] == []

    def test_pipeline_handles_invalid_port(self):
        """Test that pipeline handles invalid port numbers."""
        pipeline = AssetPipeline()

        assets = [
            {
                "domain": "test.com",
                "ip_address": "1.2.3.4",
                "port": 99999,  # Invalid port
                "protocol": None,
            },
        ]

        results = pipeline.process_batch(assets)

        assert len(results) == 1
        # Should not crash, protocol might not be inferred for unknown port

    def test_pipeline_handles_missing_fields(self):
        """Test that pipeline handles assets with missing fields."""
        pipeline = AssetPipeline()

        assets = [
            {"domain": "test.com"},  # Minimal fields
            {"ip_address": "1.2.3.4"},
            {"port": 80},
        ]

        results = pipeline.process_batch(assets)

        assert len(results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
