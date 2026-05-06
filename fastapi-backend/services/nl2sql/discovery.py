import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ColumnMetadata(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str] = None
    primary_key: bool = False
    foreign_key: Optional[str] = None # Format: "target_table.target_column"
    description: Optional[str] = None

class TableMetadata(BaseModel):
    name: str
    columns: List[ColumnMetadata]
    row_count: int = 0
    description: Optional[str] = None
    sample_data: List[Dict[str, Any]] = []

class RelationMetadata(BaseModel):
    source_table: str
    source_column: str
    target_table: str
    target_column: str

class DiscoveryService:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        try:
            self.url = make_url(connection_string)
            self.dialect = self.url.get_dialect().name
        except Exception as e:
            logger.error(f"Invalid connection string: {e}")
            raise ValueError(f"Invalid connection string: {e}")
        
        self.engine = create_engine(connection_string)
        self.inspector = inspect(self.engine)

    def get_all_tables(self) -> List[str]:
        return self.inspector.get_table_names()

    def get_table_metadata(self, table_name: str) -> TableMetadata:
        columns = []
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", [])
        
        fk_constraints = self.inspector.get_foreign_keys(table_name)
        fk_map = {}
        for fk in fk_constraints:
            for i, col in enumerate(fk["constrained_columns"]):
                fk_map[col] = f"{fk['referred_table']}.{fk['referred_columns'][i]}"

        for col in self.inspector.get_columns(table_name):
            columns.append(ColumnMetadata(
                name=col["name"],
                type=str(col["type"]),
                nullable=col["nullable"],
                default=str(col["default"]) if col.get("default") else None,
                primary_key=col["name"] in pk_cols,
                foreign_key=fk_map.get(col["name"])
            ))

        # Get row count (careful with large tables)
        row_count = 0
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
        except Exception as e:
            logger.warning(f"Could not get row count for {table_name}: {e}")

        # Get sample data
        sample_data = self.sample_table_data(table_name, limit=5)

        return TableMetadata(
            name=table_name,
            columns=columns,
            row_count=row_count,
            sample_data=sample_data
        )

    def get_all_relations(self) -> List[RelationMetadata]:
        relations = []
        for table_name in self.get_all_tables():
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                for i, col in enumerate(fk["constrained_columns"]):
                    relations.append(RelationMetadata(
                        source_table=table_name,
                        source_column=col,
                        target_table=fk["referred_table"],
                        target_column=fk["referred_columns"][i]
                    ))
        return relations

    def sample_table_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                return [dict(row) for row in result.mappings()]
        except Exception as e:
            logger.error(f"Error sampling data from {table_name}: {e}")
            return []
