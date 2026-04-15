from datetime import datetime, timedelta
from typing import List, Optional


def validate_vin_checksum(vin: str) -> bool:
    if len(vin) != 17:
        return False

    transliteration = {
        "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
        "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
        "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
    }
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

    total = 0
    for i, char in enumerate(vin.upper()):
        if char.isdigit():
            value = int(char)
        else:
            value = transliteration.get(char, 0)
        total += value * weights[i]

    check_digit = total % 11
    expected = "X" if check_digit == 10 else str(check_digit)
    return vin[8] == expected


def calculate_service_window(
    last_service_date: str,
    mileage: int,
    service_interval_miles: int = 7500,
) -> dict:
    last_service = datetime.fromisoformat(last_service_date)

    miles_until_service = service_interval_miles - (mileage % service_interval_miles)

    avg_daily_miles = 35
    days_until_service = miles_until_service / avg_daily_miles

    next_service_date = last_service + timedelta(days=days_until_service)

    if next_service_date < datetime.utcnow():
        return {
            "status": "overdue",
            "next_service_date": next_service_date.isoformat(),
            "miles_remaining": miles_until_service,
            "days_overdue": (datetime.utcnow() - next_service_date).days,
        }

    return {
        "status": "upcoming",
        "next_service_date": next_service_date.isoformat(),
        "miles_remaining": miles_until_service,
        "days_remaining": (next_service_date - datetime.utcnow()).days,
    }


def batch_schedule_appointments(
    vehicles: List[dict],
    service_type: str,
    max_per_day: int = 10,
    start_date: Optional[str] = None,
) -> List[dict]:
    if start_date:
        current_date = datetime.fromisoformat(start_date)
    else:
        current_date = datetime.utcnow()

    scheduled = []
    day_count = 0

    for i, vehicle in enumerate(vehicles):
        if i > 0 and i % max_per_day == 0:
            day_count += 1
            current_date = current_date + timedelta(days=1)

            if current_date.weekday() >= 5:
                current_date = current_date + timedelta(
                    days=7 - current_date.weekday()
                )

        scheduled.append({
            "vehicle_id": vehicle["id"],
            "vin": vehicle["vin"],
            "service_type": service_type,
            "scheduled_date": current_date.isoformat(),
            "slot": i % max_per_day,
        })

    return scheduled


def estimate_migration_effort(
    service_count: int,
    avg_endpoints_per_service: int = 8,
    complexity_factor: float = 1.0,
) -> dict:
    base_hours_per_endpoint = 4
    testing_multiplier = 1.5
    infra_setup_hours = 16

    total_endpoints = service_count * avg_endpoints_per_service
    dev_hours = total_endpoints * base_hours_per_endpoint * complexity_factor
    test_hours = dev_hours * testing_multiplier
    total_hours = dev_hours + test_hours + (infra_setup_hours * service_count)

    engineer_weeks = total_hours / 40
    recommended_team_size = max(2, min(service_count // 3, 8))
    calendar_weeks = engineer_weeks / recommended_team_size

    return {
        "total_endpoints": total_endpoints,
        "estimated_dev_hours": round(dev_hours),
        "estimated_test_hours": round(test_hours),
        "total_hours": round(total_hours),
        "engineer_weeks": round(engineer_weeks, 1),
        "recommended_team_size": recommended_team_size,
        "estimated_calendar_weeks": round(calendar_weeks, 1),
    }
