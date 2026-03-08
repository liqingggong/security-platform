"""
Unit tests for Asset Deduplication Service.

Tests the asset deduplication logic based on (domain, ip, port) triplet
and merging of source information for duplicate assets.
"""

import pytest
from app.services.asset_dedup import (
    generate_asset_key,
    AssetDedupService,
)


class TestGenerateAssetKey:
    """Tests for generate_asset_key function."""

    def test_generate_key_with_all_fields(self):
        """Test key generation with all fields present."""
        asset = {
            "domain": "example.com",
            "ip_address": "192.168.1.1",
            "port": 80
        }
        assert generate_asset_key(asset) == "example.com|192.168.1.1|80"

    def test_generate_key_with_none_domain(self):
        """Test key generation with None domain."""
        asset = {
            "domain": None,
            "ip_address": "192.168.1.1",
            "port": 443
        }
        assert generate_asset_key(asset) == "|192.168.1.1|443"

    def test_generate_key_with_none_ip(self):
        """Test key generation with None ip_address."""
        asset = {
            "domain": "example.com",
            "ip_address": None,
            "port": 8080
        }
        assert generate_asset_key(asset) == "example.com||8080"

    def test_generate_key_with_none_port(self):
        """Test key generation with None port."""
        asset = {
            "domain": "example.com",
            "ip_address": "192.168.1.1",
            "port": None
        }
        assert generate_asset_key(asset) == "example.com|192.168.1.1|0"

    def test_generate_key_with_all_none(self):
        """Test key generation with all fields None."""
        asset = {
            "domain": None,
            "ip_address": None,
            "port": None
        }
        assert generate_asset_key(asset) == "||0"

    def test_generate_key_with_missing_fields(self):
        """Test key generation with missing fields."""
        asset = {}
        assert generate_asset_key(asset) == "||0"

    def test_generate_key_with_partial_fields(self):
        """Test key generation with only some fields."""
        asset = {"ip_address": "10.0.0.1"}
        assert generate_asset_key(asset) == "|10.0.0.1|0"


class TestAssetDedupServiceMergeAssetSources:
    """Tests for source merging logic."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_merge_sources_lists(self, service):
        """Test merging sources lists."""
        primary = {"sources": ["fofa"]}
        other = {"sources": ["hunter"]}
        result = service._merge_assets(primary, other)
        assert sorted(result["sources"]) == ["fofa", "hunter"]

    def test_merge_sources_avoids_duplicates(self, service):
        """Test merging sources avoids duplicates."""
        primary = {"sources": ["fofa", "hunter"]}
        other = {"sources": ["hunter", "shodan"]}
        result = service._merge_assets(primary, other)
        assert sorted(result["sources"]) == ["fofa", "hunter", "shodan"]

    def test_merge_discovered_by(self, service):
        """Test merging discovered_by dict."""
        primary = {
            "discovered_by": {
                "fofa": {"first_seen": "2024-01-01", "count": 5}
            }
        }
        other = {
            "discovered_by": {
                "hunter": {"first_seen": "2024-01-02", "count": 3}
            }
        }
        result = service._merge_assets(primary, other)
        assert "fofa" in result["discovered_by"]
        assert "hunter" in result["discovered_by"]
        assert result["discovered_by"]["fofa"]["count"] == 5
        assert result["discovered_by"]["hunter"]["count"] == 3

    def test_merge_discovered_by_combine_counts(self, service):
        """Test merging discovered_by combines counts for same source."""
        primary = {
            "discovered_by": {
                "fofa": {"first_seen": "2024-01-01", "count": 5}
            }
        }
        other = {
            "discovered_by": {
                "fofa": {"first_seen": "2024-01-02", "count": 3}
            }
        }
        result = service._merge_assets(primary, other)
        assert result["discovered_by"]["fofa"]["count"] == 8

    def test_merge_data_dict(self, service):
        """Test merging data dict."""
        primary = {"data": {"fofa": {"title": "Test"}}}
        other = {"data": {"hunter": {"banner": "Apache"}}}
        result = service._merge_assets(primary, other)
        assert "fofa" in result["data"]
        assert "hunter" in result["data"]

    def test_fill_missing_product(self, service):
        """Test filling missing product from other asset."""
        primary = {"product": None}
        other = {"product": "Apache"}
        result = service._merge_assets(primary, other)
        assert result["product"] == "Apache"

    def test_fill_missing_banner(self, service):
        """Test filling missing banner from other asset."""
        primary = {"banner": None}
        other = {"banner": "Apache/2.4.41"}
        result = service._merge_assets(primary, other)
        assert result["banner"] == "Apache/2.4.41"

    def test_keep_existing_product(self, service):
        """Test keeping existing product when present."""
        primary = {"product": "Nginx"}
        other = {"product": "Apache"}
        result = service._merge_assets(primary, other)
        assert result["product"] == "Nginx"


class TestAssetDedupServiceDedupAssets:
    """Tests for dedup_assets method."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_dedup_no_duplicates(self, service):
        """Test deduplication with no duplicates."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["hunter"]},
        ]
        result = service.dedup_assets(assets)
        assert len(result) == 2

    def test_dedup_with_duplicates(self, service):
        """Test deduplication merges duplicates."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
        ]
        result = service.dedup_assets(assets)
        assert len(result) == 1
        assert sorted(result[0]["sources"]) == ["fofa", "hunter"]

    def test_dedup_marks_aggregated(self, service):
        """Test deduplication marks assets as aggregated."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
        ]
        result = service.dedup_assets(assets)
        assert result[0]["is_aggregated"] is True
        assert result[0]["aggregated_count"] == 2

    def test_dedup_no_aggregate_single_asset(self, service):
        """Test single assets are not marked aggregated."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
        ]
        result = service.dedup_assets(assets)
        assert result[0].get("is_aggregated") is not True
        assert result[0].get("aggregated_count") is None

    def test_dedup_empty_list(self, service):
        """Test deduplication with empty list."""
        result = service.dedup_assets([])
        assert result == []

    def test_dedup_multiple_groups(self, service):
        """Test deduplication with multiple duplicate groups."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["fofa"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["shodan"]},
        ]
        result = service.dedup_assets(assets)
        assert len(result) == 2
        for asset in result:
            assert asset["is_aggregated"] is True
            assert asset["aggregated_count"] == 2


class TestAssetDedupServiceSelectPrimary:
    """Tests for primary asset selection."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_select_primary_by_product(self, service):
        """Test primary selection prioritizes product."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": None},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache"},
        ]
        primary = service._select_primary(assets)
        assert primary["product"] == "Apache"

    def test_select_primary_by_banner(self, service):
        """Test primary selection prioritizes banner when product equal."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": None},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": "Apache/2.4"},
        ]
        primary = service._select_primary(assets)
        assert primary["banner"] == "Apache/2.4"

    def test_select_primary_by_protocol(self, service):
        """Test primary selection prioritizes protocol."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": "Apache/2.4", "protocol": None},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": "Apache/2.4", "protocol": "http"},
        ]
        primary = service._select_primary(assets)
        assert primary["protocol"] == "http"

    def test_select_primary_by_data(self, service):
        """Test primary selection prioritizes data presence."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": "Apache/2.4", "protocol": "http", "data": {}},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache", "banner": "Apache/2.4", "protocol": "http", "data": {"key": "value"}},
        ]
        primary = service._select_primary(assets)
        assert primary["data"] == {"key": "value"}

    def test_select_primary_empty_list(self, service):
        """Test primary selection with empty list."""
        primary = service._select_primary([])
        assert primary is None

    def test_select_primary_single_asset(self, service):
        """Test primary selection with single asset."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "product": "Apache"},
        ]
        primary = service._select_primary(assets)
        assert primary["product"] == "Apache"


class TestAssetDedupServiceCalculateDuplicateRate:
    """Tests for calculate_duplicate_rate method."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_calculate_rate_no_duplicates(self, service):
        """Test rate calculation with no duplicates."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443},
        ]
        rate = service.calculate_duplicate_rate(assets)
        assert rate == 0.0

    def test_calculate_rate_all_duplicates(self, service):
        """Test rate calculation with all duplicates."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
        ]
        rate = service.calculate_duplicate_rate(assets)
        assert rate == 0.5  # 1 unique from 2 total = 50% duplicate rate

    def test_calculate_rate_partial_duplicates(self, service):
        """Test rate calculation with partial duplicates."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["fofa"]},
        ]
        rate = service.calculate_duplicate_rate(assets)
        # 2 unique from 3 total = 1 duplicate out of 3 = 33.3% duplicate rate
        assert rate == pytest.approx(0.333, rel=0.01)

    def test_calculate_rate_empty_list(self, service):
        """Test rate calculation with empty list."""
        rate = service.calculate_duplicate_rate([])
        assert rate == 0.0

    def test_calculate_rate_single_asset(self, service):
        """Test rate calculation with single asset."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80},
        ]
        rate = service.calculate_duplicate_rate(assets)
        assert rate == 0.0


