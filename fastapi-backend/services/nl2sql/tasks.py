import asyncio
from core.celery_app import celery_app
from .service import NL2SQLService
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="discover_and_index_task")
def discover_and_index_task(connection_string: str, db_id: str):
    """Celery task for database discovery and indexing."""
    # Since NL2SQLService is async, we need to run it in an event loop
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Pass actual mongo client to the service
    db = get_db()
    service = NL2SQLService(connection_string, db_id, db)
    
    logger.info(f"Starting background indexing for DB {db_id}")
    loop.run_until_complete(service.discover_and_index())
    logger.info(f"Background indexing completed for DB {db_id}")
    
    return {"status": "completed", "db_id": db_id}
