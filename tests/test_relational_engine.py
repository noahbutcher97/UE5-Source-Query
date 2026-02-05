"""
Integration test for RelationalHybridEngine (v2.1).
"""

import asyncio
import time
from pathlib import Path
import json
import sys

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.core.hybrid_query_relational import RelationalHybridEngine

async def test_engine():
    print("Initializing Relational Hybrid Engine...")
    engine = RelationalHybridEngine(Path.cwd())
    
    start = time.perf_counter()
    await engine.initialize()
    print(f"Initialization took {(time.perf_counter()-start):.2f}s")
    
    queries = [
        "FHitResult",           # Should trigger FTS5 Definition
        "how to use physics",   # Should trigger Semantic
        "UCharacterMovementComponent" # Hybrid/Mixed
    ]
    
    for q in queries:
        print(f"\nQuerying: '{q}'")
        start = time.perf_counter()
        results = await engine.query(q, top_k=3)
        duration = time.perf_counter() - start
        
        num_defs = len(results['definition_results'])
        num_sem = len(results['semantic_results'])
        print(f"Results: {num_defs} defs, {num_sem} semantic")
        print(f"Total Time: {duration*1000:.2f}ms")
        
        # Print first definition if found
        if results['definition_results']:
            d = results['definition_results'][0]
            print(f"  [DEF] {d['entity_name']} in {Path(d['file_path']).name}")
            
        # Print first semantic if found
        if results['semantic_results']:
            s = results['semantic_results'][0]
            print(f"  [SEM] {Path(s['path']).name} (score: {s['score']:.3f})")

    await engine.close()

if __name__ == "__main__":
    asyncio.run(test_engine())