from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from services.nl2sql.tasks import discover_and_index_task
from services.nl2sql.service import NL2SQLService
from core.database import get_db

router = APIRouter(prefix="/nl2sql", tags=["nl2sql"])

class ConnectRequest(BaseModel):
    name: str
    connection_string: str

class QueryRequest(BaseModel):
    db_id: str
    question: str
    connection_string: str

@router.post("/discover")
async def discover_database(req: ConnectRequest):
    """Register a new database and trigger queue-based discovery."""
    try:
        # Trigger Celery task
        task = discover_and_index_task.delay(req.connection_string, "mock_db_id")
        
        return {
            "status": "processing", 
            "task_id": task.id,
            "message": f"Discovery queued for {req.name}. This is now handled by a dedicated worker."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/query")
async def query_database(req: QueryRequest):
    """Answer a natural language question against a registered database."""
    try:
        service = NL2SQLService(req.connection_string, req.db_id, None)
        result = await service.query(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata")
async def get_metadata(connection_string: str):
    """
    Return indexed schema for mock_db_id.

    If Mongo has a snapshot but `tables` is empty (e.g. discovery ran with a bad host and
    saved nothing), we live-crawl using the template's connection_string so the UI can recover
    without manually clearing the collection.
    """
    try:
        db = get_db()
        doc = await db.nl2sql_metadata.find_one({"db_id": "mock_db_id"})
        cached_tables = (doc or {}).get("tables") or []
        cached_status = (doc or {}).get("status") if doc else None

        if cached_tables and len(cached_tables) > 0:
            return {
                "tables": cached_tables,
                "status": cached_status or "indexed",
            }

        service = NL2SQLService(connection_string, "mock_db_id", db)
        table_names = service.discovery.get_all_tables()
        metadata = [
            service.discovery.get_table_metadata(t).model_dump(mode="json")
            for t in table_names
        ]
        return {
            "tables": metadata,
            "status": "crawled",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
