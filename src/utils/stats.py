def success_rate(success_count: int, total_count: int) -> float:
    if total_count == 0:
        return 0.0
    return success_count / total_count
