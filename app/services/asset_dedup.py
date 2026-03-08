"""
Asset Deduplication Service.

This module provides functionality to deduplicate assets based on the
(domain, ip, port) triplet and merge their source information.
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict


def generate_asset_key(asset: Dict[str, Any]) -> str:
    """
    Generate a unique key string for an asset based on domain, ip, and port.

    The key format is: "domain|ip|port"
    - None domain/ip are converted to empty string
    - None port is converted to 0

    Args:
        asset: Asset dictionary containing domain, ip_address, and port fields

    Returns:
        Unique key string in format "domain|ip|port"
    """
    domain = asset.get("domain") or ""
    ip = asset.get("ip_address") or ""
    port = asset.get("port") or 0
    return f"{domain}|{ip}|{port}"


class AssetDedupService:
    """
    Service for deduplicating assets and merging source information.

    This service identifies duplicate assets based on the (domain, ip, port)
    triplet and merges their source information (sources list, discovered_by,
    and data fields) into a single aggregated asset.
    """

    def dedup_assets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate a list of assets based on (domain, ip, port) triplet.

        Duplicate assets are merged together, with their source information
        combined. Merged assets are marked with is_aggregated=True and
        aggregated_count indicating how many assets were merged.

        Args:
            assets: List of asset dictionaries

        Returns:
            List of deduplicated asset dictionaries
        """
        if not assets:
            return []

        # Group assets by key
        groups = self.find_duplicates(assets)

        # If no duplicates found, return original assets unchanged
        if not groups:
            return assets

        # Track which assets have been processed
        processed_keys = set()
        result = []

        for asset in assets:
            key = generate_asset_key(asset)
            if key in processed_keys:
                continue

            if key in groups:
                # Merge the group
                merged = self._merge_group(groups[key])
                if merged:
                    result.append(merged)
                processed_keys.add(key)
            else:
                # Unique asset, add as-is
                result.append(asset)
                processed_keys.add(key)

        return result

    def _merge_group(self, group: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Merge a group of duplicate assets into a single asset.

        Args:
            group: List of assets with the same (domain, ip, port) key

        Returns:
            Merged asset dictionary, or None if group is empty
        """
        if not group:
            return None

        if len(group) == 1:
            return group[0]

        # Select primary asset (most complete)
        primary = self._select_primary(group)

        # Merge with all other assets
        for asset in group:
            if asset is not primary:
                primary = self._merge_assets(primary, asset)

        # Mark as aggregated
        primary["is_aggregated"] = True
        primary["aggregated_count"] = len(group)

        return primary

    def _select_primary(self, assets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the most complete asset as the primary for merging.

        Scoring priority (in order):
        1. product presence
        2. banner presence
        3. protocol presence
        4. data presence (non-empty dict)

        Args:
            assets: List of assets to select from

        Returns:
            The most complete asset, or None if list is empty
        """
        if not assets:
            return None

        if len(assets) == 1:
            return assets[0]

        def score_asset(asset: Dict[str, Any]) -> int:
            """Calculate completeness score for an asset."""
            score = 0
            if asset.get("product"):
                score += 1000
            if asset.get("banner"):
                score += 100
            if asset.get("protocol"):
                score += 10
            if asset.get("data"):
                score += 1
            return score

        return max(assets, key=score_asset)

    def _merge_assets(
        self, primary: Dict[str, Any], other: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two assets' source information into the primary asset.

        Merging logic:
        1. Merge sources lists (using set to avoid duplicates)
        2. Merge discovered_by dict (combine counts)
        3. Merge data dict (keep all unique source data)
        4. Fill missing fields (product, banner) from other if primary is missing them

        Args:
            primary: Primary asset to merge into (will be modified)
            other: Other asset to merge from

        Returns:
            The merged primary asset
        """
        # Merge sources lists
        primary_sources = set(primary.get("sources", []))
        other_sources = set(other.get("sources", []))
        primary["sources"] = sorted(list(primary_sources | other_sources))

        # Merge discovered_by dict
        primary_discovered = primary.get("discovered_by", {}) or {}
        other_discovered = other.get("discovered_by", {}) or {}

        merged_discovered = dict(primary_discovered)
        for source, info in other_discovered.items():
            if source in merged_discovered:
                # Combine counts
                existing_count = merged_discovered[source].get("count", 0)
                other_count = info.get("count", 0)
                merged_discovered[source]["count"] = existing_count + other_count
            else:
                merged_discovered[source] = info
        primary["discovered_by"] = merged_discovered

        # Merge data dict
        primary_data = primary.get("data", {}) or {}
        other_data = other.get("data", {}) or {}

        merged_data = dict(primary_data)
        for key, value in other_data.items():
            if key not in merged_data:
                merged_data[key] = value
        primary["data"] = merged_data

        # Fill missing fields
        if not primary.get("product") and other.get("product"):
            primary["product"] = other["product"]

        if not primary.get("banner") and other.get("banner"):
            primary["banner"] = other["banner"]

        return primary

    def calculate_duplicate_rate(self, assets: List[Dict[str, Any]]) -> float:
        """
        Calculate the duplicate rate for a list of assets.

        Duplicate rate = (total - unique) / total
        Returns a value between 0 and 1.

        Args:
            assets: List of asset dictionaries

        Returns:
            Duplicate rate as a float between 0 and 1
        """
        if not assets:
            return 0.0

        total = len(assets)
        unique_keys = set(generate_asset_key(asset) for asset in assets)
        unique = len(unique_keys)

        return (total - unique) / total

    def find_duplicates(
        self, assets: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find and return duplicate asset groups.

        Args:
            assets: List of asset dictionaries

        Returns:
            Dictionary mapping asset keys to lists of duplicate assets
            Only includes keys with 2 or more assets (actual duplicates)
        """
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for asset in assets:
            key = generate_asset_key(asset)
            groups[key].append(asset)

        # Filter to only include actual duplicates (2+ assets)
        return {key: group for key, group in groups.items() if len(group) > 1}
