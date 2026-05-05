from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

class _DB:
    client: AsyncIOMotorClient = None
    db = None

_state = _DB()

def connect():
    _state.client = AsyncIOMotorClient(settings.MONGO_URI)
    _state.db = _state.client[settings.DB_NAME]
    print(f"[DB] Connected to MongoDB → {settings.DB_NAME}")

def disconnect():
    if _state.client:
        _state.client.close()
        print("[DB] MongoDB connection closed.")

def get_db():
    return _state.db
