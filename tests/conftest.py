"""
Shared test fixtures for UE5 Source Query v2.1.
"""

import pytest
import asyncio
import sqlite3
import numpy as np
from pathlib import Path
from typing import Generator

import aiosqlite
from ue5_query.utils.db_manager import DatabaseManager
from ue5_query.core.hybrid_query_relational import RelationalHybridEngine

@pytest.fixture
def mock_embeddings():
    """Create a small mock embedding matrix (100 vectors, 768 dims)"""
    return np.random.rand(100, 768).astype(np.float32)

@pytest.fixture
async def temp_db(tmp_path) -> Generator[Path, None, None]:
    """Create a temporary database with the actual schema"""
    db_path = tmp_path / "test_ue5_query.db"
    schema_path = Path("data/schema.sql")
    
    # Apply schema
    conn = sqlite3.connect(db_path)
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    
    # Insert basic test data
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (path, origin, is_header) VALUES (?, ?, ?)", 
                  ("C:/Test/Mock.h", "engine", 1))
    file_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO entities (name, type, ue_prefix) VALUES (?, ?, ?)",
                  ("FMockStruct", "struct", "F"))
    entity_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO chunks (file_id, chunk_index, total_chunks, content_chars, content_text, vector_index) VALUES (?, ?, ?, ?, ?, ?)",
                  (file_id, 0, 1, 100, "struct FMockStruct { int x; };", 0))
    chunk_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO chunk_entities (chunk_id, entity_id) VALUES (?, ?)", (chunk_id, entity_id))
    cursor.execute("INSERT INTO definitions (file_id, entity_id, line_start, line_end, content) VALUES (?, ?, ?, ?, ?)",
                  (file_id, entity_id, 1, 1, "struct FMockStruct { int x; };"))
    
    conn.commit()
    conn.close()
    
    yield db_path

@pytest.fixture
async def db_manager(temp_db) -> DatabaseManager:
    db = DatabaseManager(temp_db)
    yield db
    await db.close()

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
