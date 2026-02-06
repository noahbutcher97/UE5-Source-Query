"""
Unit tests for Relational Metadata Layer (SQLite).
Validates integrity, constraints, and edge-case query behavior.
"""

import pytest
import sqlite3
from pathlib import Path
from ue5_query.utils.db_manager import DatabaseManager

@pytest.mark.asyncio
async def test_foreign_key_constraints(db_manager: DatabaseManager):
    """Verify that deleting a file cascadingly deletes its chunks and definitions"""
    # Setup: Ensure data exists
    file = await db_manager.get_file_by_path("C:/Test/Mock.h")
    assert file is not None
    
    file_id = file['id']
    chunks = await db_manager.fetch_all("SELECT id FROM chunks WHERE file_id = ?", (file_id,))
    assert len(chunks) > 0
    
    # Action: Delete file
    conn = await db_manager.get_async_conn()
    await conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    await conn.commit()
    
    # Validation: Chunks should be gone (Cascade)
    chunks_after = await db_manager.fetch_all("SELECT id FROM chunks WHERE file_id = ?", (file_id,))
    assert len(chunks_after) == 0
    
    # Validation: Definitions should be gone
    defs_after = await db_manager.fetch_all("SELECT id FROM definitions WHERE file_id = ?", (file_id,))
    assert len(defs_after) == 0

@pytest.mark.asyncio
async def test_duplicate_path_constraint(db_manager: DatabaseManager):
    """Verify that file paths must be unique"""
    conn = await db_manager.get_async_conn()
    with pytest.raises(sqlite3.IntegrityError):
        await conn.execute("INSERT INTO files (path, origin) VALUES (?, ?)", 
                          ("C:/Test/Mock.h", "engine"))
        await conn.commit()

@pytest.mark.asyncio
async def test_fts5_search_edge_cases(db_manager: DatabaseManager):
    """Test FTS5 behavior with symbols and missing terms"""
    # 1. Exact match
    res = await db_manager.search_definitions("FMockStruct")
    assert len(res) == 1
    assert res[0]['entity_name'] == "FMockStruct"
    
    # 2. Missing term
    res = await db_manager.search_definitions("NonExistentTerm")
    assert len(res) == 0
    
    # 3. Wildcard search (if enabled/supported by syntax)
    res = await db_manager.search_definitions("FMock*")
    assert len(res) == 1

@pytest.mark.asyncio
async def test_filtering_logic(db_manager: DatabaseManager):
    """Verify relational filtering across multiple dimensions"""
    # 1. Filter by origin
    engine_indices = await db_manager.filter_chunks(origin="engine")
    assert len(engine_indices) == 1
    assert engine_indices[0] == 0
    
    project_indices = await db_manager.filter_chunks(origin="project")
    assert len(project_indices if project_indices else []) == 0
    
    # 2. Filter by entity type (JOIN test)
    struct_indices = await db_manager.filter_chunks(entity_type="struct")
    assert len(struct_indices) == 1
    
    class_indices = await db_manager.filter_chunks(entity_type="class")
    assert len(class_indices if class_indices else []) == 0

@pytest.mark.asyncio
async def test_db_cleanup(db_manager: DatabaseManager):
    """Verify close method doesn't leak or hang"""
    await db_manager.close()
    # Subsequent calls should recreate connection or handle error
    assert db_manager._async_conn is None