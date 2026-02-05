-- UE5 Source Query - Relational Schema (v2.1)
-- Transition from monolithic JSON to SQLite for performance and integrity.

PRAGMA foreign_keys = ON;

-- 1. Files: Source file tracking and change detection
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    origin TEXT NOT NULL,          -- 'engine' or 'project'
    sha256 TEXT,                   -- For incremental updates
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_header BOOLEAN,             -- .h, .hpp
    is_implementation BOOLEAN      -- .cpp, .c
);

-- 2. Entities: Canonical list of C++ entities (Classes, Structs, etc.)
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,     -- e.g., 'FHitResult'
    type TEXT NOT NULL,            -- 'class', 'struct', 'enum', 'function', 'delegate'
    ue_prefix CHAR(1)              -- 'F', 'U', 'A', 'I', 'E'
);

-- 3. Definitions: Regex-extracted precise definitions
CREATE TABLE IF NOT EXISTS definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    content TEXT NOT NULL,         -- Full definition source code
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- 4. Members: Fields, methods, and enum values
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    definition_id INTEGER NOT NULL,
    name TEXT NOT NULL,            -- Member name
    type TEXT,                     -- Member type (for structs/classes)
    is_uproperty BOOLEAN DEFAULT 0,
    is_ufunction BOOLEAN DEFAULT 0,
    FOREIGN KEY (definition_id) REFERENCES definitions(id) ON DELETE CASCADE
);

-- 5. Chunks: Overlapping text segments for semantic search
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    content_chars INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    vector_index INTEGER NOT NULL, -- Offset into vector_store.npz
    has_uproperty BOOLEAN DEFAULT 0,
    has_ufunction BOOLEAN DEFAULT 0,
    has_uclass BOOLEAN DEFAULT 0,
    has_ustruct BOOLEAN DEFAULT 0,
    has_uenum BOOLEAN DEFAULT 0,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 6. Chunk-Entity Mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    PRIMARY KEY (chunk_id, entity_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- 7. Full Text Search (FTS5) for rapid definition lookup
CREATE VIRTUAL TABLE IF NOT EXISTS fts_definitions USING fts5(
    content,
    content='definitions',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS definitions_ai AFTER INSERT ON definitions BEGIN
  INSERT INTO fts_definitions(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS definitions_ad AFTER DELETE ON definitions BEGIN
  INSERT INTO fts_definitions(fts_definitions, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS definitions_au AFTER UPDATE ON definitions BEGIN
  INSERT INTO fts_definitions(fts_definitions, rowid, content) VALUES('delete', old.id, old.content);
  INSERT INTO fts_definitions(rowid, content) VALUES (new.id, new.content);
END;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_definitions_entity ON definitions(entity_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_members_def ON members(definition_id);
