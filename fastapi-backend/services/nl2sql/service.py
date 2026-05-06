from typing import Dict, Any, Optional
from .discovery import DiscoveryService
from .metadata_manager import MetadataManager
from .tools import NL2SQLTools
from .agent import NL2SQLAgent
from .engine import ExecutionEngine

class NL2SQLService:
    def __init__(self, connection_string: str, db_id: str, mongo_client: Any):
        self.discovery = DiscoveryService(connection_string)
        self.metadata = MetadataManager(db_id, mongo_client)
        self.tools = NL2SQLTools(self.discovery, self.metadata)
        self.agent = NL2SQLAgent(self.tools)
        self.engine = ExecutionEngine(self.discovery)

    async def discover_and_index(self):
        """Runs the crawl and indexing. Designed to be called as a background task."""
        try:
            from services.llm_service import LLMService
            
            # 1. Fast: Crawl basic schema
            tables = []
            for table_name in self.discovery.get_all_tables():
                metadata = self.discovery.get_table_metadata(table_name)
                tables.append(metadata)
            
            # 2. Fast: Build relation graph and save initial snapshot
            relations = self.discovery.get_all_relations()
            await self.metadata.save_schema_snapshot(tables, relations, status="crawled")
            
            # 3. Slow: LLM Enrichment (Table Descriptions)
            for table in tables:
                prompt = (
                    f"Table Name: {table.name}\n"
                    f"Columns: {[c.name for c in table.columns]}\n"
                    f"Sample Data: {table.sample_data[:2]}\n\n"
                    "Provide a concise, 1-sentence description of what this table stores and its purpose in the business."
                )
                try:
                    table.description = await LLMService.generate_text(
                        prompt=prompt,
                        system="You are a data architect summarizing database schemas."
                    )
                except:
                    table.description = "AI generation in progress..."

            # Update with enriched descriptions and mark as enriched
            await self.metadata.save_schema_snapshot(tables, relations, status="enriched")
            
            # 4. Slow: Embedding generation
            await self.metadata.generate_embeddings(tables)
            
        except Exception as e:
            import logging
            logging.error(f"Background Indexing Failed: {e}")

    async def query(self, user_question: str) -> Dict[str, Any]:
        """Main entry point for answering a natural language question."""
        # 1. Agent generates SQL
        agent_result = await self.agent.run(user_question)
        
        if "error" in agent_result:
            return agent_result
        
        sql = agent_result["sql"]
        
        # 2. Engine executes SQL
        execution_result = await self.engine.execute(sql)
        
        # 3. Handle Retries (Simple implementation)
        if "error" in execution_result and execution_result.get("suggest_retry"):
            # Provide feedback to agent and try one more time
            feedback = f"The previous SQL failed with error: {execution_result['error']}. Please correct it."
            agent_result = await self.agent.run(f"{user_question}\n\nFEEDBACK: {feedback}")
            if "sql" in agent_result:
                execution_result = await self.engine.execute(agent_result["sql"])

        return {
            "query": user_question,
            "sql": sql,
            "explanation": agent_result.get("explanation"),
            "results": execution_result
        }