class TestAssetDedupServiceFindDuplicates:
    """Tests for find_duplicates method."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_find_duplicates_none(self, service):
        """Test finding duplicates with no duplicates."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443},
        ]
        duplicates = service.find_duplicates(assets)
        assert duplicates == {}

    def test_find_duplicates_single_group(self, service):
        """Test finding duplicates with single duplicate group."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
        ]
        duplicates = service.find_duplicates(assets)
        assert len(duplicates) == 1
        key = "example.com|1.1.1.1|80"
        assert key in duplicates
        assert len(duplicates[key]) == 2

    def test_find_duplicates_multiple_groups(self, service):
        """Test finding duplicates with multiple groups."""
        assets = [
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
            {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["fofa"]},
            {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443, "sources": ["shodan"]},
        ]
        duplicates = service.find_duplicates(assets)
        assert len(duplicates) == 2
        assert len(duplicates["a.com|1.1.1.1|80"]) == 2
        assert len(duplicates["b.com|2.2.2.2|443"]) == 2

    def test_find_duplicates_empty_list(self, service):
        """Test finding duplicates with empty list."""
        duplicates = service.find_duplicates([])
        assert duplicates == {}

    def test_find_duplicates_single_asset(self, service):
        """Test finding duplicates with single asset."""
        assets = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80},
        ]
        duplicates = service.find_duplicates(assets)
        assert duplicates == {}


class TestAssetDedupServiceMergeGroup:
    """Tests for _merge_group method."""

    @pytest.fixture
    def service(self):
        """Create an AssetDedupService instance."""
        return AssetDedupService()

    def test_merge_group_single_asset(self, service):
        """Test merging group with single asset."""
        group = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"]},
        ]
        result = service._merge_group(group)
        assert result["sources"] == ["fofa"]
        assert result.get("is_aggregated") is not True

    def test_merge_group_multiple_assets(self, service):
        """Test merging group with multiple assets."""
        group = [
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["fofa"], "product": None},
            {"domain": "example.com", "ip_address": "1.1.1.1", "port": 80, "sources": ["hunter"], "product": "Apache"},
        ]
        result = service._merge_group(group)
        assert sorted(result["sources"]) == ["fofa", "hunter"]
        assert result["product"] == "Apache"
        assert result["is_aggregated"] is True
        assert result["aggregated_count"] == 2

    def test_merge_group_empty(self, service):
        """Test merging empty group."""
        result = service._merge_group([])
        assert result is None
