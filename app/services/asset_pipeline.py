"""
Asset Processing Pipeline.

This module provides a unified pipeline that integrates all asset processing
services: CDN detection, protocol inference, fingerprint enhancement, and
asset deduplication.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from app.services.cdn_detector import CDNDetectorService
from app.services.protocol_inference import ProtocolInferenceService
from app.services.fingerprint_enhancer import FingerprintEnhancerService
from app.services.asset_dedup import AssetDedupService


@dataclass
class PipelineStats:
    """Statistics for asset pipeline processing.

    Attributes:
        input_count: Number of assets input to the pipeline
        output_count: Number of assets output from the pipeline
        cdn_detected: Number of assets with CDN detected
        protocol_enhanced: Number of assets with protocol enhanced
        fingerprint_enhanced: Number of assets with fingerprint enhanced
        dedup_removed: Number of duplicate assets removed
        errors: List of error messages encountered during processing
    """

    input_count: int = 0
    output_count: int = 0
    cdn_detected: int = 0
    protocol_enhanced: int = 0
    fingerprint_enhanced: int = 0
    dedup_removed: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary format."""
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "cdn_detected": self.cdn_detected,
            "protocol_enhanced": self.protocol_enhanced,
            "fingerprint_enhanced": self.fingerprint_enhanced,
            "dedup_removed": self.dedup_removed,
            "errors": self.errors,
        }


class AssetPipeline:
    """Unified pipeline for processing assets through all enhancement services.

    This pipeline integrates CDN detection, protocol inference, fingerprint
    enhancement, and asset deduplication into a single processing flow.

    Processing flow for each asset:
        1. CDN Detection (if domain present)
        2. Protocol Inference (if protocol missing)
        3. Fingerprint Enhancement

    For batch processing, optional deduplication is applied at the end.

    Example:
        pipeline = AssetPipeline()

        # Process single asset
        enhanced = pipeline.process_asset(asset)

        # Process batch with deduplication
        results = pipeline.process_batch(assets, enable_dedup=True)

        # Get statistics
        stats = pipeline.get_last_stats()
        report = pipeline.get_improvement_report()
    """

    def __init__(
        self,
        cdn_service: Optional[CDNDetectorService] = None,
        protocol_service: Optional[ProtocolInferenceService] = None,
        fingerprint_service: Optional[FingerprintEnhancerService] = None,
        dedup_service: Optional[AssetDedupService] = None,
    ):
        """Initialize the pipeline with all required services.

        Args:
            cdn_service: CDN detection service (created if not provided)
            protocol_service: Protocol inference service (created if not provided)
            fingerprint_service: Fingerprint enhancement service (created if not provided)
            dedup_service: Asset deduplication service (created if not provided)
        """
        self.cdn_service = cdn_service or CDNDetectorService()
        self.protocol_service = protocol_service or ProtocolInferenceService()
        self.fingerprint_service = fingerprint_service or FingerprintEnhancerService()
        self.dedup_service = dedup_service or AssetDedupService()
        self._last_stats = PipelineStats()

    def process_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single asset through the pipeline.

        Processing steps:
        1. CDN Detection: If domain is present, detect CDN and extract original domain
        2. Protocol Inference: If protocol is missing, infer from port/banner
        3. Fingerprint Enhancement: Extract technologies from all data sources

        Args:
            asset: Asset dictionary containing fields like domain, ip_address,
                   port, banner, headers, title, url, etc.

        Returns:
            Enhanced asset dictionary with additional fields from processing
        """
        if not asset:
            return {}

        # Create a copy to avoid modifying the original
        enhanced = dict(asset)

        # 1. CDN Detection
        domain = enhanced.get("domain")
        if domain:
            cdn_info = self.cdn_service.normalize_cdn_domain(domain)
            enhanced.update(cdn_info)

        # 2. Protocol Inference (if missing)
        had_protocol = enhanced.get("protocol") is not None
        enhanced = self.protocol_service.enhance_asset(enhanced)

        # 3. Fingerprint Enhancement
        had_fingerprint = bool(
            enhanced.get("technologies") or enhanced.get("product")
        )
        enhanced = self.fingerprint_service.enhance_asset(enhanced)

        return enhanced

    def process_batch(
        self, assets: List[Dict[str, Any]], enable_dedup: bool = True
    ) -> List[Dict[str, Any]]:
        """Process a batch of assets through the pipeline.

        Args:
            assets: List of asset dictionaries to process
            enable_dedup: If True, apply deduplication after processing

        Returns:
            List of enhanced asset dictionaries
        """
        # Reset stats for this batch
        stats = PipelineStats()
        stats.input_count = len(assets)

        if not assets:
            self._last_stats = stats
            return []

        processed_assets = []
        errors = []

        for asset in assets:
            try:
                # Track pre-processing state
                had_protocol = asset.get("protocol") is not None
                had_fingerprint = bool(
                    asset.get("technologies") or asset.get("product")
                )
                domain = asset.get("domain")

                # Process the asset
                enhanced = self.process_asset(asset)

                # Track stats
                if domain:
                    cdn_info = self.cdn_service.normalize_cdn_domain(domain)
                    if cdn_info.get("is_cdn"):
                        stats.cdn_detected += 1

                if not had_protocol and enhanced.get("protocol"):
                    stats.protocol_enhanced += 1

                # Fingerprint is considered enhanced if technologies were added
                # or if product was set when it wasn't before
                has_techs = bool(enhanced.get("technologies"))
                has_product = bool(enhanced.get("product"))
                if has_techs or (has_product and not had_fingerprint):
                    stats.fingerprint_enhanced += 1

                processed_assets.append(enhanced)

            except Exception as e:
                errors.append(f"Error processing asset: {str(e)}")
                # Include original asset if processing fails
                processed_assets.append(asset)

        stats.errors = errors

        # Apply deduplication if enabled
        if enable_dedup:
            dedup_input_count = len(processed_assets)
            processed_assets = self.dedup_service.dedup_assets(processed_assets)
            stats.dedup_removed = dedup_input_count - len(processed_assets)

        stats.output_count = len(processed_assets)
        self._last_stats = stats

        return processed_assets

    def get_last_stats(self) -> Dict[str, Any]:
        """Get the statistics from the last batch processing operation.

        Returns:
            Dictionary containing processing statistics
        """
        return self._last_stats.to_dict()

    def get_improvement_report(self) -> str:
        """Generate a human-readable improvement report.

        Returns:
            Formatted string report of the last processing operation
        """
        stats = self._last_stats

        lines = [
            "=" * 50,
            "Asset Processing Pipeline Report",
            "=" * 50,
            "",
            f"Input Assets:        {stats.input_count}",
            f"Output Assets:       {stats.output_count}",
            f"CDN Detected:        {stats.cdn_detected}",
            f"Protocol Enhanced:   {stats.protocol_enhanced}",
            f"Fingerprint Enhanced: {stats.fingerprint_enhanced}",
            f"Duplicates Removed:  {stats.dedup_removed}",
        ]

        if stats.errors:
            lines.extend([
                "",
                "Errors:",
                "-" * 50,
            ])
            for error in stats.errors:
                lines.append(f"  - {error}")
        else:
            lines.append("\nErrors: None")

        lines.append("=" * 50)

        return "\n".join(lines)
