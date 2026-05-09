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
import logging
import uuid
from datetime import datetime
from core.database import get_db
from core.config import settings
from models.schemas import ChatSession, ChatMessage
from controllers import template_controller

logger = logging.getLogger(__name__)


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


async def persist_agent_turn(
    session_id: str,
    messages: list,
    pre_loop_count: int,
    turn_capture: dict,
) -> None:
    """
    Write assistant + tool fragments from the in-memory agent turn to MongoDB.
    Called after run_loop (including on WebSocket disconnect mid-stream) so reload
    keeps the full conversation.

    Uses a single $push/$each so either the whole turn fragment list is stored or none,
    avoiding half-saved multi-step agent turns.
    """
    new_slice = messages[pre_loop_count:]
    if not new_slice:
        return

    last_ai_idx = None
    for idx, m in enumerate(new_slice):
        if m.get("role") == "assistant":
            last_ai_idx = idx

    docs: list[dict] = []
    for idx, m in enumerate(new_slice):
        role = m.get("role")
        if role == "assistant":
            is_last_ai = idx == last_ai_idx
            # Last assistant: cumulative turn thought + full tool steps; earlier fragments: that iteration only.
            if is_last_ai:
                thought_val = (turn_capture.get("thought") or m.get("_thought") or "").strip() or None
            else:
                frag = (m.get("_thought") or "").strip()
                thought_val = frag or None
            msg_obj = ChatMessage(
                role="assistant",
                content=m.get("content", ""),
                thought=thought_val,
                steps=turn_capture.get("steps") if is_last_ai else None,
            )
            docs.append(msg_obj.model_dump())
        elif role == "tool":
            msg_obj = ChatMessage(
                role="tool",
                content=m.get("content", ""),
                tool_id=m.get("tool_id"),
            )
            docs.append(msg_obj.model_dump())

    if not docs:
        return

    db = get_db()
    result = await db.chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": docs}},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
    if result.matched_count == 0:
        logger.warning("persist_agent_turn: no session matched session_id=%s", session_id)
    else:
        logger.info(
            "persist_agent_turn: session=%s pushed %d messages (assistant/tool)",
            session_id,
            len(docs),
        )


async def delete_session(session_id: str) -> bool:
    db = get_db()
    result = await db.chat_sessions.delete_one({"session_id": session_id})
    return result.deleted_count > 0


def _is_observation_user_message(role: str, content: str) -> bool:
    return role == "user" and (content or "").startswith("OBSERVATION from")


def format_messages_for_ui(session: ChatSession) -> list[dict]:
    """
    One user bubble per real user message; one assistant bubble per turn with merged
    content/thought and tool steps (tool / legacy observation rows are folded in).
    """
    raw = [m for m in session.messages if m.role != "system"]
    out: list[dict] = []
    i = 0
    while i < len(raw):
        m = raw[i]
        if m.role == "user" and not _is_observation_user_message(m.role, m.content):
            out.append({"role": "user", "content": m.content})
            i += 1
            contents: list[str] = []
            thoughts: list[str] = []
            steps_val = None
            tool_rows: list[dict] = []
            while i < len(raw):
                row = raw[i]
                if row.role == "user" and not _is_observation_user_message(row.role, row.content):
                    break
                if row.role == "assistant":
                    contents.append(row.content or "")
                    thoughts.append(row.thought or "")
                    # Keep last explicit steps value (including empty list); do not treat [] as missing.
                    if getattr(row, "steps", None) is not None:
                        steps_val = row.steps
                elif row.role == "tool":
                    # Persisted tool observations (parallel to assistant.steps); used if steps missing.
                    tool_rows.append(
                        {
                            "name": row.tool_id or "tool",
                            "args": None,
                            "result": row.content or "",
                            "status": "completed",
                        }
                    )
                i += 1
            # Prefer structured steps on assistant; fall back to replaying tool rows from DB.
            if (not steps_val or len(steps_val) == 0) and tool_rows:
                steps_val = tool_rows
            elif steps_val is None:
                steps_val = []
            # Emit assistant bubble if there is text, steps, or tool rows (avoid dropping tool-only turns).
            if contents or (steps_val and len(steps_val) > 0) or tool_rows:
                out.append(
                    {
                        "role": "assistant",
                        "content": "\n\n".join(c for c in contents if c).strip(),
                        "thought": "".join(t for t in thoughts if t),
                        "steps": steps_val if (steps_val and len(steps_val) > 0) else [],
                    }
                )
        elif m.role in ("tool",) or _is_observation_user_message(m.role, m.content):
            i += 1
        elif m.role == "assistant":
            out.append(
                {
                    "role": "assistant",
                    "content": m.content or "",
                    "thought": m.thought or "",
                    "steps": getattr(m, "steps", None) or [],
                }
            )
            i += 1
        else:
            i += 1
    return out


async def get_history_payload(session: ChatSession) -> str:
    from core.json_utils import json_dumps

    history = format_messages_for_ui(session)
    return json_dumps({"type": "history", "messages": history})


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
        if m.role == "system":
            continue
        if m.role == "tool":
            tid = m.tool_id or "tool"
            messages.append(
                {
                    "role": "user",
                    "content": f"OBSERVATION from {tid}:\n{m.content}",
                }
            )
        else:
            messages.append({"role": m.role, "content": m.content})

    return messages
