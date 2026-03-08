"""
Unit tests for Fingerprint Enhancement Service.

Tests the fingerprint extraction from various sources (banner, headers, title, URL)
and asset enhancement with extracted fingerprint information.
"""

import pytest
from app.services.fingerprint_enhancer import (
    FINGERPRINT_PATTERNS,
    FingerprintEnhancerService,
)


class TestFingerprintPatterns:
    """Tests for FINGERPRINT_PATTERNS structure."""

    def test_patterns_structure(self):
        """Test that FINGERPRINT_PATTERNS has the expected structure."""
        assert isinstance(FINGERPRINT_PATTERNS, dict)

        # Check all expected categories exist
        assert "web_servers" in FINGERPRINT_PATTERNS
        assert "frameworks" in FINGERPRINT_PATTERNS
        assert "cms" in FINGERPRINT_PATTERNS
        assert "cdn" in FINGERPRINT_PATTERNS
        assert "os" in FINGERPRINT_PATTERNS

    def test_web_servers_patterns(self):
        """Test that web servers patterns exist."""
        web_servers = FINGERPRINT_PATTERNS["web_servers"]
        assert "nginx" in web_servers
        assert "apache" in web_servers
        assert "iis" in web_servers
        assert "tomcat" in web_servers
        assert "openresty" in web_servers
        assert "tengine" in web_servers
        assert "caddy" in web_servers

    def test_frameworks_patterns(self):
        """Test that frameworks patterns exist."""
        frameworks = FINGERPRINT_PATTERNS["frameworks"]
        assert "php" in frameworks
        assert "express" in frameworks
        assert "django" in frameworks
        assert "flask" in frameworks
        assert "aspnet" in frameworks
        assert "laravel" in frameworks

    def test_cms_patterns(self):
        """Test that CMS patterns exist."""
        cms = FINGERPRINT_PATTERNS["cms"]
        assert "wordpress" in cms
        assert "drupal" in cms
        assert "joomla" in cms

    def test_cdn_patterns(self):
        """Test that CDN patterns exist."""
        cdn = FINGERPRINT_PATTERNS["cdn"]
        assert "cloudflare" in cdn

    def test_os_patterns(self):
        """Test that OS patterns exist."""
        os_patterns = FINGERPRINT_PATTERNS["os"]
        assert "ubuntu" in os_patterns
        assert "centos" in os_patterns
        assert "debian" in os_patterns
        assert "windows" in os_patterns


