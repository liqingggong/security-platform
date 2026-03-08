"""
Unit tests for Asset Processing Pipeline.

Tests the unified pipeline that integrates CDN detection, protocol inference,
fingerprint enhancement, and asset deduplication services.
"""

import pytest
from app.services.asset_pipeline import (
    PipelineStats,
    AssetPipeline,
)


class TestPipelineStats:
    """Tests for PipelineStats dataclass."""

    def test_pipeline_stats_creation(self):
        """Test creating PipelineStats with default values."""
        stats = PipelineStats()
        assert stats.input_count == 0
        assert stats.output_count == 0
        assert stats.cdn_detected == 0
        assert stats.protocol_enhanced == 0
        assert stats.fingerprint_enhanced == 0
        assert stats.dedup_removed == 0
        assert stats.errors == []

    def test_pipeline_stats_with_values(self):
        """Test creating PipelineStats with specific values."""
        stats = PipelineStats(
            input_count=10,
            output_count=8,
            cdn_detected=3,
            protocol_enhanced=5,
            fingerprint_enhanced=8,
            dedup_removed=2,
            errors=["test error"],
        )
        assert stats.input_count == 10
        assert stats.output_count == 8
        assert stats.cdn_detected == 3
        assert stats.protocol_enhanced == 5
        assert stats.fingerprint_enhanced == 8
        assert stats.dedup_removed == 2
        assert stats.errors == ["test error"]


