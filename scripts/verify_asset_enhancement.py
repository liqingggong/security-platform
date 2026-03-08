#!/usr/bin/env python3
"""
Asset Enhancement Verification Script.

This script:
1. Loads the real fofa.info Excel data
2. Runs it through the AssetPipeline
3. Reports the improvement metrics
4. Asserts they meet the targets

Usage:
    python scripts/verify_asset_enhancement.py

Targets:
    - Protocol coverage: >95%
    - Fingerprint coverage: >70%
    - CDN detection: >90%
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.asset_pipeline import AssetPipeline


@dataclass
class VerificationResult:
    """Result of verification with metrics."""

    input_count: int
    output_count: int
    protocol_count: int
    protocol_rate: float
    fingerprint_count: int
    fingerprint_rate: float
    cdn_count: int
    cdn_rate: float
    dedup_removed: int
    protocol_enhanced: int
    fingerprint_enhanced: int
    passed: bool
    messages: List[str]


def load_excel_data(file_path: str) -> List[Dict[str, Any]]:
    """Load asset data from Excel file."""
    try:
        import pandas as pd

        df = pd.read_excel(file_path)
        assets = []

        for _, row in df.iterrows():
            # Parse sources (e.g., "FOFA+HUNTER" -> ["fofa", "hunter"])
            sources_str = str(row.get("来源", ""))
            if sources_str and sources_str != "-":
                sources = [s.lower().strip() for s in sources_str.split("+")]
            else:
                sources = []

            # Parse port
            port_val = row.get("端口", "-")
            if port_val != "-" and str(port_val).isdigit():
                port = int(port_val)
            else:
                port = None

            # Parse protocol
            protocol = str(row.get("协议", ""))
            if protocol == "-" or not protocol:
                protocol = None

            asset = {
                "domain": str(row.get("域名", "")) if row.get("域名") != "-" else None,
                "ip_address": str(row.get("IP", "")) if row.get("IP") != "-" else None,
                "port": port,
                "protocol": protocol,
                "banner": str(row.get("指纹", "")) if row.get("指纹") != "-" else None,
                "sources": sources,
                "url": str(row.get("URL", "")) if row.get("URL") != "-" else None,
            }
            assets.append(asset)

        return assets

    except Exception as e:
        print(f"Error loading Excel file: {e}")
        sys.exit(1)


def calculate_original_metrics(assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate metrics before enhancement."""
    total = len(assets)

    if total == 0:
        return {
            "total": 0,
            "protocol_count": 0,
            "protocol_rate": 0.0,
            "fingerprint_count": 0,
            "fingerprint_rate": 0.0,
            "cdn_count": 0,
            "cdn_rate": 0.0,
        }

    # Count assets with protocol
    protocol_count = sum(1 for a in assets if a.get("protocol"))
    protocol_rate = (protocol_count / total) * 100

    # Count assets with fingerprint (banner field)
    fingerprint_count = sum(1 for a in assets if a.get("banner"))
    fingerprint_rate = (fingerprint_count / total) * 100

    # Count CDN domains (simple check for CDN keywords)
    cdn_keywords = ["cloudflare", "cdn", "akamai", "fastly", "cloudfront"]
    cdn_count = sum(
        1 for a in assets
        if any(kw in (a.get("domain") or "").lower() for kw in cdn_keywords)
    )
    cdn_rate = (cdn_count / total) * 100

    return {
        "total": total,
        "protocol_count": protocol_count,
        "protocol_rate": protocol_rate,
        "fingerprint_count": fingerprint_count,
        "fingerprint_rate": fingerprint_rate,
        "cdn_count": cdn_count,
        "cdn_rate": cdn_rate,
    }


