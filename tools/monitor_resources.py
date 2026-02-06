"""
Resource utilization monitoring for UE5 Source Query v2.1.
Measures RAM/VRAM baseline and growth during load.
"""

import psutil
import os
import time
import asyncio
from pathlib import Path
import torch

# Add project root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.core.hybrid_query_relational import RelationalHybridEngine

async def monitor_resources():
    print("=== Resource Utilization Baseline ===")
    
    process = psutil.Process()
    
    # 1. Idle Baseline
    mem_idle = process.memory_info().rss / (1024 * 1024)
    print(f"Initial Process RAM (Idle): {mem_idle:.2f} MB")
    
    # 2. Engine Initialization
    print("Initializing Engine...")
    engine = RelationalHybridEngine(Path.cwd())
    await engine.initialize()
    
    mem_init = process.memory_info().rss / (1024 * 1024)
    print(f"Process RAM (Loaded Engine): {mem_init:.2f} MB (+{mem_init-mem_idle:.2f} MB)")
    
    if torch.cuda.is_available():
        vram_used = torch.cuda.memory_allocated() / (1024 * 1024)
        vram_reserved = torch.cuda.memory_reserved() / (1024 * 1024)
        print(f"VRAM Allocated: {vram_used:.2f} MB")
        print(f"VRAM Reserved: {vram_reserved:.2f} MB")
    else:
        print("CUDA not available, skipping VRAM check.")
        
    # 3. Active Query Load
    print("\nRunning Active Load (10 queries)...")
    start_time = time.time()
    for i in range(10):
        await engine.query("FHitResult", top_k=5)
            
    mem_final = process.memory_info().rss / (1024 * 1024)
    duration = time.time() - start_time
    
    print(f"Final Process RAM: {mem_final:.2f} MB")
    print(f"RAM Leak (Init -> Final): {mem_final-mem_init:.2f} MB")
    avg_ms = (duration / 10) * 1000
    print(f"Avg Query Time: {avg_ms:.2f} ms")
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(monitor_resources())