"""
Fingerprint Enhancement Service.

This module provides functionality to extract fingerprint information from
various asset data sources (banner, headers, title, URL path) to enhance
asset records with technology and product information.
"""

import re
from typing import Dict, Any, List, Optional, Set

# Fingerprint patterns for technology detection
FINGERPRINT_PATTERNS = {
    "web_servers": {
        "nginx": [r"nginx[\s/]", r"nginx"],
        "apache": [r"apache[\s/]", r"apache-httpd", r"httpd"],
        "iis": [r"microsoft-iis[\s/]", r"iis[\s/]"],
        "tomcat": [r"apache-coyote", r"tomcat[\s/]"],
        "openresty": [r"openresty[\s/]"],
        "tengine": [r"tengine[\s/]"],
        "caddy": [r"caddy[\s/]"],
    },
    "frameworks": {
        "php": [r"php[\s/]", r"\.php"],
        "express": [r"express[\s/]", r"/api/"],
        "django": [r"django[\s/]", r"wsgiserver"],
        "flask": [r"flask[\s/]", r"werkzeug"],
        "aspnet": [r"asp\.net", r"aspnet", r"x-aspnet", r"\.aspx"],
        "laravel": [r"laravel[\s/]", r"/laravel/"],
    },
    "cms": {
        "wordpress": [r"wordpress", r"wp-content", r"wp-admin", r"wp-includes"],
        "drupal": [r"drupal", r"/sites/default/"],
        "joomla": [r"joomla", r"/administrator/"],
    },
    "cdn": {
        "cloudflare": [r"cloudflare", r"cf-ray"],
    },
    "os": {
        "ubuntu": [r"ubuntu"],
        "centos": [r"centos"],
        "debian": [r"debian"],
        "windows": [r"windows", r"win32", r"win64"],
    },
}

# Compile regex patterns for performance
_COMPILED_PATTERNS: Dict[str, Dict[str, List[re.Pattern]]] = {}


def _get_compiled_patterns() -> Dict[str, Dict[str, List[re.Pattern]]]:
    """Get or compile fingerprint patterns for efficient matching."""
    global _COMPILED_PATTERNS
    if not _COMPILED_PATTERNS:
        for category, technologies in FINGERPRINT_PATTERNS.items():
            _COMPILED_PATTERNS[category] = {}
            for tech, patterns in technologies.items():
                _COMPILED_PATTERNS[category][tech] = [
                    re.compile(pattern, re.IGNORECASE) for pattern in patterns
                ]
    return _COMPILED_PATTERNS


