"""
UE5 Source Query - Data Migration Utility (Task T-005)
Migrates monolithic vector_meta.json to relational SQLite schema.
"""

import json
import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Set
import time

from ue5_query.core.definition_extractor import DefinitionExtractor

# Paths
ROOT = Path(__file__).parent.parent
JSON_META = ROOT / "data" / "vector_meta.json"
SCHEMA_SQL = ROOT / "data" / "schema.sql"
DB_PATH = ROOT / "data" / "ue5_query.db"

def initialize_db():
    """Create the database and apply schema"""
    print(f"Initializing database at {DB_PATH}...")
    if DB_PATH.exists():
        print("Existing database found. Deleting for fresh migration...")
        try:
            DB_PATH.unlink()
        except PermissionError:
            print("Error: Could not delete database. Ensure it is not open in another tool.")
            return False
    
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SCHEMA_SQL, 'r') as f:
            conn.executescript(f.read())
        print("Schema applied successfully.")
        return True
    except Exception as e:
        print(f"Failed to apply schema: {e}")
        return False
    finally:
        conn.close()

def migrate():
    if not JSON_META.exists():
        print(f"Error: {JSON_META} not found. Run rebuild-index first.")
        return

    if not initialize_db():
        return
    
    print(f"Loading {JSON_META}...")
    try:
        with open(JSON_META, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        return
    
    items = data.get("items", [])
    print(f"Loaded {len(items)} metadata entries.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Map files and entities to avoid duplicates and get IDs
    file_map = {} # path -> id
    entity_map = {} # name -> id
    unique_paths = set()
    
    start_time = time.time()
    
    try:
        print("Migrating items...")
        # Start a single transaction for maximum speed
        cursor.execute("BEGIN TRANSACTION")
        
        for i, item in enumerate(items):
            if i % 10000 == 0 and i > 0:
                print(f"  Processed {i}/{len(items)} items...")
            
            path = item.get("path")
            origin = item.get("origin", "engine")
            sha256 = item.get("sha256")
            
            # File Entry
            if path not in file_map:
                is_header = path.lower().endswith(('.h', '.hpp'))
                is_implementation = path.lower().endswith(('.cpp', '.c', '.cc'))
                unique_paths.add(Path(path))
                
                cursor.execute(
                    "INSERT INTO files (path, origin, sha256, is_header, is_implementation) VALUES (?, ?, ?, ?, ?)",
                    (path, origin, sha256, is_header, is_implementation)
                )
                file_map[path] = cursor.lastrowid
            
            file_id = file_map[path]
            
            # Chunk Entry
            cursor.execute(
                """INSERT INTO chunks (
                    file_id, chunk_index, total_chunks, content_chars, content_text, vector_index,
                    has_uproperty, has_ufunction, has_uclass, has_ustruct, has_uenum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    file_id, 
                    item.get("chunk_index", 0),
                    item.get("total_chunks", 1),
                    item.get("chars", 0),
                    "", # content_text not in json
                    i,  # vector_index
                    item.get("has_uproperty", False),
                    item.get("has_ufunction", False),
                    item.get("has_uclass", False),
                    item.get("has_ustruct", False),
                    item.get("has_uenum", False)
                )
            )
            chunk_id = cursor.lastrowid
            
            # Entities and many-to-many mapping
            entities = item.get("entities", [])
            entity_types = item.get("entity_types", [])
            
            for idx, entity_name in enumerate(entities):
                if entity_name not in entity_map:
                    etype = "unknown"
                    if idx < len(entity_types):
                        etype = entity_types[idx]
                    
                    prefix = None
                    if len(entity_name) > 1 and entity_name[0] in "FUAIE" and entity_name[1].isupper():
                        prefix = entity_name[0]
                        
                    cursor.execute(
                        "INSERT OR IGNORE INTO entities (name, type, ue_prefix) VALUES (?, ?, ?)",
                        (entity_name, etype, prefix)
                    )
                    
                    cursor.execute("SELECT id FROM entities WHERE name = ?", (entity_name,))
                    row = cursor.fetchone()
                    if row:
                        entity_map[entity_name] = row[0]
                
                if entity_name in entity_map:
                    entity_id = entity_map[entity_name]
                    cursor.execute(
                        "INSERT OR IGNORE INTO chunk_entities (chunk_id, entity_id) VALUES (?, ?)",
                        (chunk_id, entity_id)
                    )

        # 2. Definition Extraction (NEW)
        print("\nExtracting precise definitions from source files...")
        existing_files = [p for p in unique_paths if p.exists()]
        extractor = DefinitionExtractor(existing_files)
        
        # Scan for all entities in all files
        # Note: This is a heavy operation, normally done by indexer
        # but here we do it to populate the relational layer.
        processed_files = 0
        for path_obj in existing_files:
            processed_files += 1
            if processed_files % 100 == 0:
                print(f"  Scanned {processed_files}/{len(existing_files)} files for definitions...")
            
            path_str = str(path_obj)
            file_id = file_map[path_str]
            
            # Extract everything from this file
            # (In a real scenario, indexer would pass these directly)
            content = extractor._read_file(path_obj)
            if not content: continue
            
            # Use patterns from extractor to find all definitions
            for etype, pattern in [('struct', extractor.STRUCT_PATTERN), 
                                  ('class', extractor.CLASS_PATTERN), 
                                  ('enum', extractor.ENUM_PATTERN)]:
                for match in pattern.finditer(content):
                    # Find name using the same logic as extractor
                    entity_name = None
                    for g in reversed(match.groups()):
                        if g and g[0].isupper():
                            entity_name = g
                            break
                    
                    if not entity_name: continue
                    
                    # Ensure entity exists in entities table
                    if entity_name not in entity_map:
                        prefix = entity_name[0] if len(entity_name) > 1 and entity_name[0] in "FUAIE" and entity_name[1].isupper() else None
                        cursor.execute(
                            "INSERT OR IGNORE INTO entities (name, type, ue_prefix) VALUES (?, ?, ?)",
                            (entity_name, etype, prefix)
                        )
                        cursor.execute("SELECT id FROM entities WHERE name = ?", (entity_name,))
                        row = cursor.fetchone()
                        if row: entity_map[entity_name] = row[0]
                    
                    entity_id = entity_map.get(entity_name)
                    if not entity_id: continue
                    
                    # Extract full block
                    line_start = content[:match.start()].count('\n') + 1
                    definition_text, line_end = extractor._extract_definition_block(
                        content, match.end(), content.splitlines(), line_start
                    )
                    
                    if not definition_text: continue
                    
                    # Insert Definition
                    cursor.execute(
                        "INSERT INTO definitions (file_id, entity_id, line_start, line_end, content) VALUES (?, ?, ?, ?, ?)",
                        (file_id, entity_id, line_start, line_end, definition_text)
                    )
                    def_id = cursor.lastrowid
                    
                    # Parse Members
                    members = extractor._parse_members(definition_text, etype)
                    for m in members:
                        m_parts = m.split(' ', 1)
                        m_type = m_parts[0] if len(m_parts) > 1 else None
                        m_name = m_parts[1] if len(m_parts) > 1 else m_parts[0]
                        
                        cursor.execute(
                            "INSERT INTO members (definition_id, name, type, is_uproperty, is_ufunction) VALUES (?, ?, ?, ?, ?)",
                            (def_id, m_name, m_type, 'UPROPERTY' in definition_text, 'UFUNCTION' in definition_text)
                        )
        
        print("Finalizing transaction...")
        conn.execute("COMMIT")
        
        duration = time.time() - start_time
        print(f"\nMigration Complete in {duration:.2f}s!")
        print(f"  Files: {len(file_map)}")
        print(f"  Entities: {len(entity_map)}")
        print(f"  Chunks: {len(items)}")
        print(f"  Definitions: {processed_files} files scanned.")
        
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"\nMigration FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()