class TestExtractFromBanner:
    """Tests for extract_from_banner method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_extract_nginx_from_banner(self, service):
        """Test extracting nginx from server banner."""
        banner = "nginx/1.18.0"
        result = service.extract_from_banner(banner)
        assert "nginx" in result

    def test_extract_apache_from_banner(self, service):
        """Test extracting Apache from server banner."""
        banner = "Apache/2.4.41 (Ubuntu)"
        result = service.extract_from_banner(banner)
        assert "apache" in result
        assert "ubuntu" in result

    def test_extract_iis_from_banner(self, service):
        """Test extracting IIS from server banner."""
        banner = "Microsoft-IIS/10.0"
        result = service.extract_from_banner(banner)
        assert "iis" in result

    def test_extract_tomcat_from_banner(self, service):
        """Test extracting Tomcat from server banner."""
        banner = "Apache-Coyote/1.1"
        result = service.extract_from_banner(banner)
        assert "tomcat" in result

    def test_extract_openresty_from_banner(self, service):
        """Test extracting OpenResty from server banner."""
        banner = "openresty/1.19.3.1"
        result = service.extract_from_banner(banner)
        assert "openresty" in result

    def test_extract_tengine_from_banner(self, service):
        """Test extracting Tengine from server banner."""
        banner = "Tengine/2.3.2"
        result = service.extract_from_banner(banner)
        assert "tengine" in result

    def test_extract_caddy_from_banner(self, service):
        """Test extracting Caddy from server banner."""
        banner = "Caddy/2.4.3"
        result = service.extract_from_banner(banner)
        assert "caddy" in result

    def test_extract_multiple_from_banner(self, service):
        """Test extracting multiple technologies from banner."""
        banner = "Apache/2.4.41 (Ubuntu) PHP/7.4.3"
        result = service.extract_from_banner(banner)
        assert "apache" in result
        assert "ubuntu" in result
        assert "php" in result

    def test_extract_from_empty_banner(self, service):
        """Test extracting from empty banner returns empty set."""
        result = service.extract_from_banner("")
        assert result == set()

    def test_extract_from_none_banner(self, service):
        """Test extracting from None banner returns empty set."""
        result = service.extract_from_banner(None)
        assert result == set()

    def test_extract_case_insensitive(self, service):
        """Test that extraction is case-insensitive."""
        banner = "NGINX/1.18.0"
        result = service.extract_from_banner(banner)
        assert "nginx" in result


class TestExtractFromHeaders:
    """Tests for extract_from_headers method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_extract_from_server_header(self, service):
        """Test extracting from Server header."""
        headers = {"Server": "nginx/1.18.0"}
        result = service.extract_from_headers(headers)
        assert "nginx" in result

    def test_extract_from_x_powered_by_header(self, service):
        """Test extracting from X-Powered-By header."""
        headers = {"X-Powered-By": "PHP/7.4.3"}
        result = service.extract_from_headers(headers)
        assert "php" in result

    def test_extract_from_multiple_headers(self, service):
        """Test extracting from multiple headers."""
        headers = {
            "Server": "Apache/2.4.41 (Ubuntu)",
            "X-Powered-By": "PHP/7.4.3",
        }
        result = service.extract_from_headers(headers)
        assert "apache" in result
        assert "ubuntu" in result
        assert "php" in result

    def test_extract_cloudflare_from_headers(self, service):
        """Test extracting Cloudflare from headers."""
        headers = {
            "Server": "cloudflare",
            "CF-RAY": "1234567890abcdef-SJC",
        }
        result = service.extract_from_headers(headers)
        assert "cloudflare" in result

    def test_extract_aspnet_from_headers(self, service):
        """Test extracting ASP.NET from headers."""
        headers = {
            "Server": "Microsoft-IIS/10.0",
            "X-AspNet-Version": "4.0.30319",
        }
        result = service.extract_from_headers(headers)
        assert "iis" in result
        assert "aspnet" in result

    def test_extract_from_empty_headers(self, service):
        """Test extracting from empty headers returns empty set."""
        result = service.extract_from_headers({})
        assert result == set()

    def test_extract_from_none_headers(self, service):
        """Test extracting from None headers returns empty set."""
        result = service.extract_from_headers(None)
        assert result == set()

    def test_extract_case_insensitive_headers(self, service):
        """Test that header extraction is case-insensitive."""
        headers = {"server": "nginx/1.18.0", "x-powered-by": "PHP/7.4.3"}
        result = service.extract_from_headers(headers)
        assert "nginx" in result
        assert "php" in result


