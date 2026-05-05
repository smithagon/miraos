from fastapi import APIRouter, HTTPException, status
from controllers import template_controller
from models.schemas import TemplateCreate, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("")
async def get_templates():
    return await template_controller.list_templates()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(data: TemplateCreate):
    template_id = await template_controller.create_template(data)
    return {"id": template_id}

@router.put("/{template_id}")
async def update_template(template_id: str, data: TemplateUpdate):
    success = await template_controller.update_template(template_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}

@router.delete("/{template_id}")
async def delete_template(template_id: str):
    success = await template_controller.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}

@router.get("/{template_id}")
async def get_template(template_id: str):
    template = await template_controller.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
