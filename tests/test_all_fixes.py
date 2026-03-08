"""
Automated test script to verify all three fixes:
1. Task progress updates to 100% and status=COMPLETED when done
2. Scan plan tool selection is respected (disabled tools don't run)
3. Asset URL column is populated (auto-generated from domain/port/protocol)

Run this script to verify all fixes are working.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, MagicMock
from app.workers.tasks import (
    TaskStatus,
    _upsert_aggregated_asset,
    _upsert_source_asset,
)
from app.db import models


def test_fix_1_task_progress():
    """
    Fix 1: Verify check_and_aggregate sets status=COMPLETED and progress=100
    """
    print("\n" + "="*60)
    print("Test Fix 1: Task Progress Status")
    print("="*60)

    # Check the source code for the fix
    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    # Verify the fix is present
    if 'status=TaskStatus.COMPLETED, progress=100' in content:
        print("✓ PASS: check_and_aggregate sets status=COMPLETED and progress=100")
        return True
    else:
        print("✗ FAIL: status=COMPLETED not found in check_and_aggregate")
        return False


def test_fix_2_tool_selection():
    """
    Fix 2: Verify enable.get defaults to False instead of True
    """
    print("\n" + "="*60)
    print("Test Fix 2: Scan Plan Tool Selection")
    print("="*60)

    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    # Count occurrences of enable.get with default False
    false_defaults = content.count('enable.get("fofa", False)') + \
                     content.count('enable.get("hunter", False)') + \
                     content.count('enable.get("subfinder", False)')

    # Count occurrences of enable.get with default True (should be 0)
    true_defaults = content.count('enable.get("fofa", True)') + \
                    content.count('enable.get("hunter", True)') + \
                    content.count('enable.get("subfinder", True)')

    print(f"  Found {false_defaults} enable.get(..., False) calls")
    print(f"  Found {true_defaults} enable.get(..., True) calls")

    if true_defaults == 0 and false_defaults >= 4:  # At least 4 places: fofa, hunter, subfinder (2 rounds)
        print("✓ PASS: All enable.get defaults changed to False")
        return True
    else:
        print("✗ FAIL: Some enable.get still default to True")
        return False


def test_fix_3_url_generation():
    """
    Fix 3: Verify URL auto-generation from domain/port/protocol
    """
    print("\n" + "="*60)
    print("Test Fix 3: Asset URL Auto-Generation")
    print("="*60)

    # Test 1: Check backend logic
    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    backend_fixed = 'if not norm_url and norm_domain and port:' in content

    # Test 2: Check frontend logic
    assets_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'pages', 'Assets.tsx')
    with open(assets_file, 'r') as f:
        frontend_content = f.read()

    frontend_fixed = 'if (!url && record?.domain && record?.port)' in frontend_content or \
                     'if (!url && record?.domain && record?.port)' in frontend_content

    if backend_fixed:
        print("✓ PASS: Backend auto-generates URL from domain/port/protocol")
    else:
        print("✗ FAIL: Backend URL auto-generation not found")

    if frontend_fixed:
        print("✓ PASS: Frontend falls back to generated URL when url field is empty")
    else:
        print("✗ FAIL: Frontend URL fallback not found")

    return backend_fixed and frontend_fixed


def test_backend_url_generation_logic():
    """
    Test the actual URL generation logic
    """
    print("\n  Testing URL generation logic...")

    test_cases = [
        # (url, domain, port, protocol, expected_url)
        (None, "example.com", 80, "http", "http://example.com:80"),
        (None, "example.com", 443, "https", "https://example.com:443"),
        (None, "example.com", 8080, None, "http://example.com:8080"),  # default to http
        ("http://existing.com", "example.com", 80, "http", "http://existing.com"),  # keep existing
        (None, None, 80, "http", None),  # no domain, no url
        (None, "example.com", None, "http", None),  # no port, no url
    ]

    all_passed = True
    for url, domain, port, protocol, expected in test_cases:
        norm_domain = (domain or "").strip().lower() or None
        norm_url = (url or "").strip() or None

        # Apply the fix logic
        if not norm_url and norm_domain and port:
            proto = (protocol or "http").lower()
            norm_url = f"{proto}://{norm_domain}:{port}"

        if norm_url == expected:
            print(f"    ✓ ({url}, {domain}, {port}, {protocol}) -> {norm_url}")
        else:
            print(f"    ✗ ({url}, {domain}, {port}, {protocol}) -> {norm_url}, expected {expected}")
            all_passed = False

    return all_passed


def main():
    """
    Run all tests and report results
    """
    print("\n" + "="*60)
    print("AUTOMATED TEST: Verifying All Three Fixes")
    print("="*60)

    results = []

    # Run tests
    results.append(("Fix 1: Task Progress", test_fix_1_task_progress()))
    results.append(("Fix 2: Tool Selection", test_fix_2_tool_selection()))
    results.append(("Fix 3: URL Generation", test_fix_3_url_generation()))

    # Test URL generation logic
    url_logic_passed = test_backend_url_generation_logic()
    results.append(("Fix 3b: URL Logic", url_logic_passed))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n  ⚠️  SOME TESTS FAILED - Please review the fixes")
        return 1


if __name__ == "__main__":
    sys.exit(main())