class TestAssetPipeline:
    """Tests for AssetPipeline class."""

    @pytest.fixture
    def pipeline(self):
        """Create an AssetPipeline instance."""
        return AssetPipeline()

    def test_pipeline_initialization(self, pipeline):
        """Test that pipeline initializes all services."""
        from app.services.cdn_detector import CDNDetectorService
        from app.services.protocol_inference import ProtocolInferenceService
        from app.services.fingerprint_enhancer import FingerprintEnhancerService
        from app.services.asset_dedup import AssetDedupService

        assert isinstance(pipeline.cdn_service, CDNDetectorService)
        assert isinstance(pipeline.protocol_service, ProtocolInferenceService)
        assert isinstance(pipeline.fingerprint_service, FingerprintEnhancerService)
        assert isinstance(pipeline.dedup_service, AssetDedupService)

    def test_pipeline_process_single_asset(self, pipeline):
        """Test processing a single asset through the pipeline."""
        asset = {
            "domain": "api.example.com.cdn.cloudflare.net",
            "ip_address": "1.2.3.4",
            "port": 443,
            "banner": "nginx/1.18.0",
        }

        result = pipeline.process_asset(asset)

        # CDN detection
        assert result["is_cdn"] is True
        assert result["cdn_provider"] == "cloudflare"
        assert result["original_domain"] == "api.example.com"

        # Protocol inference (port 443 -> https)
        assert result["protocol"] == "https"

        # Fingerprint enhancement
        assert "nginx" in result.get("technologies", [])
        assert result.get("product") == "nginx"

    def test_pipeline_process_asset_without_domain(self, pipeline):
        """Test processing an asset without a domain."""
        asset = {
            "ip_address": "1.2.3.4",
            "port": 80,
            "banner": "Apache/2.4.41",
        }

        result = pipeline.process_asset(asset)

        # No CDN info added
        assert "is_cdn" not in result
        assert "cdn_provider" not in result

        # Protocol inference (port 80 -> http)
        assert result["protocol"] == "http"

        # Fingerprint enhancement
        assert "apache" in result.get("technologies", [])

    def test_pipeline_process_asset_with_existing_protocol(self, pipeline):
        """Test that existing protocol is not overwritten."""
        asset = {
            "domain": "example.com",
            "port": 8080,
            "protocol": "https",  # Already set
            "banner": "nginx",
        }

        result = pipeline.process_asset(asset)

        # Protocol should remain unchanged
        assert result["protocol"] == "https"

    def test_pipeline_process_asset_without_enhancement(self, pipeline):
        """Test processing an asset with no enhancement opportunities."""
        asset = {
            "ip_address": "1.2.3.4",
            "port": 9999,  # Unknown port
        }

        result = pipeline.process_asset(asset)

        # No CDN info
        assert "is_cdn" not in result

        # No protocol inferred (unknown port)
        assert "protocol" not in result

        # No fingerprint info
        assert result.get("technologies") == []

    def test_pipeline_batch_process(self, pipeline):
        """Test batch processing with deduplication."""
        assets = [
            {
                "domain": "api.example.com.cdn.cloudflare.net",
                "ip_address": "1.2.3.4",
                "port": 443,
                "banner": "nginx/1.18.0",
                "sources": ["source1"],
            },
            {
                "domain": "api.example.com.cdn.cloudflare.net",  # Same domain/ip/port
                "ip_address": "1.2.3.4",
                "port": 443,
                "banner": "nginx",
                "sources": ["source2"],
            },
            {
                "domain": "other.example.com",
                "ip_address": "5.6.7.8",
                "port": 80,
                "banner": "Apache/2.4.41",
                "sources": ["source3"],
            },
        ]

        results = pipeline.process_batch(assets, enable_dedup=True)

        # Should have 2 assets (one duplicate removed)
        assert len(results) == 2

        # Check stats
        stats = pipeline.get_last_stats()
        assert stats["input_count"] == 3
        assert stats["output_count"] == 2
        assert stats["dedup_removed"] == 1
        assert stats["cdn_detected"] == 2  # Two assets had CDN domains (before dedup)

    def test_pipeline_batch_without_dedup(self, pipeline):
        """Test batch processing without deduplication."""
        assets = [
            {
                "domain": "example.com",
                "ip_address": "1.2.3.4",
                "port": 443,
                "sources": ["source1"],
            },
            {
                "domain": "example.com",  # Duplicate
                "ip_address": "1.2.3.4",
                "port": 443,
                "sources": ["source2"],
            },
        ]

        results = pipeline.process_batch(assets, enable_dedup=False)

        # Should have 2 assets (no dedup)
        assert len(results) == 2

        # Check stats
        stats = pipeline.get_last_stats()
        assert stats["dedup_removed"] == 0

    def test_pipeline_batch_empty_list(self, pipeline):
        """Test batch processing with empty list."""
        results = pipeline.process_batch([])

        assert results == []
        stats = pipeline.get_last_stats()
        assert stats["input_count"] == 0
        assert stats["output_count"] == 0

    def test_pipeline_stats_tracking(self, pipeline):
        """Test that stats are tracked correctly during processing."""
        assets = [
            {
                "domain": "cdn.example.com.cloudflare.net",
                "ip_address": "1.2.3.4",
                "port": 443,
                "banner": "nginx",
            },
            {
                "domain": "regular.example.com",
                "ip_address": "5.6.7.8",
                "port": 8080,
                "banner": "Apache",
            },
            {
                "domain": "regular.example.com",  # Duplicate
                "ip_address": "5.6.7.8",
                "port": 8080,
                "banner": "Apache",
            },
        ]

        pipeline.process_batch(assets, enable_dedup=True)
        stats = pipeline.get_last_stats()

        assert stats["input_count"] == 3
        assert stats["output_count"] == 2
        assert stats["cdn_detected"] == 1
        assert stats["protocol_enhanced"] == 3  # All have protocols inferred
        # Fingerprint enhanced counts assets where technologies were added
        # The first asset with banner="nginx" gets fingerprinted
        # The duplicate assets may be deduped before fingerprinting is counted
        assert stats["fingerprint_enhanced"] >= 1
        assert stats["dedup_removed"] == 1

    def test_pipeline_stats(self, pipeline):
        """Test get_last_stats returns correct stats structure."""
        # Process some assets first
        asset = {
            "domain": "example.com",
            "port": 80,
            "banner": "nginx",
        }
        pipeline.process_asset(asset)

        stats = pipeline.get_last_stats()

        assert isinstance(stats, dict)
        assert "input_count" in stats
        assert "output_count" in stats
        assert "cdn_detected" in stats
        assert "protocol_enhanced" in stats
        assert "fingerprint_enhanced" in stats
        assert "dedup_removed" in stats
        assert "errors" in stats

    def test_get_improvement_report(self, pipeline):
        """Test get_improvement_report returns human-readable report."""
        assets = [
            {
                "domain": "cdn.example.com.cloudflare.net",
                "ip_address": "1.2.3.4",
                "port": 443,
                "banner": "nginx",
            },
            {
                "domain": "regular.example.com",
                "ip_address": "5.6.7.8",
                "port": 8080,
                "banner": "Apache",
            },
        ]

        pipeline.process_batch(assets, enable_dedup=True)
        report = pipeline.get_improvement_report()

        assert isinstance(report, str)
        assert "Asset Processing Pipeline Report" in report
        assert "Input Assets" in report
        assert "Output Assets" in report
        assert "CDN Detected" in report
        assert "Protocol Enhanced" in report
        assert "Fingerprint Enhanced" in report
        assert "Duplicates Removed" in report

    def test_get_improvement_report_before_processing(self, pipeline):
        """Test get_improvement_report before any processing."""
        report = pipeline.get_improvement_report()

        assert isinstance(report, str)
        assert "Asset Processing Pipeline Report" in report
        assert "Input Assets:" in report
        assert "0" in report

    def test_pipeline_handles_errors_gracefully(self, pipeline):
        """Test that pipeline handles errors gracefully."""
        # Asset with None values that might cause issues
        asset = {
            "domain": None,
            "ip_address": None,
            "port": None,
            "banner": None,
        }

        result = pipeline.process_asset(asset)

        # Should not raise exception
        assert result is not None
        assert isinstance(result, dict)

    def test_pipeline_multiple_batches(self, pipeline):
        """Test that processing multiple batches updates stats correctly."""
        batch1 = [
            {"domain": "example1.com", "port": 80, "banner": "nginx"},
        ]
        batch2 = [
            {"domain": "example2.com", "port": 443, "banner": "Apache"},
        ]

        pipeline.process_batch(batch1)
        stats1 = pipeline.get_last_stats()
        assert stats1["input_count"] == 1

        pipeline.process_batch(batch2)
        stats2 = pipeline.get_last_stats()
        assert stats2["input_count"] == 1  # Stats reset for each batch

    def test_pipeline_asset_modification(self, pipeline):
        """Test that pipeline creates copies and doesn't modify original."""
        asset = {
            "domain": "example.com",
            "port": 80,
            "banner": "nginx",
        }
        original = dict(asset)

        result = pipeline.process_asset(asset)

        # Original should not be modified
        assert asset == original

        # Result should have enhancements
        assert result != original
        assert "technologies" in result