class TestExtractFromTitle:
    """Tests for extract_from_title method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_extract_wordpress_from_title(self, service):
        """Test extracting WordPress from page title."""
        title = "My Blog - Just another WordPress site"
        result = service.extract_from_title(title)
        assert "wordpress" in result

    def test_extract_drupal_from_title(self, service):
        """Test extracting Drupal from page title."""
        title = "Welcome to Drupal | Example Site"
        result = service.extract_from_title(title)
        assert "drupal" in result

    def test_extract_joomla_from_title(self, service):
        """Test extracting Joomla from page title."""
        title = "Home - Joomla Example Site"
        result = service.extract_from_title(title)
        assert "joomla" in result

    def test_extract_no_cms_from_title(self, service):
        """Test extracting from title with no CMS indicators."""
        title = "Welcome to Example Site"
        result = service.extract_from_title(title)
        assert result == set()

    def test_extract_from_empty_title(self, service):
        """Test extracting from empty title returns empty set."""
        result = service.extract_from_title("")
        assert result == set()

    def test_extract_from_none_title(self, service):
        """Test extracting from None title returns empty set."""
        result = service.extract_from_title(None)
        assert result == set()

    def test_extract_case_insensitive_title(self, service):
        """Test that title extraction is case-insensitive."""
        title = "MY BLOG - JUST ANOTHER WORDPRESS SITE"
        result = service.extract_from_title(title)
        assert "wordpress" in result


class TestExtractFromUrlPath:
    """Tests for extract_from_url_path method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_extract_wordpress_from_url(self, service):
        """Test extracting WordPress from URL path."""
        url = "https://example.com/wp-content/themes/twentytwenty/style.css"
        result = service.extract_from_url_path(url)
        assert "wordpress" in result

    def test_extract_wordpress_admin_from_url(self, service):
        """Test extracting WordPress from admin URL."""
        url = "https://example.com/wp-admin/login.php"
        result = service.extract_from_url_path(url)
        assert "wordpress" in result

    def test_extract_drupal_from_url(self, service):
        """Test extracting Drupal from URL path."""
        url = "https://example.com/sites/default/files/logo.png"
        result = service.extract_from_url_path(url)
        assert "drupal" in result

    def test_extract_joomla_from_url(self, service):
        """Test extracting Joomla from URL path."""
        url = "https://example.com/administrator/index.php"
        result = service.extract_from_url_path(url)
        assert "joomla" in result

    def test_extract_laravel_from_url(self, service):
        """Test extracting Laravel from URL path."""
        url = "https://example.com/laravel/public/index.php"
        result = service.extract_from_url_path(url)
        assert "laravel" in result

    def test_extract_php_from_url(self, service):
        """Test extracting PHP from URL path."""
        url = "https://example.com/index.php"
        result = service.extract_from_url_path(url)
        assert "php" in result

    def test_extract_aspnet_from_url(self, service):
        """Test extracting ASP.NET from URL path."""
        url = "https://example.com/page.aspx"
        result = service.extract_from_url_path(url)
        assert "aspnet" in result

    def test_extract_express_from_url(self, service):
        """Test extracting Express from URL path."""
        url = "https://example.com/api/users"
        result = service.extract_from_url_path(url)
        assert "express" in result

    def test_extract_no_tech_from_url(self, service):
        """Test extracting from URL with no tech indicators."""
        url = "https://example.com/about.html"
        result = service.extract_from_url_path(url)
        assert result == set()

    def test_extract_from_empty_url(self, service):
        """Test extracting from empty URL returns empty set."""
        result = service.extract_from_url_path("")
        assert result == set()

    def test_extract_from_none_url(self, service):
        """Test extracting from None URL returns empty set."""
        result = service.extract_from_url_path(None)
        assert result == set()


