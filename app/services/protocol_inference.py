"""
Protocol Inference Service.

This module provides functionality to infer protocol information (http/https)
from port numbers and service banners for asset data quality improvement.
"""

from typing import Optional, Dict, Any, List

# Port to protocol mapping for common HTTP/HTTPS ports
PORT_PROTOCOL_MAP = {
    # HTTP ports
    80: "http",
    8080: "http",
    8000: "http",
    8888: "http",
    9000: "http",
    3000: "http",
    5000: "http",
    8008: "http",
    8081: "http",
    8082: "http",
    8083: "http",
    9090: "http",
    9093: "http",
    # HTTPS ports
    443: "https",
    8443: "https",
    9443: "https",
    10443: "https",
    4433: "https",
    2083: "https",
    2087: "https",
    2096: "https",
    2053: "https",
}

# Indicators for HTTPS in service banners (higher priority)
HTTPS_INDICATORS = ["https://", "HTTPS", "TLS", "SSL", "certificate", "handshake"]

# Indicators for HTTP in service banners
HTTP_INDICATORS = ["HTTP/1.1", "HTTP/1.0", "HTTP/2"]


def infer_protocol_from_port(port: Optional[int]) -> Optional[str]:
    """
    Infer protocol (http/https) from port number.

    Args:
        port: Port number to check

    Returns:
        "http" for common HTTP ports, "https" for common HTTPS ports,
        or None if port is unknown or None
    """
    if port is None:
        return None
    return PORT_PROTOCOL_MAP.get(port)


class ProtocolInferenceService:
    """
    Service for inferring and enhancing asset protocol information.

    This service analyzes port numbers and service banners to infer
    the appropriate protocol (http/https) for assets with missing
    protocol information.
    """

    def infer_from_banner(self, banner: Optional[str]) -> Optional[str]:
        """
        Extract protocol from service banner.

        Analyzes the banner string for HTTP/HTTPS indicators.
        HTTPS indicators take priority over HTTP indicators.

        Args:
            banner: Service banner string to analyze

        Returns:
            "http", "https", or None if no indicators found
        """
        if banner is None or banner == "":
            return None

        banner_str = str(banner)

        # Check HTTPS indicators first (higher priority)
        for indicator in HTTPS_INDICATORS:
            if indicator in banner_str:
                return "https"

        # Check HTTP indicators
        for indicator in HTTP_INDICATORS:
            if indicator in banner_str:
                return "http"

        return None

    def enhance_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance asset dict with inferred protocol if missing.

        Protocol inference priority:
        1. Keep existing protocol if already set
        2. Infer from port number
        3. Infer from service banner

        Args:
            asset: Asset dictionary containing at least 'port' key,
                   optionally 'protocol' and 'banner' keys

        Returns:
            The enhanced asset dictionary (modified in place)
        """
        # If protocol is already set, don't overwrite it
        if asset.get("protocol") is not None:
            return asset

        port = asset.get("port")
        banner = asset.get("banner")

        # Try to infer from port first (higher priority)
        protocol = infer_protocol_from_port(port)

        # If port doesn't give us an answer, try banner
        if protocol is None and banner is not None:
            protocol = self.infer_from_banner(banner)

        # Set the protocol if we found one
        if protocol is not None:
            asset["protocol"] = protocol

        return asset

    def batch_enhance(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of assets and enhance each with inferred protocol.

        Args:
            assets: List of asset dictionaries

        Returns:
            The list of enhanced assets (modified in place)
        """
        for asset in assets:
            self.enhance_asset(asset)
        return assets
