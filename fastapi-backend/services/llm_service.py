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
            stream = await client.chat(
                model=settings.MODEL_NAME,
                messages=messages,
                stream=True,
            )
        except Exception as exc:
            yield json_dumps({"type": "error", "content": f"Ollama error: {exc}"})
            yield json_dumps({"type": "done"})
            return

        buffer = ""
        in_thought = False
        in_call = False
        call_name = ""
        full_chat = ""
        full_thought = ""

        async for chunk in stream:
            token = chunk["message"]["content"]
            buffer += token

            # ── Process Tags ──────────────────────────────────────────────
            while True:
                if not in_thought and not in_call:
                    # Look for opening tags
                    thought_idx = buffer.find("<thought>")
                    call_idx = buffer.find("<call:")
                    
                    # Find which one comes first
                    if thought_idx != -1 and (call_idx == -1 or thought_idx < call_idx):
                        # Start thought
                        pre = buffer[:thought_idx]
                        if pre:
                            full_chat += pre
                            yield json_dumps({"type": "chat", "content": pre})
                        in_thought = True
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
                    if "</thought>" in buffer:
                        thought_text, _, rest = buffer.partition("</thought>")
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

        yield json_dumps({"type": "done"})

        # Append assistant turn into the message list (mutates caller's list)
        messages.append({
            "role": "assistant",
            "content": full_chat,
            "_thought": full_thought,
        })
