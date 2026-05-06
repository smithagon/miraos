import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy import text
from .discovery import DiscoveryService

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self, discovery_service: DiscoveryService):
        self.discovery = discovery_service

    def validate_sql(self, sql: str) -> Tuple[bool, str]:
        """Performs safety checks on the generated SQL."""
        forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"]
        
        # Simple keyword check
        upper_sql = sql.upper()
        for kw in forbidden_keywords:
            if kw in upper_sql:
                return False, f"Security Violation: '{kw}' keyword is not allowed."
        
        # Check if it starts with SELECT
        if not upper_sql.strip().startswith("SELECT"):
            return False, "Only SELECT queries are allowed."

        return True, ""

    async def execute(self, sql: str) -> Dict[str, Any]:
        """Executes the SQL and returns results, with self-correction logic."""
        is_valid, error_msg = self.validate_sql(sql)
        if not is_valid:
            return {"error": error_msg}

        try:
            with self.discovery.engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                
                return {
                    "columns": list(columns),
                    "data": data,
                    "row_count": len(data)
                }
        except Exception as e:
            logger.error(f"Database Execution Error: {e}")
            return {
                "error": str(e),
                "suggest_retry": True
            }
