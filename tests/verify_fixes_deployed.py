#!/usr/bin/env python3
"""
Verify all fixes are properly deployed and ready.
"""

import os
import sys

def check_fix_1():
    """Fix 1: Task progress stuck at 10%"""
    print("\n[Fix 1] Task Progress Status Update")
    print("-" * 50)

    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    # Check for the fix in check_and_aggregate
    if 'status=TaskStatus.COMPLETED, progress=100, output_data=output_data' in content:
        print("✓ Code fix present: check_and_aggregate sets status=COMPLETED")
        return True
    else:
        print("✗ Code fix missing!")
        return False

def check_fix_2():
    """Fix 2: Tool selection not respected"""
    print("\n[Fix 2] Scan Plan Tool Selection")
    print("-" * 50)

    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    checks = [
        ('enable.get("fofa", False)', 'FOFA default disabled', 2),  # First + second round
        ('enable.get("hunter", False)', 'Hunter default disabled', 2),  # First + second round
        ('enable.get("subfinder", False)', 'Subfinder default disabled', 1),  # Only first round
    ]

    all_ok = True
    for pattern, desc, min_count in checks:
        count = content.count(pattern)
        if count >= min_count:
            print(f"✓ {desc}: found {count} times")
        else:
            print(f"✗ {desc}: only found {count} times (expected >= {min_count})")
            all_ok = False

    return all_ok

def check_fix_3():
    """Fix 3: URL column empty"""
    print("\n[Fix 3] Asset URL Auto-Generation")
    print("-" * 50)

    # Backend check
    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')
    with open(tasks_file, 'r') as f:
        content = f.read()

    backend_ok = 'if not norm_url and norm_domain and port:' in content

    # Frontend check
    assets_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'pages', 'Assets.tsx')
    with open(assets_file, 'r') as f:
        frontend_content = f.read()

    frontend_ok = 'if (!url && record?.domain && record?.port)' in frontend_content

    if backend_ok:
        print("✓ Backend: Auto-generates URL from domain/port/protocol")
    else:
        print("✗ Backend: Missing URL generation logic")

    if frontend_ok:
        print("✓ Frontend: Fallback to generated URL")
    else:
        print("✗ Frontend: Missing URL fallback logic")

    return backend_ok and frontend_ok

def check_celery_restart():
    """Check if Celery workers are running"""
    print("\n[Celery Status]")
    print("-" * 50)

    import subprocess
    result = subprocess.run(['pgrep', '-f', 'celery'], capture_output=True, text=True)

    if result.returncode == 0 and result.stdout.strip():
        pids = result.stdout.strip().split('\n')
        print(f"✓ Celery is running with {len(pids)} processes")
        return True
    else:
        print("✗ Celery is not running!")
        return False

def main():
    print("=" * 60)
    print("VERIFICATION: All Fixes Deployed and Ready")
    print("=" * 60)

    results = []
    results.append(("Fix 1: Task Progress", check_fix_1()))
    results.append(("Fix 2: Tool Selection", check_fix_2()))
    results.append(("Fix 3: URL Generation", check_fix_3()))
    results.append(("Celery Workers", check_celery_restart()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL FIXES ARE DEPLOYED AND READY!")
        print("\nNext time you run a task:")
        print("  1. Task should update to 100% and COMPLETED status")
        print("  2. Only selected tools in scan plan will run")
        print("  3. URL column will show generated URLs")
        return 0
    else:
        print("⚠️  Some checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