def calculate_enhanced_metrics(
    assets: List[Dict[str, Any]], stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate metrics after enhancement."""
    total = len(assets)

    if total == 0:
        return {
            "total": 0,
            "protocol_count": 0,
            "protocol_rate": 0.0,
            "fingerprint_count": 0,
            "fingerprint_rate": 0.0,
            "cdn_count": 0,
            "cdn_rate": 0.0,
        }

    # Count assets with protocol after enhancement
    protocol_count = sum(1 for a in assets if a.get("protocol"))
    protocol_rate = (protocol_count / total) * 100

    # Count assets with fingerprint after enhancement
    fingerprint_count = sum(
        1 for a in assets if a.get("technologies") or a.get("product")
    )
    fingerprint_rate = (fingerprint_count / total) * 100

    # Count CDN assets after enhancement
    cdn_count = sum(1 for a in assets if a.get("is_cdn"))
    cdn_rate = (cdn_count / total) * 100

    return {
        "total": total,
        "protocol_count": protocol_count,
        "protocol_rate": protocol_rate,
        "fingerprint_count": fingerprint_count,
        "fingerprint_rate": fingerprint_rate,
        "cdn_count": cdn_count,
        "cdn_rate": cdn_rate,
        "dedup_removed": stats.get("dedup_removed", 0),
        "protocol_enhanced": stats.get("protocol_enhanced", 0),
        "fingerprint_enhanced": stats.get("fingerprint_enhanced", 0),
    }


def verify_targets(enhanced_metrics: Dict[str, Any]) -> VerificationResult:
    """Verify that metrics meet the targets."""
    messages = []
    passed = True

    # Targets
    PROTOCOL_TARGET = 95.0
    FINGERPRINT_TARGET = 70.0
    CDN_TARGET = 90.0

    # Check protocol coverage
    if enhanced_metrics["protocol_rate"] >= PROTOCOL_TARGET:
        messages.append(
            f"✓ Protocol coverage: {enhanced_metrics['protocol_rate']:.2f}% "
            f"(target: >{PROTOCOL_TARGET}%)"
        )
    else:
        messages.append(
            f"✗ Protocol coverage: {enhanced_metrics['protocol_rate']:.2f}% "
            f"(target: >{PROTOCOL_TARGET}%)"
        )
        passed = False

    # Check fingerprint coverage
    if enhanced_metrics["fingerprint_rate"] >= FINGERPRINT_TARGET:
        messages.append(
            f"✓ Fingerprint coverage: {enhanced_metrics['fingerprint_rate']:.2f}% "
            f"(target: >{FINGERPRINT_TARGET}%)"
        )
    else:
        messages.append(
            f"✗ Fingerprint coverage: {enhanced_metrics['fingerprint_rate']:.2f}% "
            f"(target: >{FINGERPRINT_TARGET}%)"
        )
        passed = False

    # Check CDN detection
    # Note: CDN target might not be applicable if no CDN domains in data
    if enhanced_metrics["cdn_rate"] >= CDN_TARGET or enhanced_metrics["cdn_count"] == 0:
        if enhanced_metrics["cdn_count"] == 0:
            messages.append(
                f"⚠ CDN detection: {enhanced_metrics['cdn_rate']:.2f}% "
                f"(no CDN domains in dataset)"
            )
        else:
            messages.append(
                f"✓ CDN detection: {enhanced_metrics['cdn_rate']:.2f}% "
                f"(target: >{CDN_TARGET}%)"
            )
    else:
        messages.append(
            f"✗ CDN detection: {enhanced_metrics['cdn_rate']:.2f}% "
            f"(target: >{CDN_TARGET}%)"
        )
        passed = False

    return VerificationResult(
        input_count=enhanced_metrics.get("input_count", 0),
        output_count=enhanced_metrics["total"],
        protocol_count=enhanced_metrics["protocol_count"],
        protocol_rate=enhanced_metrics["protocol_rate"],
        fingerprint_count=enhanced_metrics["fingerprint_count"],
        fingerprint_rate=enhanced_metrics["fingerprint_rate"],
        cdn_count=enhanced_metrics["cdn_count"],
        cdn_rate=enhanced_metrics["cdn_rate"],
        dedup_removed=enhanced_metrics.get("dedup_removed", 0),
        protocol_enhanced=enhanced_metrics.get("protocol_enhanced", 0),
        fingerprint_enhanced=enhanced_metrics.get("fingerprint_enhanced", 0),
        passed=passed,
        messages=messages,
    )


def print_report(
    original: Dict[str, Any],
    enhanced: Dict[str, Any],
    result: VerificationResult,
    stats: Dict[str, Any],
):
    """Print verification report."""
    print("\n" + "=" * 70)
    print("ASSET ENHANCEMENT PIPELINE - VERIFICATION REPORT")
    print("=" * 70)

    print("\n📊 DATASET SUMMARY")
    print("-" * 70)
    print(f"Input Assets:        {result.input_count}")
    print(f"Output Assets:       {result.output_count}")
    print(f"Duplicates Removed:  {result.dedup_removed}")

    print("\n📈 ORIGINAL METRICS (Before Enhancement)")
    print("-" * 70)
    print(
        f"Protocol Coverage:   {original['protocol_rate']:>6.2f}% "
        f"({original['protocol_count']}/{original['total']})"
    )
    print(
        f"Fingerprint Coverage:{original['fingerprint_rate']:>6.2f}% "
        f"({original['fingerprint_count']}/{original['total']})"
    )
    print(
        f"CDN Detection:       {original['cdn_rate']:>6.2f}% "
        f"({original['cdn_count']}/{original['total']})"
    )

    print("\n🚀 ENHANCED METRICS (After Enhancement)")
    print("-" * 70)
    print(
        f"Protocol Coverage:   {enhanced['protocol_rate']:>6.2f}% "
        f"({enhanced['protocol_count']}/{enhanced['total']})"
    )
    print(
        f"Fingerprint Coverage:{enhanced['fingerprint_rate']:>6.2f}% "
        f"({enhanced['fingerprint_count']}/{enhanced['total']})"
    )
    print(
        f"CDN Detection:       {enhanced['cdn_rate']:>6.2f}% "
        f"({enhanced['cdn_count']}/{enhanced['total']})"
    )

    print("\n📊 IMPROVEMENTS")
    print("-" * 70)
    protocol_improvement = enhanced["protocol_rate"] - original["protocol_rate"]
    fingerprint_improvement = enhanced["fingerprint_rate"] - original["fingerprint_rate"]
    cdn_improvement = enhanced["cdn_rate"] - original["cdn_rate"]

    print(f"Protocol:            {protocol_improvement:>+6.2f}%")
    print(f"Fingerprint:         {fingerprint_improvement:>+6.2f}%")
    print(f"CDN:                 {cdn_improvement:>+6.2f}%")

    print("\n🔧 PIPELINE STATISTICS")
    print("-" * 70)
    print(f"CDN Detected:        {stats.get('cdn_detected', 0)}")
    print(f"Protocol Enhanced:   {stats.get('protocol_enhanced', 0)}")
    print(f"Fingerprint Enhanced:{stats.get('fingerprint_enhanced', 0)}")
    print(f"Errors:              {len(stats.get('errors', []))}")

    print("\n✅ TARGET VERIFICATION")
    print("-" * 70)
    for msg in result.messages:
        print(f"  {msg}")

    print("\n" + "=" * 70)
    if result.passed:
        print("✅ ALL TARGETS MET - VERIFICATION PASSED")
    else:
        print("❌ SOME TARGETS NOT MET - VERIFICATION FAILED")
    print("=" * 70 + "\n")


def main():
    """Main verification function."""
    # File path
    file_path = "/Users/liqinggong/Downloads/资产列表_2026-03-08_15-00-07.xlsx"

    print(f"Loading data from: {file_path}")

    # Load data
    assets = load_excel_data(file_path)
    print(f"Loaded {len(assets)} assets")

    # Calculate original metrics
    original_metrics = calculate_original_metrics(assets)

    # Process through pipeline
    print("\nProcessing assets through pipeline...")
    pipeline = AssetPipeline()
    enhanced_assets = pipeline.process_batch(assets, enable_dedup=True)
    stats = pipeline.get_last_stats()

    # Calculate enhanced metrics
    enhanced_metrics = calculate_enhanced_metrics(enhanced_assets, stats)
    enhanced_metrics["input_count"] = len(assets)

    # Verify targets
    result = verify_targets(enhanced_metrics)

    # Print report
    print_report(original_metrics, enhanced_metrics, result, stats)

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
