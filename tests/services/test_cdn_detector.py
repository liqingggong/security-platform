"""
Unit tests for CDN Detection and Association Service.

Tests the CDN detection logic for various CDN providers and
domain extraction from CDN domains.
"""

import pytest
from app.services.cdn_detector import (
    detect_cdn,
    CDNDetectorService,
    CDN_PATTERNS,
)


class TestDetectCdnFunction:
    """Tests for detect_cdn function."""

    def test_detect_cloudflare_cdn(self):
        """Test Cloudflare CDN domain detection."""
        assert detect_cdn("api.example.com.cdn.cloudflare.net") == "cloudflare"
        assert detect_cdn("static.example.com.cloudflare.net") == "cloudflare"
        assert detect_cdn("cdn.example.com.cloudflare-dns.com") == "cloudflare"

    def test_detect_aliyun_cdn(self):
        """Test Aliyun CDN domain detection."""
        assert detect_cdn("static.example.com.w.kunlunar.com") == "aliyun"
        assert detect_cdn("api.example.com.w.alikunlun.net") == "aliyun"
        assert detect_cdn("example.com.aliyuncs.com") == "aliyun"

    def test_detect_tencent_cdn(self):
        """Test Tencent CDN domain detection."""
        assert detect_cdn("static.example.com.tc.cdn") == "tencent"
        assert detect_cdn("api.example.com.cdn.dnsv1.com") == "tencent"

    def test_detect_baidu_cdn(self):
        """Test Baidu CDN domain detection."""
        assert detect_cdn("example.com.jomodns.com") == "baidu"
        assert detect_cdn("static.example.com.bdydns.net") == "baidu"

    def test_detect_huawei_cdn(self):
        """Test Huawei CDN domain detection."""
        assert detect_cdn("example.com.hc.cdn") == "huawei"
        assert detect_cdn("static.example.com.cdnhwc1.com") == "huawei"
        assert detect_cdn("api.example.com.cdnhwc123.com") == "huawei"

    def test_detect_wangsu_cdn(self):
        """Test Wangsu (ChinaNetCenter) CDN domain detection."""
        assert detect_cdn("example.com.wscdns.com") == "wangsu"
        assert detect_cdn("static.example.com.cdn20.com") == "wangsu"

    def test_detect_qiniu_cdn(self):
        """Test Qiniu CDN domain detection."""
        assert detect_cdn("example.com.qiniudns.com") == "qiniu"
        assert detect_cdn("static.example.com.clouddn.com") == "qiniu"

    def test_detect_aws_cdn(self):
        """Test AWS CloudFront CDN domain detection."""
        assert detect_cdn("example.com.cloudfront.net") == "aws"

    def test_no_cdn_detected(self):
        """Test that non-CDN domains return None."""
        assert detect_cdn("example.com") is None
        assert detect_cdn("www.example.com") is None
        assert detect_cdn("api.example.com") is None
        assert detect_cdn("sub.domain.example.com") is None

    def test_detect_cdn_none_input(self):
        """Test None input returns None."""
        assert detect_cdn(None) is None

    def test_detect_cdn_empty_string(self):
        """Test empty string returns None."""
        assert detect_cdn("") is None

    def test_detect_cdn_case_sensitivity(self):
        """Test that CDN detection is case-insensitive."""
        assert detect_cdn("EXAMPLE.COM.CLOUDFLARE.NET") == "cloudflare"
        assert detect_cdn("Example.Com.Cloudflare.Net") == "cloudflare"


