# Audit: Database Architecture & Performance (v2.1)

## ## Metadata
- **Author**: Gemini-CLI Intelligence Layer
- **Date Created**: 2026-02-04
- **Project**: UE5 Source Query System
- **Status**: Final Audit Report
- **Version**: 1.0.0 (SemVer)
- **License**: MIT
- **Contact**: posner.noah@gmail.com

---

## ## Overview
The current metadata strategy (Flat JSON files) creates a performance wall for the UE5 Source Query System. Linear scans of `vector_meta.json` are $O(N)$, leading to latency that scales poorly with index size. This audit identifies 20 refactors to implement a Relational Database (SQLite) with B-Tree indexing, referential integrity, and full-text search capabilities.

---

## ## Refactoring Recommendations (Top 20)

### 1. Relational Metadata Schema (SQLite)
- **Description**: Migrate from `vector_meta.json` to a structured SQLite database (`ue5_index.db`).
- **Purpose**: Resolve the $O(N)$ filtering bottleneck and provide data integrity via relational constraints.
- **Success Metric**: Filter operations (e.g., origin="project") reduced from ~200ms to <1ms.

### 2. B-Tree Indexing on High-Cardinality Fields
- **Description**: Add SQL indexes on `rel_path`, `entity_name`, and `origin`.
- **Purpose**: Enable near-instant retrieval of metadata for specific files or entities.

### 3. Foreign Key Cascading Deletes
- **Description**: Link `source_files` to `code_chunks` via `ON DELETE CASCADE`.
- **Purpose**: Prevent "orphaned chunks" by ensuring that deleting a file record automatically purges all associated snippets.

### 4. FTS5 Full-Text Search
- **Description**: Implement a Virtual Table using SQLite's FTS5 extension for `text_content`.
- **Purpose**: Provide high-performance exact keyword matching as a fallback to vector search.
- **Success Metric**: Instant results for specific debug strings or macro names.

### 5. WAL Mode for Concurrent Access
- **Description**: Enable `PRAGMA journal_mode=WAL;`.
- **Purpose**: Allow the background indexer to write new data while the search server simultaneously reads old data.

### 6. File-Hash Incremental Validation
- **Description**: Store `SHA256` file hashes in the `source_files` table.
- **Purpose**: Skip re-embedding for unchanged files, reducing full rebuild times by 90%.

### 7. Entity Type Normalization
- **Description**: Replace string-based "struct/class" tags with an `entity_types` lookup table.
- **Purpose**: Reduce storage footprint and speed up filtered searches.

### 8. JSONB for Flexible Attributes
- **Description**: Use a `metadata` JSONB column for UE5-specific properties (e.g., `UFUNCTION` specifiers).
- **Purpose**: Allow the schema to evolve without requiring complex SQL migrations for every new property.

### 9. Composite Search Indexing
- **Description**: Create a composite index on `(origin, is_header, rel_path)`.
- **Purpose**: Optimize the most common search patterns used in the `HybridQueryEngine`.

### 10. Database Connection Pooling
- **Description**: Implement a shared connection pool (e.g., via `SQLAlchemy`).
- **Purpose**: Reduce the overhead of opening/closing the database file for every query.

### 11. Alembic Migration Framework
- **Description**: Integrate `Alembic` to manage database schema versions.
- **Purpose**: Ensure that team members can safely upgrade their local index databases without losing data.

### 12. Index Maintenance Audit Log
- **Description**: Maintain an `index_events` table tracking when and how the index was updated.
- **Purpose**: Facilitate debugging of indexing failures across different team machines.

### 13. Automated Vacuuming (Auto-Vacuum)
- **Description**: Configure `PRAGMA auto_vacuum = INCREMENTAL;`.
- **Purpose**: Automatically reclaim disk space when files are removed from the index.

### 14. Covering Index for Entity Lookup
- **Description**: Index `(entity_name, file_id)` to include the file pointer.
- **Purpose**: Allow definition lookups to be satisfied entirely from the index without a table scan.

### 15. SQL-Based Maintenance Views
- **Description**: Create views like `view_index_stats` to aggregate chunk counts by module.
- **Purpose**: Simplify the logic in the Diagnostics tab of the Unified Dashboard.

### 16. Referential Integrity Enforcement
- **Description**: Enable `PRAGMA foreign_keys = ON;`.
- **Purpose**: Guarantee that every chunk in the database points to a valid file entry.

### 17. Hybrid Result View
- **Description**: Implement a SQL View joining `entities` and `code_chunks`.
- **Purpose**: Simplify the "merge" logic in the Python engine by pushing it to the database layer.

### 18. Batch Transaction Processing
- **Description**: Wrap indexing operations in large transactions (e.g., 1000 records per commit).
- **Purpose**: Increase indexing throughput by 50x compared to individual row inserts.

### 19. Distributed Index Synchronization
- **Description**: Implement a CLI utility to export/import the SQLite database for team sharing.
- **Purpose**: Allow one "build machine" to generate the index and distribute it via Git LFS or S3.

### 20. Thread-Local DB Sessions
- **Description**: Ensure each FastAPI worker has its own scoped database session.
- **Purpose**: Prevent "database is locked" errors in a multi-worker environment.

---

## ## Prioritized Task Registry

| Task ID | Description | Effort | Impact (1-5) | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **DB-01** | **SQLite Migration** | Medium | 5 | O(log N) lookup speed |
| **DB-02** | **B-Tree Indexing** | Low | 5 | Sub-1ms metadata selection |
| **DB-03** | **WAL Mode Enable** | Low | 4 | Real-time concurrent indexing |
| **DB-04** | **FTS5 Integration** | Low | 4 | Exact keyword search fallback |
| **DB-05** | **Hash Validation** | Medium | 5 | 90% faster incremental builds |
| **DB-06** | **CASCADE Deletes** | Low | 4 | 0% orphaned chunk rate |
| **DB-07** | **Alembic Setup** | Medium | 3 | Versioned, safe DB updates |
| **DB-08** | **Batch Commits** | Low | 5 | Fast, scalable indexing |
| **DB-09** | **JSONB Columns** | Low | 3 | Flexible metadata support |
| **DB-10** | **Audit Logging** | Low | 2 | Index rebuild traceability |
| **DB-11** | **Conn Pooling** | Medium | 3 | Higher query throughput |
| **DB-12** | **Composite Index** | Low | 4 | Scope Search Optimization |
| **DB-13** | **Auto-Vacuum** | Low | 2 | Reduced disk bloat |
| **DB-14** | **Stats Views** | Low | 3 | Simplified dashboard logic |
| **DB-15** | **FK Enforcement** | Low | 5 | High data consistency |
| **DB-16** | **Partial Indexing** | Medium | 3 | Smaller, faster index |
| **DB-17** | **Sync Utility** | Low | 4 | Simplified team deployment |
| **DB-18** | **Thread Safety** | Medium | 4 | 0 "DB Locked" errors |
| **DB-19** | **Normalization** | Medium | 3 | Storage efficiency |
| **DB-20** | **Hybrid View** | Low | 3 | Cleaner engine logic |

---
*End of Report*
