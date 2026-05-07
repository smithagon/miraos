"""
View (route) layer for Chat — WebSocket + REST endpoints.

Pattern: Route → Controller → Service

REST:
  GET  /chat/sessions         – list all sessions
  POST /chat/sessions         – create a new session
  DELETE /chat/sessions/{id}  – delete a session

WebSocket:
  WS /chat/ws/{session_id}    – stream chat for a specific session
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from controllers import chat_controller
from services.llm_service import LLMService
from services.agent_service import AgentService
from models.schemas import ChatMessage, SessionCreate

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_MSG_LEN = 4000


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/sessions")
async def get_sessions():
    return await chat_controller.list_sessions()


@router.post("/sessions", status_code=201)
async def post_session(payload: SessionCreate):
    session = await chat_controller.create_session(payload.template_id)
    return {"session_id": session.session_id}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = await chat_controller.delete_session(session_id)
    return {"deleted": deleted}


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str, template_id: str = None):
    await websocket.accept()

    session = await chat_controller.get_or_create_session(session_id)
    history_payload = await chat_controller.get_history_payload(session)
    await websocket.send_text(history_payload)

    messages = await chat_controller.build_ollama_messages(session, template_id)

    try:
        while True:
            data = await websocket.receive_text()

            # ── Input validation ──────────────────────────────────────────
            if not data or len(data) > MAX_MSG_LEN:
                await websocket.send_text(json.dumps({"type": "error", "content": "Message too long."}))
                await websocket.send_text(json.dumps({"type": "done"}))
                continue

            # ── Persist user message ──────────────────────────────────────
            user_msg = ChatMessage(role="user", content=data)
            await chat_controller.save_message(session.session_id, user_msg)
            messages.append({"role": "user", "content": data})

            # ── Get Template and Permissions ──────────────────────────────
            effective_template_id = template_id or session.template_id
            allowed_tools = []
            context = {}
            if effective_template_id:
                template = await chat_controller.template_controller.get_template(effective_template_id)
                if template:
                    allowed_tools = template.get("allowed_tools", [])
                    if template.get("nl2sql_config"):
                        context["nl2sql_config"] = template["nl2sql_config"]

            # ── Stream Agentic Loop ───────────────────────────────────────
            async def on_payload(p: str):
                await websocket.send_text(p)

            # Record how many messages we have BEFORE the agent starts
            # (includes system prompt and the user message we just added)
            pre_loop_count = len(messages)

            await AgentService.run_loop(
                messages=messages,
                allowed_tools=allowed_tools,
                on_payload=on_payload,
                context=context
            )

            # ── Persist new agent turns (thoughts, tool results, etc.) ─────
            # AgentService.run_loop appends new turns to the 'messages' list.
            for m in messages[pre_loop_count:]:
                msg_obj = ChatMessage(
                    role=m["role"],
                    content=m["content"],
                    thought=m.get("_thought") or m.get("thought"),
                    tool_id=m.get("tool_id")
                )
                await chat_controller.save_message(session.session_id, msg_obj)

    except WebSocketDisconnect:
        print(f"[Chat WS] Client disconnected from session {session_id}.")
    except Exception as exc:
        print(f"[Chat WS] Error in session {session_id}: {exc}")
