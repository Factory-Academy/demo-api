from src.services.items import status


def test_empty_batch_results_returns_fresh_lists_each_call():
    first = status.empty_batch_results()
    first["updated"].append(1)
    first["failed"].append({"id": 2, "reason": "not found"})
    first["skipped"].append({"id": 3, "reason": "already in state"})

    second = status.empty_batch_results()

    assert second == {"updated": [], "failed": [], "skipped": []}
    assert second["updated"] is not first["updated"]
    assert second["failed"] is not first["failed"]
    assert second["skipped"] is not first["skipped"]


def test_empty_batch_results_copies_seed_lists():
    seed_updated = [1]
    seed_failed = [{"id": 2, "reason": "not found"}]
    seed_skipped = [{"id": 3, "reason": "already in state"}]

    results = status.empty_batch_results(
        updated=seed_updated,
        failed=seed_failed,
        skipped=seed_skipped,
    )
    results["updated"].append(99)
    results["failed"].append({"id": 4, "reason": "x"})
    results["skipped"].append({"id": 5, "reason": "y"})

    assert seed_updated == [1]
    assert seed_failed == [{"id": 2, "reason": "not found"}]
    assert seed_skipped == [{"id": 3, "reason": "already in state"}]
