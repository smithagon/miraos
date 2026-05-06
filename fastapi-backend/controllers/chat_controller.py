"""
Controller (business logic) for chat sessions.

Responsibilities:
  • list_sessions          – return all sessions sorted by latest
  • create_session         – create a brand new session with a unique id
  • get_or_create_session  – load/init a session from MongoDB by id
  • save_message           – persist a chat turn
  • delete_session         – remove a session
  • get_history_payload    – format history for the frontend
  • build_ollama_messages  – shape messages for the Ollama API
"""

import json
import uuid
from datetime import datetime
from core.database import get_db
from core.config import settings
from models.schemas import ChatSession, ChatMessage
from controllers import template_controller


async def list_sessions() -> list[dict]:
    """Return all sessions sorted by updated_at descending (excluding full messages)."""
    db = get_db()
    cursor = db.chat_sessions.find(
        {},
        {"session_id": 1, "template_id": 1, "title": 1, "updated_at": 1, "created_at": 1, "messages": {"$slice": 2}},
    ).sort("updated_at", -1)
    sessions = []
    async for doc in cursor:
        doc.pop("_id", None)
        # Derive a title from the first user message
        first_user = next(
            (m for m in doc.get("messages", []) if m.get("role") == "user"), None
        )
        preview = (first_user["content"][:60] + "…") if first_user and len(first_user["content"]) > 60 else (first_user["content"] if first_user else "New Chat")
        
        template_name = "Default"
        if doc.get("template_id"):
            template = await template_controller.get_template(doc["template_id"])
            if template:
                template_name = template.get("name", "Default")

        sessions.append({
            "session_id": doc["session_id"],
            "template_id": doc.get("template_id"),
            "template_name": template_name,
            "title": doc.get("title") or preview,
            "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
        })
    return sessions


async def create_session(template_id: str = None) -> ChatSession:
    """Create a fresh session with a unique id and persist it."""
    db = get_db()
    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        template_id=template_id,
        messages=[ChatMessage(role="system", content=settings.SYSTEM_PROMPT)],
    )
    await db.chat_sessions.insert_one(session.model_dump())
    return session


async def get_or_create_session(session_id: str) -> ChatSession:
    db = get_db()
    doc = await db.chat_sessions.find_one({"session_id": session_id})
    if doc:
        doc.pop("_id", None)
        return ChatSession(**doc)
    # If the requested session doesn't exist, create a new one with that id
    session = ChatSession(
        session_id=session_id,
        messages=[ChatMessage(role="system", content=settings.SYSTEM_PROMPT)],
    )
    await db.chat_sessions.insert_one(session.model_dump())
    return session


async def save_message(session_id: str, msg: ChatMessage):
    db = get_db()
    await db.chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": msg.model_dump()},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


async def delete_session(session_id: str) -> bool:
    db = get_db()
    result = await db.chat_sessions.delete_one({"session_id": session_id})
    return result.deleted_count > 0


async def get_history_payload(session: ChatSession) -> str:
    history = [
        {"role": m.role, "content": m.content, "thought": m.thought}
        for m in session.messages
        if m.role != "system"
    ]
    return json.dumps({"type": "history", "messages": history})


async def build_ollama_messages(session: ChatSession, template_id: str = None) -> list:
    messages = []
    
    # ── Handle Template / System Prompt ──────────────────────────────────────
    system_prompt = settings.SYSTEM_PROMPT
    
    # Priority: template_id passed to build (from WS) > template_id stored in session
    effective_template_id = template_id or session.template_id
    
    if effective_template_id:
        template = await template_controller.get_template(effective_template_id)
        if template and template.get("base_prompt"):
            system_prompt = template["base_prompt"]
    
    messages.append({"role": "system", "content": system_prompt})
    
    # ── Append Session Messages (excluding existing system messages) ─────────
    for m in session.messages:
        if m.role != "system":
            messages.append({"role": m.role, "content": m.content})
            
    return messages
