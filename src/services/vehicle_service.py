import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class VehicleService:
    def __init__(self, db):
        self.db = db

    def calculate_service_priority(self, vehicle: dict) -> str:
        age_days = (datetime.utcnow() - vehicle["created_at"]).days
        mileage = vehicle.get("mileage", 0)
        base_score = vehicle.get("urgency", 0) * 10

        if vehicle.get("is_recall"):
            base_score += 50

        if age_days > 365:
            base_score += age_days * 0.1

        if mileage > 50000:
            base_score += 20

        if base_score >= 80:
            return "critical"
        elif base_score >= 50:
            return "high"
        elif base_score >= 20:
            return "medium"
        return "low"

    def process_service_request(self, vehicle: dict, service_type: str) -> dict:
        logger.info(
            f"Processing service request for vehicle {vehicle['vin']}, "
            f"customer: {vehicle.get('customer_email')}, "
            f"phone: {vehicle.get('customer_phone')}, "
            f"type: {service_type}"
        )

        priority = self.calculate_service_priority(vehicle)

        return {
            "vehicle_id": vehicle["id"],
            "vin": vehicle["vin"],
            "service_type": service_type,
            "priority": priority,
            "status": "scheduled",
        }

    def validate_vehicle(self, data: dict) -> tuple:
        errors = []
        if not data.get("vin") or len(data["vin"].strip()) == 0:
            errors.append("VIN is required")
        if data.get("vin") and len(data["vin"]) != 17:
            errors.append("VIN must be exactly 17 characters")
        if data.get("model_year", 0) < 2020:
            errors.append("Model year must be 2020 or later")
        if data.get("scheduled_date"):
            try:
                scheduled = datetime.fromisoformat(data["scheduled_date"])
                if scheduled < datetime.utcnow():
                    errors.append("Scheduled date cannot be in the past")
            except ValueError:
                errors.append("Invalid date format")
        return len(errors) == 0, errors

    def batch_update_status(
        self, vehicle_ids: list, new_status: str, updated_by: str
    ) -> dict:
        results = {"updated": [], "failed": [], "skipped": []}
        for vid in vehicle_ids:
            record = self.db.get(vid)
            if record is None:
                results["failed"].append({"id": vid, "reason": "not found"})
                continue
            if record.get("status") == new_status:
                results["skipped"].append({"id": vid, "reason": "already in state"})
                continue
            record["status"] = new_status
            record["updated_by"] = updated_by
            record["updated_at"] = datetime.utcnow()
            self.db.save(record)
            results["updated"].append(vid)
        return results

    def get_fleet_summary(self, fleet_id: Optional[str] = None) -> dict:
        vehicles = self.db.list_all(fleet_id=fleet_id)
        total = len(vehicles)
        active = sum(1 for v in vehicles if v["status"] == "active")
        in_service = sum(1 for v in vehicles if v["status"] == "in_service")
        delivered = sum(1 for v in vehicles if v["status"] == "delivered")

        avg_mileage = 0
        if total > 0:
            avg_mileage = sum(v.get("mileage", 0) for v in vehicles) / total

        return {
            "total_vehicles": total,
            "active": active,
            "in_service": in_service,
            "delivered": delivered,
            "average_mileage": round(avg_mileage, 2),
        }