class FingerprintEnhancerService:
    """
    Service for extracting fingerprints from asset data sources.

    This service analyzes various asset data (banner, headers, title, URL path)
    to identify technologies and enhance asset records with fingerprint
    information.
    """

    def extract_from_banner(self, banner: Optional[str]) -> Set[str]:
        """
        Extract technologies from service banner.

        Args:
            banner: Service banner string (e.g., "Apache/2.4.41 (Ubuntu)")

        Returns:
            Set of detected technology names
        """
        detected: Set[str] = set()

        if not banner:
            return detected

        compiled_patterns = _get_compiled_patterns()
        banner_lower = banner.lower()

        for category, technologies in compiled_patterns.items():
            for tech, patterns in technologies.items():
                for pattern in patterns:
                    if pattern.search(banner_lower):
                        detected.add(tech)
                        break

        return detected

    def extract_from_headers(self, headers: Optional[Dict[str, str]]) -> Set[str]:
        """
        Extract technologies from HTTP headers.

        Args:
            headers: Dictionary of HTTP headers

        Returns:
            Set of detected technology names
        """
        detected: Set[str] = set()

        if not headers:
            return detected

        compiled_patterns = _get_compiled_patterns()

        # Headers to check for fingerprint information (header name and value)
        header_keys = ["server", "x-powered-by", "x-aspnet-version", "cf-ray"]

        for key, value in headers.items():
            key_lower = key.lower()
            value_lower = value.lower()
            # Check both header name and value for patterns
            combined_text = f"{key_lower}: {value_lower}"
            for category, technologies in compiled_patterns.items():
                for tech, patterns in technologies.items():
                    for pattern in patterns:
                        if pattern.search(value_lower) or pattern.search(combined_text):
                            detected.add(tech)
                            break

        return detected

    def extract_from_title(self, title: Optional[str]) -> Set[str]:
        """
        Extract CMS information from page title.

        Args:
            title: Page title string

        Returns:
            Set of detected CMS names
        """
        detected: Set[str] = set()

        if not title:
            return detected

        compiled_patterns = _get_compiled_patterns()
        title_lower = title.lower()

        # Only check CMS patterns in title
        cms_patterns = compiled_patterns.get("cms", {})
        for tech, patterns in cms_patterns.items():
            for pattern in patterns:
                if pattern.search(title_lower):
                    detected.add(tech)
                    break

        return detected

    def extract_from_url_path(self, url: Optional[str]) -> Set[str]:
        """
        Extract technologies from URL path.

        Args:
            url: URL string

        Returns:
            Set of detected technology names
        """
        detected: Set[str] = set()

        if not url:
            return detected

        compiled_patterns = _get_compiled_patterns()
        url_lower = url.lower()

        # Check CMS and framework patterns in URL
        for category in ["cms", "frameworks"]:
            category_patterns = compiled_patterns.get(category, {})
            for tech, patterns in category_patterns.items():
                for pattern in patterns:
                    if pattern.search(url_lower):
                        detected.add(tech)
                        break

        return detected

    def enhance_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance asset with extracted fingerprint information.

        Extracts technologies from all available sources (banner, headers,
        title, url) and updates the asset with:
        - technologies: List of all detected technologies
        - product: First web server found (if asset has no product)

        Args:
            asset: Asset dictionary with optional banner, headers, title, url

        Returns:
            Enhanced asset dictionary
        """
        if not asset:
            return {}

        # Create a copy to avoid modifying the original
        enhanced = dict(asset)

        # Extract from all sources (use list to preserve order)
        detected_techs_ordered: List[str] = []
        detected_techs_set: Set[str] = set()

        def add_techs(techs: Set[str]) -> None:
            """Add technologies preserving order and avoiding duplicates."""
            for tech in techs:
                if tech not in detected_techs_set:
                    detected_techs_set.add(tech)
                    detected_techs_ordered.append(tech)

        # Extract from banner (highest priority)
        banner = enhanced.get("banner")
        if banner:
            add_techs(self.extract_from_banner(banner))

        # Extract from headers
        headers = enhanced.get("headers")
        if headers:
            add_techs(self.extract_from_headers(headers))

        # Extract from title
        title = enhanced.get("title")
        if title:
            add_techs(self.extract_from_title(title))

        # Extract from URL
        url = enhanced.get("url")
        if url:
            add_techs(self.extract_from_url_path(url))

        # Merge with existing technologies if present
        existing_techs = enhanced.get("technologies", [])
        if existing_techs is None:
            existing_techs = []
        if isinstance(existing_techs, str):
            existing_techs = [existing_techs]
        # Add existing techs at the end (lowest priority)
        for tech in existing_techs:
            if tech not in detected_techs_set:
                detected_techs_set.add(tech)
                detected_techs_ordered.append(tech)

        # Set technologies as list
        enhanced["technologies"] = detected_techs_ordered

        # Set product from first web server if no product exists
        if not enhanced.get("product"):
            web_servers = self._get_web_servers_from_techs(detected_techs_ordered)
            if web_servers:
                enhanced["product"] = web_servers[0]

        return enhanced

    def _get_web_servers_from_techs(self, techs: List[str]) -> List[str]:
        """
        Get web server technologies from a list of detected technologies.

        Args:
            techs: List of detected technology names

        Returns:
            List of web server technology names in order of detection
        """
        web_server_techs = set(FINGERPRINT_PATTERNS.get("web_servers", {}).keys())
        return [tech for tech in techs if tech in web_server_techs]

    def batch_enhance(self, assets: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Process a list of assets and enhance each with fingerprint information.

        Args:
            assets: List of asset dictionaries

        Returns:
            List of enhanced asset dictionaries
        """
        if not assets:
            return []

        return [self.enhance_asset(asset) for asset in assets]

    def calculate_fingerprint_coverage(
        self, assets: Optional[List[Dict[str, Any]]]
    ) -> float:
        """
        Calculate the percentage of assets with fingerprint information.

        An asset is considered to have fingerprint information if it has:
        - non-empty technologies list, or
        - a product field set

        Args:
            assets: List of asset dictionaries

        Returns:
            Coverage percentage (0.0 to 100.0)
        """
        if not assets:
            return 0.0

        total = len(assets)
        if total == 0:
            return 0.0

        fingerprinted = 0
        for asset in assets:
            has_techs = bool(asset.get("technologies"))
            has_product = bool(asset.get("product"))
            if has_techs or has_product:
                fingerprinted += 1

        return (fingerprinted / total) * 100.0
