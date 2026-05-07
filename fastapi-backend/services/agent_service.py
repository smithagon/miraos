import json
import logging
import os
import inspect
from typing import List, Dict, Any, Callable, AsyncGenerator
from services.llm_service import LLMService
from services.tool_registry import tool_registry
from models.schemas import ChatMessage
from core.json_utils import json_dumps

logger = logging.getLogger(__name__)

class AgentService:
    @staticmethod
    async def run_loop(
        messages: List[Dict[str, Any]],
        allowed_tools: List[str],
        on_payload: Callable[[str], Any],
        max_iterations: int = 10,
        context: Dict[str, Any] = None
    ):
        """
        Orchestrates the Thought-Action-Observation loop.
        """
        iteration = 0
        
        # ── Inject Tool Definitions into System Prompt ──────────────────────
        available_tools = tool_registry.list_tools(allowed_tools)
        if available_tools:
            tool_instructions = "\n\nAVAILABLE TOOLS:\n"
            for t in available_tools:
                tool_instructions += f"- {t['name']}: {t['description']}\n  Parameters: {json_dumps(t['parameters'])}\n"
            
            tool_instructions += "\nTo use a tool, use the format: <call:tool_name>{\"arg\": \"val\"}</call:tool_name>\n"
            tool_instructions += "You MUST always provide a <thought> before a <call>.\n"
            
            # Find system message and append instructions
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] += tool_instructions
                    break

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent Loop Iteration {iteration}")

            full_chat = ""
            full_thought = ""
            active_tool_call = None

            async for payload in LLMService.stream(messages):
                await on_payload(payload)
                
                parsed = json.loads(payload)
                if parsed["type"] == "chat":
                    full_chat += parsed.get("content", "")
                elif parsed["type"] == "thought":
                    full_thought += parsed.get("content", "")
                elif parsed["type"] == "call":
                    active_tool_call = {
                        "name": parsed["name"],
                        "arguments": parsed["arguments"]
                    }
                elif parsed["type"] == "done":
                    break

            # If no tool was called, we are done
            if not active_tool_call:
                break

            # ── Execute Tool ────────────────────────────────────────────────
            tool_name = active_tool_call["name"]
            try:
                tool_args = json.loads(active_tool_call["arguments"])
            except Exception:
                tool_args = {}

            tool = tool_registry.get_tool(tool_name)
            if not tool or tool_name not in allowed_tools:
                observation = f"Error: Tool '{tool_name}' is not available or not permitted."
            else:
                # Add context (like DB config) if needed
                if context:
                    tool_args["_context"] = context
                
                logger.info(f"Executing tool: {tool_name} with {tool_args}")
                try:
                    if inspect.iscoroutinefunction(tool.func):
                        observation = await tool.func(tool_args)
                    else:
                        observation = tool.func(tool_args)
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    observation = f"Error executing tool {tool_name}: {e}"

            # ── Send Observation to Frontend ───────────────────────────────
            await on_payload(json_dumps({
                "type": "observation",
                "name": tool_name,
                "content": observation
            }))

            # ── Add to History and Continue Loop ────────────────────────────
            # The LLMService.stream already appended the assistant's turn
            # But we need to add the tool's result
            messages.append({
                "role": "user", # Using user role for observations for better compatibility
                "content": f"OBSERVATION from {tool_name}:\n{observation}",
                "tool_id": tool_name
            })

        await on_payload(json_dumps({"type": "done"}))
