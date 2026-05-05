"""
View (route) layer for Items CRUD REST endpoints.

Pattern: Route → Controller
"""

from fastapi import APIRouter, HTTPException
from controllers import items_controller
from models.schemas import ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def get_items():
    return await items_controller.list_items()


@router.post("/", status_code=201)
async def post_item(payload: ItemCreate):
    return await items_controller.create_item(payload)


@router.put("/{item_id}")
async def put_item(item_id: str, payload: ItemUpdate):
    item = await items_controller.update_item(item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/{item_id}")
async def del_item(item_id: str):
    deleted = await items_controller.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True}