class TestCDNDetectorService:
    """Tests for CDNDetectorService class."""

    @pytest.fixture
    def service(self):
        """Create a CDNDetectorService instance."""
        return CDNDetectorService()

    def test_detect_cdn_method(self, service):
        """Test the detect_cdn method of the service."""
        assert service.detect_cdn("api.example.com.cdn.cloudflare.net") == "cloudflare"
        assert service.detect_cdn("example.com") is None

    def test_extract_original_domain_from_cloudflare(self, service):
        """Test extracting original domain from Cloudflare CDN domains."""
        assert service.extract_original_domain("api.example.com.cdn.cloudflare.net") == "api.example.com"
        assert service.extract_original_domain("static.example.com.cloudflare.net") == "static.example.com"

    def test_extract_original_domain_from_aliyun(self, service):
        """Test extracting original domain from Aliyun CDN domains."""
        assert service.extract_original_domain("static.example.com.w.kunlunar.com") == "static.example.com"
        assert service.extract_original_domain("api.example.com.w.alikunlun.net") == "api.example.com"
        assert service.extract_original_domain("example.com.aliyuncs.com") == "example.com"

    def test_extract_original_domain_from_tencent(self, service):
        """Test extracting original domain from Tencent CDN domains."""
        assert service.extract_original_domain("static.example.com.tc.cdn") == "static.example.com"
        assert service.extract_original_domain("api.example.com.cdn.dnsv1.com") == "api.example.com"

    def test_extract_original_domain_from_baidu(self, service):
        """Test extracting original domain from Baidu CDN domains."""
        assert service.extract_original_domain("example.com.jomodns.com") == "example.com"
        assert service.extract_original_domain("static.example.com.bdydns.net") == "static.example.com"

    def test_extract_original_domain_from_huawei(self, service):
        """Test extracting original domain from Huawei CDN domains."""
        assert service.extract_original_domain("example.com.hc.cdn") == "example.com"
        assert service.extract_original_domain("static.example.com.cdnhwc1.com") == "static.example.com"

    def test_extract_original_domain_from_wangsu(self, service):
        """Test extracting original domain from Wangsu CDN domains."""
        assert service.extract_original_domain("example.com.wscdns.com") == "example.com"
        assert service.extract_original_domain("static.example.com.cdn20.com") == "static.example.com"

    def test_extract_original_domain_from_qiniu(self, service):
        """Test extracting original domain from Qiniu CDN domains."""
        assert service.extract_original_domain("example.com.qiniudns.com") == "example.com"
        assert service.extract_original_domain("static.example.com.clouddn.com") == "static.example.com"

    def test_extract_original_domain_from_aws(self, service):
        """Test extracting original domain from AWS CloudFront CDN domains."""
        assert service.extract_original_domain("example.com.cloudfront.net") == "example.com"

    def test_extract_original_domain_non_cdn(self, service):
        """Test extracting original domain from non-CDN domains returns the domain itself."""
        assert service.extract_original_domain("example.com") == "example.com"
        assert service.extract_original_domain("www.example.com") == "www.example.com"
        assert service.extract_original_domain("api.example.com") == "api.example.com"

    def test_extract_original_domain_none_input(self, service):
        """Test extract_original_domain with None input."""
        assert service.extract_original_domain(None) is None

    def test_extract_original_domain_empty_string(self, service):
        """Test extract_original_domain with empty string."""
        assert service.extract_original_domain("") == ""

    def test_normalize_cdn_domain_with_cdn(self, service):
        """Test normalize_cdn_domain with CDN domains."""
        result = service.normalize_cdn_domain("api.example.com.cdn.cloudflare.net")
        assert result["is_cdn"] is True
        assert result["cdn_provider"] == "cloudflare"
        assert result["original_domain"] == "api.example.com"

    def test_normalize_cdn_domain_without_cdn(self, service):
        """Test normalize_cdn_domain with non-CDN domains."""
        result = service.normalize_cdn_domain("example.com")
        assert result["is_cdn"] is False
        assert result["cdn_provider"] is None
        assert result["original_domain"] == "example.com"

    def test_normalize_cdn_domain_none_input(self, service):
        """Test normalize_cdn_domain with None input."""
        result = service.normalize_cdn_domain(None)
        assert result["is_cdn"] is False
        assert result["cdn_provider"] is None
        assert result["original_domain"] is None

    def test_normalize_cdn_domain_returns_dict(self, service):
        """Test that normalize_cdn_domain returns a dictionary with expected keys."""
        result = service.normalize_cdn_domain("example.com")
        assert isinstance(result, dict)
        assert "is_cdn" in result
        assert "cdn_provider" in result
        assert "original_domain" in result

    def test_batch_process_domains(self, service):
        """Test batch processing of domains."""
        domains = [
            "api.example.com.cdn.cloudflare.net",
            "static.example.com.w.kunlunar.com",
            "example.com",
            "www.test.com",
        ]
        results = service.batch_process(domains)

        assert len(results) == 4
        assert results[0]["is_cdn"] is True
        assert results[0]["cdn_provider"] == "cloudflare"
        assert results[0]["original_domain"] == "api.example.com"

        assert results[1]["is_cdn"] is True
        assert results[1]["cdn_provider"] == "aliyun"
        assert results[1]["original_domain"] == "static.example.com"

        assert results[2]["is_cdn"] is False
        assert results[2]["cdn_provider"] is None
        assert results[2]["original_domain"] == "example.com"

        assert results[3]["is_cdn"] is False
        assert results[3]["cdn_provider"] is None
        assert results[3]["original_domain"] == "www.test.com"

    def test_batch_process_empty_list(self, service):
        """Test batch processing with empty list."""
        results = service.batch_process([])
        assert results == []

    def test_batch_process_none_input(self, service):
        """Test batch processing with None input."""
        results = service.batch_process(None)
        assert results == []

    def test_build_cdn_mapping(self, service):
        """Test building CDN mapping from domains."""
        domains = [
            "api.example.com.cdn.cloudflare.net",
            "static.example.com.cdn.cloudflare.net",
            "cdn.example.com.w.kunlunar.com",
            "example.com",
            "www.test.com",
        ]
        mapping = service.build_cdn_mapping(domains)

        # Should have mappings for CDN domains
        assert "api.example.com" in mapping
        assert mapping["api.example.com"] == ["api.example.com.cdn.cloudflare.net"]

        assert "static.example.com" in mapping
        assert mapping["static.example.com"] == ["static.example.com.cdn.cloudflare.net"]

        assert "cdn.example.com" in mapping
        assert mapping["cdn.example.com"] == ["cdn.example.com.w.kunlunar.com"]

        # Non-CDN domains should not be in mapping
        assert "example.com" not in mapping
        assert "www.test.com" not in mapping

    def test_build_cdn_mapping_multiple_cdns_same_original(self, service):
        """Test building CDN mapping with multiple CDNs for same original domain."""
        domains = [
            "api.example.com.cdn.cloudflare.net",
            "api.example.com.w.kunlunar.com",
        ]
        mapping = service.build_cdn_mapping(domains)

        assert "api.example.com" in mapping
        assert len(mapping["api.example.com"]) == 2
        assert "api.example.com.cdn.cloudflare.net" in mapping["api.example.com"]
        assert "api.example.com.w.kunlunar.com" in mapping["api.example.com"]

    def test_build_cdn_mapping_empty_list(self, service):
        """Test building CDN mapping with empty list."""
        mapping = service.build_cdn_mapping([])
        assert mapping == {}

    def test_build_cdn_mapping_no_cdns(self, service):
        """Test building CDN mapping with no CDN domains."""
        domains = ["example.com", "www.test.com"]
        mapping = service.build_cdn_mapping(domains)
        assert mapping == {}

    def test_deeply_nested_subdomain_extraction(self, service):
        """Test extracting original domain from deeply nested subdomains."""
        assert service.extract_original_domain("deep.sub.domain.example.com.cdn.cloudflare.net") == "deep.sub.domain.example.com"

    def test_cdn_patterns_structure(self):
        """Test that CDN_PATTERNS has the expected structure."""
        assert isinstance(CDN_PATTERNS, dict)
        assert "cloudflare" in CDN_PATTERNS
        assert "aliyun" in CDN_PATTERNS
        assert "tencent" in CDN_PATTERNS
        assert "baidu" in CDN_PATTERNS
        assert "huawei" in CDN_PATTERNS
        assert "wangsu" in CDN_PATTERNS
        assert "qiniu" in CDN_PATTERNS
        assert "aws" in CDN_PATTERNS

        # Each provider should have a list of patterns
        for provider, patterns in CDN_PATTERNS.items():
            assert isinstance(patterns, list)
            assert len(patterns) > 0
            for pattern in patterns:
                assert isinstance(pattern, str)
