"""
UE5 Source Query - Database Manager (Task T-006)
Provides asynchronous access to the relational metadata store.
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import sqlite3

import aiosqlite
from ue5_query.utils.logger import get_project_logger

logger = get_project_logger(__name__)

class DatabaseManager:
    """
    Manages SQLite connections and provides high-level query methods.
    Supports both async (for FastAPI) and sync (for legacy/CLI) paths.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to project data directory
            root = Path(__file__).parent.parent.parent
            db_path = root / "data" / "ue5_query.db"
        
        self.db_path = db_path
        self._async_conn: Optional[aiosqlite.Connection] = None

    async def get_async_conn(self) -> aiosqlite.Connection:
        """Get or create an asynchronous connection"""
        if self._async_conn is None:
            self._async_conn = await aiosqlite.connect(self.db_path)
            # Enable foreign keys and set row factory to Row for dict-like access
            await self._async_conn.execute("PRAGMA foreign_keys = ON")
            self._async_conn.row_factory = aiosqlite.Row
        return self._async_conn

    def get_sync_conn(self) -> sqlite3.Connection:
        """Get a synchronous connection (caller is responsible for closing)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    async def close(self):
        """Close the async connection"""
        if self._async_conn:
            await self._async_conn.close()
            self._async_conn = None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dicts"""
        conn = await self.get_async_conn()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dict"""
        conn = await self.get_async_conn()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    # --- Domain Specific Queries ---

    async def get_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        return await self.fetch_one("SELECT * FROM files WHERE path = ?", (path,))

    async def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return await self.fetch_one("SELECT * FROM entities WHERE name = ?", (name,))

    async def search_definitions(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search definitions using FTS5"""
        sql = """
            SELECT d.*, e.name as entity_name, e.type as entity_type, f.path as file_path
            FROM fts_definitions fts
            JOIN definitions d ON d.id = fts.rowid
            JOIN entities e ON e.id = d.entity_id
            JOIN files f ON f.id = d.file_id
            WHERE fts_definitions MATCH ?
            LIMIT ?
        """
        return await self.fetch_all(sql, (query_text, limit))

    async def get_chunks_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        return await self.fetch_all("SELECT * FROM chunks WHERE file_id = ? ORDER BY chunk_index", (file_id,))

    async def filter_chunks(self, 
                           origin: Optional[str] = None, 
                           entity_type: Optional[str] = None,
                           has_uproperty: Optional[bool] = None) -> Optional[List[int]]:
        """
        Powerful filtering for semantic search reranking.
        Returns a list of vector_indexes corresponding to the .npz store.
        Returns None if no filters were applied.
        """
        if origin is None and entity_type is None and has_uproperty is None:
            return None

        query = "SELECT vector_index FROM chunks c JOIN files f ON f.id = c.file_id WHERE 1=1"
        params = []
        
        if origin:
            query += " AND f.origin = ?"
            params.append(origin)
        
        if entity_type:
            # This is an example of why relational is better - we can filter by entity type across all chunks
            query += " AND c.id IN (SELECT chunk_id FROM chunk_entities ce JOIN entities e ON e.id = ce.entity_id WHERE e.type = ?)"
            params.append(entity_type)
            
        if has_uproperty is not None:
            query += " AND c.has_uproperty = ?"
            params.append(1 if has_uproperty else 0)
            
        rows = await self.fetch_all(query, tuple(params))
        return [row['vector_index'] for row in rows]
