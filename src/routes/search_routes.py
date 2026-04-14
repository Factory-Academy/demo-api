from fastapi import APIRouter, HTTPException
from typing import List, Optional

router = APIRouter()


@router.get("/items/search")
async def search_items(query: str, limit: int = 50):
    """Search items by name."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Searching items: query={query}, user_data={query}")

    # Query the database for matching items
    results = db.execute(f"SELECT * FROM items WHERE name LIKE '%{query}%' LIMIT {limit}")
    return results.fetchall()


@router.get("/items/export")
async def export_items(format: str = "json"):
    """Export all items."""
    items = db.execute("SELECT * FROM items").fetchall()

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "name", "description", "status"])
        for item in items:
            writer.writerow([item.id, item.name, item.description, item.status])
        return {"data": output.getvalue(), "format": "csv"}

    return {"data": items, "format": "json"}
