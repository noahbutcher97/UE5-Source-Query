"""
Benchmark and validation for SQLite relational metadata layer vs Legacy JSON.
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
import sqlite3

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.utils.db_manager import DatabaseManager

DB_PATH = Path("data/ue5_query.db")
JSON_PATH = Path("data/vector_meta.json")

async def benchmark_sqlite():
    db = DatabaseManager(DB_PATH)
    print(f"\n--- SQLite Benchmarks ({DB_PATH.name}) ---")
    
    # 1. Total count
    start = time.perf_counter()
    res = await db.fetch_one("SELECT count(*) as count FROM chunks")
    duration = (time.perf_counter()-start)*1000
    print(f"Total Chunks: {res['count']} (Took {duration:.2f}ms)")
    
    # 2. Filter by origin
    start = time.perf_counter()
    indices = await db.filter_chunks(origin="engine")
    duration = (time.perf_counter()-start)*1000
    print(f"Filter origin='engine': {len(indices if indices else [])} matches (Took {duration:.2f}ms)")
    
    # 3. Filter by entity type (JOIN)
    start = time.perf_counter()
    indices = await db.filter_chunks(entity_type="class")
    duration = (time.perf_counter()-start)*1000
    print(f"Filter type='class': {len(indices if indices else [])} matches (Took {duration:.2f}ms)")
    
    # 4. FTS5 Search
    start = time.perf_counter()
    results = await db.search_definitions("FHitResult")
    duration = (time.perf_counter()-start)*1000
    print(f"FTS5 Search 'FHitResult': {len(results)} matches (Took {duration:.2f}ms)")
    if results:
        print(f"  First match: {results[0]['file_path']}")

    await db.close()

def benchmark_json():
    print(f"\n--- Legacy JSON Benchmarks ({JSON_PATH.name}) ---")
    if not JSON_PATH.exists():
        print("JSON meta missing, skipping.")
        return

    # 1. Load time (monolithic)
    start = time.perf_counter()
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
    items = data['items']
    duration = (time.perf_counter()-start)*1000
    print(f"Load & Parse: {len(items)} items (Took {duration:.2f}ms)")
    
    # 2. Filter by origin (Linear scan)
    start = time.perf_counter()
    matches = [i for i in items if i.get('origin') == 'engine']
    duration = (time.perf_counter()-start)*1000
    print(f"Filter origin='engine': {len(matches)} matches (Took {duration:.2f}ms)")
    
    # 3. Filter by entity type (Linear scan)
    start = time.perf_counter()
    matches = [i for i in items if 'class' in i.get('entity_types', [])]
    duration = (time.perf_counter()-start)*1000
    print(f"Filter type='class': {len(matches)} matches (Took {duration:.2f}ms)")

async def main():
    print("UE5 Source Query - Database Performance Validation")
    print("="*60)
    
    benchmark_json()
    await benchmark_sqlite()
    
    print("\n" + "="*60)
    print("Validation Complete.")

if __name__ == "__main__":
    asyncio.run(main())