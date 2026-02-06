"""
Performance benchmarks and optimization validation for v2.1.
Measures latency, throughput, and establishes baseline metrics.
"""

import pytest
import time
import asyncio
import numpy as np
from pathlib import Path
from ue5_query.utils.db_manager import DatabaseManager

# Spec Requirements:
# - Definition lookup < 10ms (cached/indexed)
# - Filtered semantic search < 50ms (metadata phase)
# - 50+ concurrent users (simulated via 100 iterations in loop)

@pytest.mark.asyncio
async def test_definition_latency_baseline(db_manager: DatabaseManager):
    """Establish baseline for FTS5 lookup speed"""
    # Use real DB if available for more realistic numbers, otherwise fixture
    # We'll use fixture for repeatability in tests
    
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        await db_manager.search_definitions("FMockStruct", limit=5)
        latencies.append(time.perf_counter() - start)
    
    avg_latency_ms = (sum(latencies) / len(latencies)) * 1000
    print(f"\n[PERF] Avg FTS5 Latency: {avg_latency_ms:.3f}ms")
    
    # Requirement Check
    assert avg_latency_ms < 10.0, f"Definition search too slow: {avg_latency_ms:.2f}ms"

@pytest.mark.asyncio
async def test_relational_filter_throughput(db_manager: DatabaseManager):
    """Establish baseline for JOIN-based filtering speed"""
    start = time.perf_counter()
    iterations = 200
    
    for _ in range(iterations):
        await db_manager.filter_chunks(entity_type="struct", origin="engine")
        
    duration = time.perf_counter() - start
    queries_per_sec = iterations / duration
    print(f"[PERF] Filter Throughput: {queries_per_sec:.1f} QPS")
    
    # Requirement Check
    assert queries_per_sec > 500, f"Filter throughput too low: {queries_per_sec:.1f} QPS"

@pytest.mark.asyncio
async def test_vram_leak_check():
    """
    Simulated VRAM/RAM check.
    In v2.1 we must ensure we don't reload model weights unnecessarily.
    """
    import psutil
    import gc
    
    process = psutil.Process()
    mem_initial = process.memory_info().rss
    
    # Simulate loading engine (Mock weights would be better, but let's check base growth)
    from ue5_query.core.semantic_engine import SemanticSearchEngine
    # Just init without weights load to check object overhead
    engine = SemanticSearchEngine(Path("data"))
    
    mem_after = process.memory_info().rss
    growth_kb = (mem_after - mem_initial) / 1024
    print(f"[PERF] RAM Overhead (Engine Object): {growth_kb:.1f} KB")
    
    assert growth_kb < 1024 * 50, "Engine object base overhead excessive"

@pytest.mark.asyncio
async def test_async_concurrency_stress(db_manager: DatabaseManager):
    """Verify non-blocking behavior under simulated concurrent load"""
    
    async def concurrent_task(task_id):
        start = time.perf_counter()
        # Mix of definition and filtering
        if task_id % 2 == 0:
            await db_manager.search_definitions("FMockStruct")
        else:
            await db_manager.filter_chunks(origin="engine")
        return time.perf_counter() - start

    # Start 50 tasks simultaneously
    tasks = [concurrent_task(i) for i in range(50)]
    latencies = await asyncio.gather(*tasks)
    
    max_latency = max(latencies) * 1000
    avg_latency = (sum(latencies) / len(latencies)) * 1000
    
    print(f"[PERF] Concurrency Stress (50 tasks): Avg={avg_latency:.2f}ms, Max={max_latency:.2f}ms")
    
    # In a non-blocking environment, max latency shouldn't be 50x avg latency
    assert max_latency < 100.0, "Concurrent tasks experiencing heavy blocking"