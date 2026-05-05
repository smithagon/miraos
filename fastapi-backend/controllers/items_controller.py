"""
Controller (business logic) for the Items CRUD entity.

Responsibilities:
  • list_items   – fetch all items from MongoDB
  • create_item  – insert a new item
  • update_item  – patch an existing item by id
  • delete_item  – remove an item by id
"""

from datetime import datetime
from bson import ObjectId
from core.database import get_db
from models.schemas import ItemCreate, ItemUpdate


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


async def list_items() -> list:
    db = get_db()
    cursor = db.items.find().sort("created_at", -1)
    return [_serialize(d) async for d in cursor]


async def create_item(payload: ItemCreate) -> dict:
    db = get_db()
    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.items.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def update_item(item_id: str, payload: ItemUpdate) -> dict | None:
    db = get_db()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    doc = await db.items.find_one_and_update(
        {"_id": ObjectId(item_id)},
        {"$set": update_data},
        return_document=True,
    )
    return _serialize(doc) if doc else None


async def delete_item(item_id: str) -> bool:
    db = get_db()
    result = await db.items.delete_one({"_id": ObjectId(item_id)})
    return result.deleted_count > 0
