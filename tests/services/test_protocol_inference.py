"""
Unit tests for Protocol Inference Service.

Tests the protocol inference logic based on port numbers and service banners.
"""

import pytest
from app.services.protocol_inference import (
    infer_protocol_from_port,
    ProtocolInferenceService,
    PORT_PROTOCOL_MAP,
    HTTPS_INDICATORS,
    HTTP_INDICATORS,
)


class TestInferProtocolFromPort:
    """Tests for infer_protocol_from_port function."""

    def test_infer_protocol_from_common_ports(self):
        """Test common HTTP and HTTPS ports."""
        assert infer_protocol_from_port(80) == "http"
        assert infer_protocol_from_port(443) == "https"

    def test_infer_protocol_from_https_ports(self):
        """Test all known HTTPS ports return 'https'."""
        https_ports = [443, 8443, 9443, 10443, 4433, 2083, 2087, 2096, 2053]
        for port in https_ports:
            assert infer_protocol_from_port(port) == "https", f"Port {port} should return https"

    def test_infer_protocol_from_http_ports(self):
        """Test all known HTTP ports return 'http'."""
        http_ports = [80, 8080, 8000, 8888, 9000, 3000, 5000, 8008, 8081, 8082, 8083, 9090, 9093]
        for port in http_ports:
            assert infer_protocol_from_port(port) == "http", f"Port {port} should return http"

    def test_infer_protocol_unknown_port(self):
        """Test unknown ports return None."""
        assert infer_protocol_from_port(9999) is None
        assert infer_protocol_from_port(12345) is None
        assert infer_protocol_from_port(0) is None

    def test_infer_protocol_none_input(self):
        """Test None input returns None."""
        assert infer_protocol_from_port(None) is None


class TestProtocolInferenceService:
    """Tests for ProtocolInferenceService class."""

    @pytest.fixture
    def service(self):
        """Create a ProtocolInferenceService instance."""
        return ProtocolInferenceService()

    def test_infer_from_banner_https_indicators(self, service):
        """Test banner analysis with HTTPS indicators."""
        # Test with HTTPS indicators
        assert service.infer_from_banner("Server uses https:// protocol") == "https"
        assert service.infer_from_banner("HTTPS enabled server") == "https"
        assert service.infer_from_banner("TLS 1.3 handshake") == "https"
        assert service.infer_from_banner("SSL certificate valid") == "https"
        assert service.infer_from_banner("certificate error") == "https"
        assert service.infer_from_banner("handshake failed") == "https"

    def test_infer_from_banner_http_indicators(self, service):
        """Test banner analysis with HTTP indicators."""
        assert service.infer_from_banner("HTTP/1.1 200 OK") == "http"
        assert service.infer_from_banner("HTTP/1.0 404 Not Found") == "http"
        assert service.infer_from_banner("HTTP/2 server") == "http"

    def test_infer_from_banner_no_indicators(self, service):
        """Test banner analysis with no protocol indicators."""
        assert service.infer_from_banner("Apache Server") is None
        assert service.infer_from_banner("") is None

    def test_infer_from_banner_none_input(self, service):
        """Test banner analysis with None input."""
        assert service.infer_from_banner(None) is None

    def test_infer_from_banner_priority(self, service):
        """Test that HTTPS indicators take priority over HTTP indicators."""
        # HTTPS should win when both indicators present
        assert service.infer_from_banner("HTTP/1.1 200 OK with SSL certificate") == "https"

    def test_enhance_asset_protocol_missing(self, service):
        """Test enhancing asset with missing protocol."""
        asset = {"ip": "192.168.1.1", "port": 443, "protocol": None}
        result = service.enhance_asset(asset)
        assert result["protocol"] == "https"

    def test_enhance_asset_protocol_from_port(self, service):
        """Test enhancing asset protocol inferred from port."""
        asset = {"ip": "192.168.1.1", "port": 8080}
        result = service.enhance_asset(asset)
        assert result["protocol"] == "http"

    def test_enhance_asset_protocol_from_banner(self, service):
        """Test enhancing asset protocol inferred from banner."""
        asset = {"ip": "192.168.1.1", "port": 9999, "banner": "HTTP/1.1 200 OK"}
        result = service.enhance_asset(asset)
        assert result["protocol"] == "http"

    def test_enhance_asset_protocol_already_set(self, service):
        """Test that existing protocol is not overwritten."""
        asset = {"ip": "192.168.1.1", "port": 80, "protocol": "https"}
        result = service.enhance_asset(asset)
        assert result["protocol"] == "https"  # Should keep existing

    def test_enhance_asset_port_priority_over_banner(self, service):
        """Test that port inference takes priority over banner."""
        # Port 443 should give https even if banner says HTTP
        asset = {"ip": "192.168.1.1", "port": 443, "banner": "HTTP/1.1 200 OK"}
        result = service.enhance_asset(asset)
        assert result["protocol"] == "https"

    def test_enhance_asset_unknown_port_no_banner(self, service):
        """Test enhancing asset with unknown port and no banner."""
        asset = {"ip": "192.168.1.1", "port": 9999}
        result = service.enhance_asset(asset)
        assert result.get("protocol") is None

    def test_enhance_asset_returns_dict(self, service):
        """Test that enhance_asset returns the asset dict."""
        asset = {"ip": "192.168.1.1", "port": 80}
        result = service.enhance_asset(asset)
        assert isinstance(result, dict)
        assert result is asset  # Should return same object

    def test_batch_enhance_empty_list(self, service):
        """Test batch enhance with empty list."""
        result = service.batch_enhance([])
        assert result == []

    def test_batch_enhance_multiple_assets(self, service):
        """Test batch enhance with multiple assets."""
        assets = [
            {"ip": "192.168.1.1", "port": 80},
            {"ip": "192.168.1.2", "port": 443},
            {"ip": "192.168.1.3", "port": 9999, "banner": "HTTP/1.1 200 OK"},
        ]
        results = service.batch_enhance(assets)
        assert len(results) == 3
        assert results[0]["protocol"] == "http"
        assert results[1]["protocol"] == "https"
        assert results[2]["protocol"] == "http"

    def test_batch_enhance_preserves_original(self, service):
        """Test that batch enhance modifies assets in place."""
        assets = [{"ip": "192.168.1.1", "port": 80}]
        results = service.batch_enhance(assets)
        assert results[0] is assets[0]
