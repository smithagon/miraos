import os
import json
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from core.json_utils import json_dumps
from services.terminal_service import TerminalService
from services.nl2sql.discovery import DiscoveryService
from services.nl2sql.engine import ExecutionEngine

class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        self.tools[name] = Tool(name, description, parameters, func)

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self, filter_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if filter_list is None:
            return [t.to_dict() for t in self.tools.values()]
        return [t.to_dict() for name, t in self.tools.items() if name in filter_list]

    def _register_default_tools(self):
        # ── Terminal Tool ───────────────────────────────────────────────────
        self.register(
            name="execute_command",
            description="Execute a shell command in the local terminal. Use for system inspection, installing dependencies, or running scripts.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to run."}
                },
                "required": ["command"]
            },
            func=self._execute_command_wrapper
        )

        # ── File System Tools ──────────────────────────────────────────────
        self.register(
            name="list_dir",
            description="List the contents of a directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the directory (defaults to current dir)."}
                }
            },
            func=self._list_dir_wrapper
        )

        self.register(
            name="read_file",
            description="Read the contents of a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file."}
                },
                "required": ["path"]
            },
            func=self._read_file_wrapper
        )

        # ── NL2SQL Tools ────────────────────────────────────────────────────
        self.register(
            name="get_db_schema",
            description="Get the full schema of the connected database, including tables and columns.",
            parameters={"type": "object", "properties": {}},
            func=self._get_db_schema_wrapper
        )

        self.register(
            name="execute_sql",
            description="Execute a read-only SQL query against the database.",
            parameters={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "The SQL query to execute."}
                },
                "required": ["sql"]
            },
            func=self._execute_sql_wrapper
        )

    # ── Tool Wrappers ───────────────────────────────────────────────────────
    
    @staticmethod
    def _execute_command_wrapper(args: Dict[str, Any]) -> str:
        cmd = args.get("command")
        if not cmd:
            return "Error: No command provided."
        result = TerminalService.execute(cmd)
        return json_dumps(result)

    @staticmethod
    def _list_dir_wrapper(args: Dict[str, Any]) -> str:
        path = args.get("path", ".")
        try:
            items = os.listdir(path)
            return json_dumps({"items": items, "path": os.path.abspath(path)})
        except Exception as e:
            return json_dumps({"error": str(e)})

    @staticmethod
    def _read_file_wrapper(args: Dict[str, Any]) -> str:
        path = args.get("path")
        try:
            with open(path, "r") as f:
                content = f.read()
            return content
        except Exception as e:
            return json_dumps({"error": str(e)})

    @staticmethod
    def _get_db_schema_wrapper(args: Dict[str, Any]) -> str:
        context = args.get("_context", {})
        config = context.get("nl2sql_config")
        if not config or not config.get("connection_string"):
            return "Error: No database connection configured for this template."
        
        try:
            discovery = DiscoveryService(config["connection_string"])
            tables = discovery.get_all_tables()
            schema = {}
            for t in tables:
                meta = discovery.get_table_metadata(t)
                schema[t] = meta.model_dump()
            return json_dumps(schema)
        except Exception as e:
            return json_dumps({"error": str(e)})

    @staticmethod
    async def _execute_sql_wrapper(args: Dict[str, Any]) -> str:
        # Note: Since this is called from AgentService which is async, we can make this async if needed
        # But ToolRegistry.func is currently sync. I'll make it handle both or just use run_in_executor
        context = args.get("_context", {})
        config = context.get("nl2sql_config")
        sql = args.get("sql")
        
        if not config or not config.get("connection_string"):
            return "Error: No database connection configured for this template."
        if not sql:
            return "Error: No SQL query provided."
            
        try:
            discovery = DiscoveryService(config["connection_string"])
            engine = ExecutionEngine(discovery)
            # engine.execute is async, so we'd need to await it
            # For simplicity in this step, I'll update AgentService to handle async tools
            result = await engine.execute(sql)
            return json_dumps(result)
        except Exception as e:
            return json_dumps({"error": str(e)})

# Singleton instance
tool_registry = ToolRegistry()
