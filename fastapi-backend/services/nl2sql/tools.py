from typing import List, Dict, Any, Optional
from .discovery import DiscoveryService, TableMetadata
from .metadata_manager import MetadataManager

class NL2SQLTools:
    def __init__(self, discovery_service: DiscoveryService, metadata_manager: MetadataManager):
        self.discovery = discovery_service
        self.metadata = metadata_manager

    def get_relevant_tables(self, query: str) -> List[str]:
        """Find tables semantically related to the query."""
        # In a real implementation, this would call metadata_manager.get_relevant_tables
        # For now, we'll return all tables if the DB is small, or a mocked list
        return self.discovery.get_all_tables()

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get column names, types, and descriptions for a specific table."""
        metadata = self.discovery.get_table_metadata(table_name)
        return metadata.model_dump(mode="json")

    def get_table_relations(self, table_names: List[str]) -> List[Dict[str, Any]]:
        """Get foreign key relationships and join conditions between a set of tables."""
        all_relations = self.discovery.get_all_relations()
        filtered = []
        for rel in all_relations:
            if rel.source_table in table_names and rel.target_table in table_names:
                filtered.append(rel.model_dump(mode="json"))
        return filtered

    def get_sample_values(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get sample rows from a table to understand data distribution."""
        return self.discovery.sample_table_data(table_name, limit=limit)

    def get_column_stats(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Get statistics for a column (cardinality, min, max, null count)."""
        # Placeholder for complex stats logic
        return {
            "table": table_name,
            "column": column_name,
            "cardinality": "High",
            "sample_values": ["val1", "val2"]
        }

    def search_glossary(self, term: str) -> Optional[str]:
        """Look up business definitions or specific SQL snippets for a term."""
        # Placeholder for glossary lookup
        return None
