import json
import logging
import ollama
from typing import List, Dict, Any, Optional
from .tools import NL2SQLTools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert SQL Generator for Mira OS. 
Your goal is to answer natural language questions by generating accurate SQL queries.
You have access to a set of tools to explore the database schema and data.

TOOLS:
- get_relevant_tables(query: str): Returns a list of tables related to the query.
- get_table_schema(table_name: str): Returns column details for a table.
- get_table_relations(table_names: List[str]): Returns join paths between tables.
- get_sample_values(table_name: str): Returns sample rows from a table.

PROCESS:
1. Identify relevant tables.
2. Examine schemas and relations.
3. Plan the SQL query (JOINs, WHERE, GROUP BY).
4. Generate the SQL.

Always return your response in JSON format:
{
  "thought": "Your reasoning process",
  "tool_call": {"name": "tool_name", "args": {...}} | null,
  "sql": "The final SQL query" | null,
  "explanation": "Brief explanation of the SQL" | null
}
"""

class NL2SQLAgent:
    def __init__(self, tools: NL2SQLTools, model: str = "qwen3:8b"):
        self.tools = tools
        self.model = model

    async def run(self, user_query: str, max_iterations: int = 5) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]

        for i in range(max_iterations):
            try:
                response = ollama.chat(model=self.model, messages=messages, format="json")
                content = json.loads(response["message"]["content"])
                
                logger.info(f"Iteration {i}: {content.get('thought')}")

                # If the agent wants to call a tool
                if content.get("tool_call"):
                    tool_name = content["tool_call"]["name"]
                    tool_args = content["tool_call"]["args"]
                    
                    # Dispatch tool call
                    result = self._call_tool(tool_name, tool_args)
                    
                    messages.append({"role": "assistant", "content": json.dumps(content)})
                    messages.append({"role": "user", "content": f"Tool Result ({tool_name}): {json.dumps(result)}"})
                    continue
                
                # If the agent has generated the SQL
                if content.get("sql"):
                    return {
                        "sql": content["sql"],
                        "explanation": content.get("explanation"),
                        "thought": content.get("thought")
                    }

            except Exception as e:
                logger.error(f"Error in agentic loop: {e}")
                break

        return {"error": "Failed to generate SQL within iteration limit."}

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name == "get_relevant_tables":
            return self.tools.get_relevant_tables(args["query"])
        elif name == "get_table_schema":
            return self.tools.get_table_schema(args["table_name"])
        elif name == "get_table_relations":
            return self.tools.get_table_relations(args["table_names"])
        elif name == "get_sample_values":
            return self.tools.get_sample_values(args["table_name"])
        else:
            return f"Unknown tool: {name}"
