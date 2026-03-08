"""
CDN Detection and Association Service.

This module provides functionality to detect CDN providers from domain names
and extract the original domain from CDN domains for asset association.
"""

import re
from typing import Optional, Dict, Any, List

# CDN domain patterns for various providers
CDN_PATTERNS = {
    "cloudflare": [
        r"\.cdn\.cloudflare\.net$",
        r"\.cloudflare\.net$",
        r"\.cloudflare-dns\.com$",
    ],
    "aliyun": [
        r"\.w\.kunlunar\.com$",
        r"\.w\.alikunlun\.net$",
        r"\.aliyuncs\.com$",
    ],
    "tencent": [
        r"\.tc\.cdn$",
        r"\.cdn\.dnsv1\.com$",
    ],
    "baidu": [
        r"\.jomodns\.com$",
        r"\.bdydns\.net$",
    ],
    "huawei": [
        r"\.hc\.cdn$",
        r"\.cdnhwc([0-9]+)\.com$",
    ],
    "wangsu": [
        r"\.wscdns\.com$",
        r"\.cdn20\.com$",
    ],
    "qiniu": [
        r"\.qiniudns\.com$",
        r"\.clouddn\.com$",
    ],
    "aws": [
        r"\.cloudfront\.net$",
    ],
}

# Compile regex patterns for performance
_COMPILED_PATTERNS: Dict[str, List[re.Pattern]] = {}


def _get_compiled_patterns() -> Dict[str, List[re.Pattern]]:
    """Get or compile CDN patterns for efficient matching."""
    global _COMPILED_PATTERNS
    if not _COMPILED_PATTERNS:
        for provider, patterns in CDN_PATTERNS.items():
            _COMPILED_PATTERNS[provider] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    return _COMPILED_PATTERNS


def detect_cdn(domain: Optional[str]) -> Optional[str]:
    """
    Detect CDN provider from domain name.

    Args:
        domain: Domain name to check

    Returns:
        CDN provider name (e.g., "cloudflare", "aliyun") or None if not a CDN domain
    """
    if not domain:
        return None

    domain_lower = domain.lower()
    compiled_patterns = _get_compiled_patterns()

    for provider, patterns in compiled_patterns.items():
        for pattern in patterns:
            if pattern.search(domain_lower):
                return provider

    return None


class CDNDetectorService:
    """
    Service for detecting CDN providers and extracting original domains.

    This service analyzes domain names to identify CDN providers and
    extract the original domain for asset association and mapping.
    """

    def detect_cdn(self, domain: Optional[str]) -> Optional[str]:
        """
        Detect if a domain uses a CDN.

        Args:
            domain: Domain name to check

        Returns:
            CDN provider name or None if not a CDN domain
        """
        return detect_cdn(domain)

    def extract_original_domain(self, cdn_domain: Optional[str]) -> Optional[str]:
        """
        Extract the original domain from a CDN domain.

        For example:
        - api.example.com.cdn.cloudflare.net -> api.example.com
        - static.example.com.w.kunlunar.com -> static.example.com

        Args:
            cdn_domain: The CDN domain name

        Returns:
            The original domain, or the input domain if not a CDN domain,
            or None if input is None
        """
        if not cdn_domain:
            return cdn_domain

        domain_lower = cdn_domain.lower()
        compiled_patterns = _get_compiled_patterns()

        for provider, patterns in compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(domain_lower)
                if match:
                    # Remove the CDN suffix from the domain
                    original = domain_lower[:match.start()]
                    # Remove trailing dot if present
                    if original.endswith("."):
                        original = original[:-1]
                    return original

        # Not a CDN domain, return as-is
        return cdn_domain

    def normalize_cdn_domain(self, domain: Optional[str]) -> Dict[str, Any]:
        """
        Normalize a domain and return CDN information.

        Args:
            domain: Domain name to normalize

        Returns:
            Dictionary with keys:
                - is_cdn: Boolean indicating if it's a CDN domain
                - cdn_provider: CDN provider name or None
                - original_domain: Original domain or the domain itself
        """
        cdn_provider = self.detect_cdn(domain)
        original_domain = self.extract_original_domain(domain)

        return {
            "is_cdn": cdn_provider is not None,
            "cdn_provider": cdn_provider,
            "original_domain": original_domain,
        }

    def batch_process(self, domains: Optional[List[str]]) -> List[Dict[str, Any]]:
        """
        Process a list of domains and normalize each.

        Args:
            domains: List of domain names

        Returns:
            List of normalized domain information dictionaries
        """
        if not domains:
            return []

        return [self.normalize_cdn_domain(domain) for domain in domains]

    def build_cdn_mapping(self, domains: Optional[List[str]]) -> Dict[str, List[str]]:
        """
        Build a mapping of original domains to their CDN domains.

        Args:
            domains: List of domain names (can include CDN and non-CDN domains)

        Returns:
            Dictionary mapping original domain -> list of CDN domains
        """
        mapping: Dict[str, List[str]] = {}

        if not domains:
            return mapping

        for domain in domains:
            cdn_provider = self.detect_cdn(domain)
            if cdn_provider:
                original = self.extract_original_domain(domain)
                if original not in mapping:
                    mapping[original] = []
                mapping[original].append(domain)

        return mapping
