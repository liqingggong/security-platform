"""
Test to verify the 10% progress issue is fixed.

This test directly calls check_and_aggregate with mocked data to verify
that it correctly sets status=COMPLETED when tasks finish.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


def test_check_and_aggregate_sets_completed():
    """
    Test that check_and_aggregate sets status=COMPLETED when all child tasks complete.
    """
    print("\n" + "="*60)
    print("Testing check_and_aggregate progress update")
    print("="*60)

    # Import after path setup
    from app.workers.tasks import check_and_aggregate, TaskStatus, _update_task

    # Mock task
    mock_task = Mock()
    mock_task.id = 999
    mock_task.tenant_id = 1
    mock_task.status = TaskStatus.RUNNING
    mock_task.input_data = {"enable": {"fofa": False, "hunter": True, "subfinder": True}}
    mock_task.started_at = datetime.utcnow()
    mock_task.created_at = datetime.utcnow()

    # Track _update_task calls
    update_calls = []
    def mock_update_task(task_id, **fields):
        update_calls.append((task_id, fields))
        print(f"  _update_task called: task_id={task_id}, fields={fields}")

    # Mock AsyncResult - simulates completed tasks
    class MockResult:
        def __init__(self, task_id, ready_val=True, successful_val=True, result_val=None):
            self._id = task_id
            self._ready = ready_val
            self._successful = successful_val
            self._result = result_val or {"search_records": [{"ip": "1.1.1.1"}], "inserted_count": 1}

        def ready(self):
            return self._ready

        def successful(self):
            return self._successful

        @property
        def result(self):
            return self._result

    # Mock database
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task

    # Patch all dependencies
    with patch('app.workers.tasks._db', return_value=mock_db):
        with patch('app.workers.tasks._update_task', side_effect=mock_update_task):
            with patch('app.workers.tasks._log_task'):
                with patch('app.workers.tasks.AsyncResult', side_effect=lambda cid, **kwargs: MockResult(cid)):
                    with patch('app.workers.tasks._aggregate_assets_from_sources', return_value=5):
                        with patch('app.workers.tasks._deduplicate_assets', return_value=0):
                            with patch('app.workers.tasks.aggregate_pipeline_results', return_value={"results": []}):
                                with patch('app.workers.tasks.DomainAggregationService'):
                                    with patch('app.workers.tasks.time.sleep'):  # Skip sleeps
                                        # Test with mock child task IDs
                                        child_task_ids = {
                                            "first": ["task1", "task2"],
                                            "second": [],
                                            "post": []
                                        }

                                        result = check_and_aggregate(999, child_task_ids, max_wait=10)

                                        print(f"\n  Result: {result}")
                                        print(f"\n  _update_task was called {len(update_calls)} times")

                                        # Find the final status update
                                        completed_calls = [c for c in update_calls if c[1].get('status') == TaskStatus.COMPLETED]
                                        progress_calls = [c for c in update_calls if c[1].get('progress') == 100]

                                        if completed_calls:
                                            print(f"\n  ✓ SUCCESS: status=COMPLETED was set!")
                                            print(f"    Calls: {completed_calls}")
                                            return True
                                        else:
                                            print(f"\n  ✗ FAILURE: status=COMPLETED was NOT set!")
                                            print(f"    All update calls: {update_calls}")
                                            return False


def test_run_pipeline_calls_check_and_aggregate():
    """
    Test that run_pipeline calls check_and_aggregate.delay.
    """
    print("\n" + "="*60)
    print("Testing run_pipeline calls check_and_aggregate")
    print("="*60)

    from app.workers.tasks import run_pipeline, TaskStatus

    mock_task = Mock()
    mock_task.id = 1000
    mock_task.tenant_id = 1
    mock_task.status = TaskStatus.PENDING
    mock_task.input_data = {}

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task

    check_and_aggregate_called = []

    def mock_delay(*args, **kwargs):
        check_and_aggregate_called.append((args, kwargs))
        print(f"  check_and_aggregate.delay called with args={args}, kwargs={kwargs}")

    with patch('app.workers.tasks._db', return_value=mock_db):
        with patch('app.workers.tasks._update_task'):
            with patch('app.workers.tasks._log_task'):
                with patch('app.workers.tasks.run_fofa_pull') as mock_fofa:
                    with patch('app.workers.tasks.run_hunter_pull') as mock_hunter:
                        with patch('app.workers.tasks.run_subfinder') as mock_subfinder:
                            with patch('app.workers.tasks.group'):
                                with patch('app.workers.tasks.check_and_aggregate') as mock_check:
                                    mock_check.delay = mock_delay

                                    payload = {
                                        "enable": {"hunter": True, "subfinder": True},
                                        "root_domains": ["example.com"],
                                        "hunter_query": 'domain="example.com"',
                                    }

                                    result = run_pipeline(1000, payload)

                                    print(f"\n  run_pipeline result: {result}")

                                    if check_and_aggregate_called:
                                        print(f"\n  ✓ SUCCESS: check_and_aggregate.delay was called!")
                                        return True
                                    else:
                                        print(f"\n  ✗ FAILURE: check_and_aggregate.delay was NOT called!")
                                        return False


def verify_fix_in_code():
    """
    Verify the fix is present in the code.
    """
    print("\n" + "="*60)
    print("Verifying fix in source code")
    print("="*60)

    tasks_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'workers', 'tasks.py')

    with open(tasks_file, 'r') as f:
        content = f.read()

    # Check for the fix
    check_lines = [
        ('status=TaskStatus.COMPLETED, progress=100', 'COMPLETED status setting'),
    ]

    all_found = True
    for pattern, description in check_lines:
        if pattern in content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_found = False

    return all_found


def main():
    print("\n" + "="*60)
    print("TESTING 10% PROGRESS ISSUE FIX")
    print("="*60)

    results = []

    # Test 1: Verify fix in code
    results.append(("Fix in code", verify_fix_in_code()))

    # Test 2: Test check_and_aggregate
    try:
        results.append(("check_and_aggregate sets COMPLETED", test_check_and_aggregate_sets_completed()))
    except Exception as e:
        print(f"\n  Error during test: {e}")
        import traceback
        traceback.print_exc()
        results.append(("check_and_aggregate sets COMPLETED", False))

    # Test 3: Test run_pipeline
    try:
        results.append(("run_pipeline calls check_and_aggregate", test_run_pipeline_calls_check_and_aggregate()))
    except Exception as e:
        print(f"\n  Error during test: {e}")
        import traceback
        traceback.print_exc()
        results.append(("run_pipeline calls check_and_aggregate", False))

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
        print("\n  🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n  ⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
