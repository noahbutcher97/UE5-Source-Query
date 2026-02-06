"""
Profiling utility for UE5 Source Query v2.1.
Uses pyinstrument to identify bottlenecks in the relational search path.
"""

import asyncio
import time
import sys
from pathlib import Path
from pyinstrument import Profiler

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.core.hybrid_query_relational import RelationalHybridEngine

async def run_profile():
    print("=== Profiling Relational Hybrid Engine ===")
    
    engine = RelationalHybridEngine(Path.cwd())
    await engine.initialize()
    
    query = "FHitResult collision detection"
    
    profiler = Profiler()
    
    print(f"Running profile for query: '{query}'...")
    
    profiler.start()
    # Run a few times to get a stable profile
    for _ in range(5):
        await engine.query(query, top_k=5)
    profiler.stop()
    
    # Print results to console
    print("\n--- Profile Results ---")
    profiler.print()
    
    # Save to HTML for deep analysis
    output_html = Path("logs/profile_results.html")
    output_html.parent.mkdir(exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(profiler.output_html())
    
    print(f"\nDetailed HTML profile saved to: {output_html}")
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(run_profile())