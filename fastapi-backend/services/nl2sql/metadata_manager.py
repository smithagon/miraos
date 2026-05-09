import networkx as nx
from typing import List, Dict, Any, Optional
import ollama
from .discovery import TableMetadata, RelationMetadata
import logging

logger = logging.getLogger(__name__)

class MetadataManager:
    def __init__(self, db_id: str, mongo_client: Any):
        self.db_id = db_id
        self.mongo = mongo_client
        self.relation_graph = nx.DiGraph()

    async def save_schema_snapshot(self, tables: List[TableMetadata], relations: List[RelationMetadata], status: str = "indexed"):
        """Saves the crawled schema to MongoDB and builds the relation graph."""
        if self.mongo:
            metadata_coll = self.mongo.db.nl2sql_metadata
            doc = {
                "db_id": self.db_id,
                "tables": [t.model_dump(mode="json") for t in tables],
                "relations": [r.model_dump(mode="json") for r in relations],
                "status": status,
                "updated_at": "now"
            }
            # Upsert the metadata for this DB
            await metadata_coll.update_one(
                {"db_id": self.db_id},
                {"$set": doc},
                upsert=True
            )
        
        # Build Relation Graph (In-memory for current session)
        for rel in relations:
            self.relation_graph.add_edge(
                rel.source_table, 
                rel.target_table, 
                source_col=rel.source_column, 
                target_col=rel.target_column
            )
        
        logger.info(f"Saved schema snapshot for DB {self.db_id} with {len(tables)} tables.")

    def get_join_path(self, table_a: str, table_b: str) -> List[str]:
        """Finds the shortest join path between two tables using the relation graph."""
        try:
            # We treat the graph as undirected for join path discovery
            undirected = self.relation_graph.to_undirected()
            return nx.shortest_path(undirected, source=table_a, target=table_b)
        except nx.NetworkXNoPath:
            return []
        except Exception as e:
            logger.error(f"Error finding join path: {e}")
            return []

    async def generate_embeddings(self, tables: List[TableMetadata]):
        """Generates embeddings for each table and its columns for semantic retrieval."""
        for table in tables:
            # Create a semantic string for the table
            col_names = ", ".join([c.name for c in table.columns])
            semantic_text = f"Table: {table.name}. Columns: {col_names}. Description: {table.description or ''}"
            
            # Generate embedding using Ollama (or OpenAI)
            # This is a placeholder for the actual embedding call
            try:
                # response = ollama.embeddings(model="nomic-embed-text", prompt=semantic_text)
                # embedding = response["embedding"]
                # Save embedding to vector store or Mongo
                pass
            except Exception as e:
                logger.error(f"Embedding generation failed for {table.name}: {e}")

    async def get_relevant_tables(self, query: str, top_k: int = 5) -> List[str]:
        """Performs a semantic search to find tables relevant to the natural language query."""
        # 1. Embed query
        # 2. Vector search against table embeddings
        # 3. Return top_k table names
        return [] # Placeholder
