import json
import ollama
from typing import AsyncGenerator
from core.config import settings
from core.json_utils import json_dumps


class LLMService:
    """Wraps Ollama streaming and parses <thought> tags."""

    @staticmethod
    async def generate_text(prompt: str, system: str = "") -> str:
        """Non-streaming generation for internal tasks."""
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            res = await client.chat(model=settings.MODEL_NAME, messages=messages)
            return res['message']['content']
        except Exception as e:
            return f"Error generating text: {e}"

    @staticmethod
    async def stream(messages: list) -> AsyncGenerator[str, None]:
        from services.agent_service import logger
        logger.info(f"LLM Stream starting with {len(messages)} messages")
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)

        try:
            chat_kwargs = {
                "model": settings.MODEL_NAME,
                "messages": messages,
                "stream": True,
            }
            if settings.OLLAMA_THINK:
                chat_kwargs["think"] = True
            stream = await client.chat(**chat_kwargs)
        except Exception as exc:
            yield json_dumps({"type": "error", "content": f"Ollama error: {exc}"})
            yield json_dumps({"type": "done"})
            return

        buffer = ""
        in_thought = False
        thought_close_tag = "</thought>"
        in_call = False
        call_name = ""
        full_chat = ""
        full_thought = ""

        async for chunk in stream:
            msg = chunk.message
            if isinstance(msg, dict):
                token = msg.get("content") or ""
                thinking_piece = msg.get("thinking") or ""
            else:
                token = msg.content or ""
                # Ollama “thinking” models (e.g. Qwen3) stream reasoning separately from `content`.
                thinking_piece = msg.thinking or ""
            if thinking_piece:
                full_thought += thinking_piece
                yield json_dumps({"type": "thought", "content": thinking_piece})

            if not token:
                continue

            buffer += token

            # ── Process Tags ──────────────────────────────────────────────
            while True:
                if not in_thought and not in_call:
                    # Look for opening tags
                    thought_idx = buffer.find("<thought>")
                    redacted_idx = buffer.find("<think>")
                    call_idx = buffer.find("<call:")
                    # Prefer earliest opener among thought-style tags
                    candidates = [
                        (thought_idx, "thought"),
                        (redacted_idx, "redacted_thinking"),
                    ]
                    candidates = [(i, k) for i, k in candidates if i != -1]
                    thought_kind = None
                    if candidates:
                        thought_idx, thought_kind = min(candidates, key=lambda x: x[0])
                    else:
                        thought_idx = -1
                    
                    # Find which one comes first
                    if thought_idx != -1 and (call_idx == -1 or thought_idx < call_idx):
                        # Start thought (plain or Qwen-style redacted block embedded in content)
                        pre = buffer[:thought_idx]
                        if pre:
                            full_chat += pre
                            yield json_dumps({"type": "chat", "content": pre})
                        in_thought = True
                        if thought_kind == "redacted_thinking":
                            thought_close_tag = "</think>"
                            buffer = buffer[thought_idx + len("<think>"):]
                        else:
                            thought_close_tag = "</thought>"
                            buffer = buffer[thought_idx + len("<thought>"):]
                        continue
                    elif call_idx != -1:
                        # Start call? check for name closing '>'
                        rest = buffer[call_idx + len("<call:"):]
                        if ">" in rest:
                            pre = buffer[:call_idx]
                            if pre:
                                full_chat += pre
                                yield json_dumps({"type": "chat", "content": pre})
                            
                            name, _, body = rest.partition(">")
                            call_name = name.strip()
                            in_call = True
                            buffer = body
                            continue
                        else:
                            # Wait for more data to get the tool name
                            break
                    else:
                        # No tags found, flush some safe buffer
                        if len(buffer) > 20:
                            safe_to_flush = buffer[:-15]
                            full_chat += safe_to_flush
                            yield json_dumps({"type": "chat", "content": safe_to_flush})
                            buffer = buffer[-15:]
                        break

                elif in_thought:
                    if thought_close_tag in buffer:
                        thought_text, _, rest = buffer.partition(thought_close_tag)
                        full_thought += thought_text
                        yield json_dumps({"type": "thought", "content": thought_text})
                        in_thought = False
                        buffer = rest
                        continue
                    else:
                        # Flush safe thought content
                        if len(buffer) > 20:
                            safe_to_flush = buffer[:-15]
                            full_thought += safe_to_flush
                            yield json_dumps({"type": "thought", "content": safe_to_flush})
                            buffer = buffer[-15:]
                        break

                elif in_call:
                    # Look for ANY closing call tag to be robust
                    # Standard: </call:name> or </call>
                    close_tag_generic = "</call"
                    if close_tag_generic in buffer:
                        # Find the actual closing '>'
                        close_idx = buffer.find(">", buffer.find(close_tag_generic))
                        if close_idx != -1:
                            args_text = buffer[:buffer.find(close_tag_generic)]
                            rest = buffer[close_idx + 1:]
                            
                            yield json_dumps({"type": "call", "name": call_name, "arguments": args_text.strip()})
                            in_call = False
                            call_name = ""
                            buffer = rest
                            continue
                        else:
                            # Wait for the closing '>'
                            break
                    else:
                        # Still collecting arguments
                        break

        # Final Flush
        if buffer:
            if in_thought:
                full_thought += buffer
                yield json_dumps({"type": "thought", "content": buffer})
            elif in_call:
                yield json_dumps({"type": "error", "content": "Tool call truncated."})
            else:
                full_chat += buffer
                yield json_dumps({"type": "chat", "content": buffer})

        # MUST run before yielding "done": AgentService breaks the async-for on "done", which
        # closes this generator before any code after the final yield would run — so the
        # assistant turn was never appended and nothing was persisted.
        messages.append({
            "role": "assistant",
            "content": full_chat,
            "_thought": full_thought,
        })

        yield json_dumps({"type": "done"})
