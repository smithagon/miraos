import json
import ollama
from typing import AsyncGenerator
from core.config import settings


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
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)

        try:
            stream = await client.chat(
                model=settings.MODEL_NAME,
                messages=messages,
                stream=True,
            )
        except Exception as exc:
            yield json.dumps({"type": "error", "content": f"Ollama error: {exc}"})
            yield json.dumps({"type": "done"})
            return

        buffer = ""
        in_thought = False
        full_chat = ""
        full_thought = ""

        async for chunk in stream:
            token = chunk["message"]["content"]
            buffer += token

            # ── Open thought tag ──────────────────────────────────────────
            if "<thought>" in buffer:
                pre, _, rest = buffer.partition("<thought>")
                if pre:
                    full_chat += pre
                    yield json.dumps({"type": "chat", "content": pre})
                in_thought = True
                buffer = rest

            # ── Close thought tag ─────────────────────────────────────────
            if "</thought>" in buffer:
                thought_text, _, rest = buffer.partition("</thought>")
                full_thought += thought_text
                yield json.dumps({"type": "thought", "content": thought_text})
                in_thought = False
                buffer = rest

            # ── Flush safe buffer ─────────────────────────────────────────
            if len(buffer) > 15 and "<" not in buffer[-10:]:
                if in_thought:
                    full_thought += buffer
                else:
                    full_chat += buffer
                yield json.dumps({"type": "thought" if in_thought else "chat", "content": buffer})
                buffer = ""

        # Flush remainder
        if buffer:
            if in_thought:
                full_thought += buffer
            else:
                full_chat += buffer
            yield json.dumps({"type": "thought" if in_thought else "chat", "content": buffer})

        yield json.dumps({"type": "done"})

        # Append assistant turn into the message list (mutates caller's list)
        messages.append({
            "role": "assistant",
            "content": full_chat,
            "_thought": full_thought,
        })