class TestEnhanceAsset:
    """Tests for enhance_asset method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_enhance_asset_with_fingerprint(self, service):
        """Test full asset enhancement with fingerprint extraction."""
        asset = {
            "id": 1,
            "host": "example.com",
            "banner": "Apache/2.4.41 (Ubuntu)",
            "headers": {"X-Powered-By": "PHP/7.4.3"},
            "title": "Welcome to WordPress",
            "url": "https://example.com/wp-admin/",
        }

        result = service.enhance_asset(asset)

        # Check that technologies are extracted
        assert "technologies" in result
        assert "apache" in result["technologies"]
        assert "ubuntu" in result["technologies"]
        assert "php" in result["technologies"]
        assert "wordpress" in result["technologies"]

        # Check that product is set from web server
        assert result["product"] == "apache"

    def test_enhance_asset_without_product_sets_web_server(self, service):
        """Test that product is set to first web server if not present."""
        asset = {
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "nginx"

    def test_enhance_asset_preserves_existing_product(self, service):
        """Test that existing product is preserved."""
        asset = {
            "product": "custom-product",
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "custom-product"

    def test_enhance_asset_with_no_fingerprint_data(self, service):
        """Test enhancement with no fingerprint data available."""
        asset = {
            "id": 1,
            "host": "example.com",
        }

        result = service.enhance_asset(asset)

        # Should have empty technologies list
        assert "technologies" in result
        assert result["technologies"] == []

        # Product should not be set
        assert "product" not in result

    def test_enhance_asset_deduplicates_technologies(self, service):
        """Test that duplicate technologies are deduplicated."""
        asset = {
            "banner": "nginx/1.18.0",
            "headers": {"Server": "nginx/1.18.0"},
        }

        result = service.enhance_asset(asset)
        # nginx should appear only once
        assert result["technologies"].count("nginx") == 1


class TestMergeWithExistingFingerprint:
    """Tests for merging with existing fingerprint data."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_merge_with_existing_technologies(self, service):
        """Test merging extracted tech with existing technologies."""
        asset = {
            "technologies": ["mysql", "redis"],
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)

        # Should contain both existing and new technologies
        assert "mysql" in result["technologies"]
        assert "redis" in result["technologies"]
        assert "nginx" in result["technologies"]

    def test_merge_preserves_existing_product(self, service):
        """Test that existing product is not overwritten."""
        asset = {
            "product": "existing-product",
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "existing-product"

    def test_merge_with_existing_product_none(self, service):
        """Test that product is set when existing product is None."""
        asset = {
            "product": None,
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "nginx"

    def test_merge_with_existing_empty_technologies(self, service):
        """Test merging with empty existing technologies list."""
        asset = {
            "technologies": [],
            "banner": "nginx/1.18.0",
        }

        result = service.enhance_asset(asset)
        assert "nginx" in result["technologies"]


class TestBatchEnhance:
    """Tests for batch_enhance method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_batch_enhance_multiple_assets(self, service):
        """Test batch enhancement of multiple assets."""
        assets = [
            {"banner": "nginx/1.18.0"},
            {"banner": "Apache/2.4.41"},
            {"headers": {"Server": "cloudflare"}},
        ]

        results = service.batch_enhance(assets)

        assert len(results) == 3
        assert "nginx" in results[0]["technologies"]
        assert "apache" in results[1]["technologies"]
        assert "cloudflare" in results[2]["technologies"]

    def test_batch_enhance_empty_list(self, service):
        """Test batch enhancement with empty list."""
        results = service.batch_enhance([])
        assert results == []

    def test_batch_enhance_none_input(self, service):
        """Test batch enhancement with None input."""
        results = service.batch_enhance(None)
        assert results == []


class TestCalculateFingerprintCoverage:
    """Tests for calculate_fingerprint_coverage method."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_calculate_coverage_with_all_fingerprinted(self, service):
        """Test coverage calculation when all assets have fingerprints."""
        assets = [
            {"technologies": ["nginx"]},
            {"technologies": ["apache"]},
            {"product": "iis"},
        ]

        coverage = service.calculate_fingerprint_coverage(assets)
        assert coverage == 100.0

    def test_calculate_coverage_with_no_fingerprinted(self, service):
        """Test coverage calculation when no assets have fingerprints."""
        assets = [
            {"host": "example1.com"},
            {"host": "example2.com"},
        ]

        coverage = service.calculate_fingerprint_coverage(assets)
        assert coverage == 0.0

    def test_calculate_coverage_with_partial(self, service):
        """Test coverage calculation with partial fingerprint coverage."""
        assets = [
            {"technologies": ["nginx"]},
            {"host": "example2.com"},
            {"product": "apache"},
            {"host": "example4.com"},
        ]

        coverage = service.calculate_fingerprint_coverage(assets)
        assert coverage == 50.0

    def test_calculate_coverage_empty_list(self, service):
        """Test coverage calculation with empty list."""
        coverage = service.calculate_fingerprint_coverage([])
        assert coverage == 0.0

    def test_calculate_coverage_none_input(self, service):
        """Test coverage calculation with None input."""
        coverage = service.calculate_fingerprint_coverage(None)
        assert coverage == 0.0

    def test_calculate_coverage_with_empty_technologies(self, service):
        """Test coverage calculation with empty technologies list."""
        assets = [
            {"technologies": []},
            {"host": "example2.com"},
        ]

        coverage = service.calculate_fingerprint_coverage(assets)
        assert coverage == 0.0


class TestWebServerPriority:
    """Tests for web server priority in product selection."""

    @pytest.fixture
    def service(self):
        """Create a FingerprintEnhancerService instance."""
        return FingerprintEnhancerService()

    def test_nginx_priority_over_framework(self, service):
        """Test that nginx is selected as product over framework."""
        asset = {
            "banner": "nginx/1.18.0",
            "headers": {"X-Powered-By": "PHP/7.4.3"},
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "nginx"

    def test_apache_priority_over_cms(self, service):
        """Test that apache is selected as product over CMS."""
        asset = {
            "banner": "Apache/2.4.41",
            "title": "Welcome to WordPress",
        }

        result = service.enhance_asset(asset)
        assert result["product"] == "apache"

    def test_first_web_server_selected(self, service):
        """Test that first web server in list is selected as product."""
        asset = {
            "banner": "nginx/1.18.0",
            "headers": {"Server": "Apache/2.4.41"},
        }

        result = service.enhance_asset(asset)
        # nginx should be selected as it appears first in banner
        assert result["product"] == "nginx"
