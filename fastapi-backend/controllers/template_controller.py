from datetime import datetime
from bson import ObjectId
from core.database import get_db
from models.schemas import TemplateCreate, TemplateUpdate, PromptTemplate

async def list_templates() -> list[dict]:
    db = get_db()
    cursor = db.templates.find()
    templates = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        templates.append(doc)
    return templates

async def create_template(data: TemplateCreate) -> str:
    db = get_db()
    template_dict = data.model_dump()
    template_dict["created_at"] = datetime.utcnow()
    template_dict["updated_at"] = datetime.utcnow()
    result = await db.templates.insert_one(template_dict)
    return str(result.inserted_id)

async def update_template(template_id: str, data: TemplateUpdate) -> bool:
    db = get_db()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    result = await db.templates.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

async def delete_template(template_id: str) -> bool:
    db = get_db()
    result = await db.templates.delete_one({"_id": ObjectId(template_id)})
    return result.deleted_count > 0

async def get_template(template_id: str) -> dict | None:
    db = get_db()
    doc = await db.templates.find_one({"_id": ObjectId(template_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        return doc
    return None
