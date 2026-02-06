"""
Load and Regression tests for FastAPI search endpoint.
Validates async throughput and response integrity.
"""

import pytest
import asyncio
import time
import httpx
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

# We test the live app logic via TestClient
from ue5_query.server.app import app, state

@pytest.fixture(autouse=True)
def mock_engine():
    """Mock the engine to avoid loading heavy models during API tests"""
    with patch('ue5_query.server.app.RelationalHybridEngine') as mock_cls:
        mock_engine = mock_cls.return_value
        mock_engine.initialize = AsyncMock()
        mock_engine.close = AsyncMock()
        mock_engine.query = AsyncMock(return_value={
            "question": "mocked",
            "intent": {"type": "semantic", "entity_name": None, "scope": "all"},
            "definition_results": [],
            "semantic_results": [
                {"path": "C:/Mock.cpp", "chunk_index": 0, "total_chunks": 1, "score": 0.9, "origin": "engine"}
            ],
            "timing": {"total_s": 0.01}
        })
        mock_engine._is_ready = True
        
        # Manually inject into app state for tests
        state.engine = mock_engine
        yield mock_engine

def test_health_endpoint():
    """Verify health reporting logic"""
    with TestClient(app) as client:
        # Mock DB check inside health endpoint if needed, 
        # but here we just want to see it returns 200
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

@pytest.mark.asyncio
async def test_search_integrity():
    """Verify search contract and response types"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/search", json={
            "question": "FHitResult",
            "top_k": 3,
            "scope": "all"
        })
        
        assert resp.status_code == 200
        data = resp.json()
        assert "definition_results" in data
        assert "semantic_results" in data
        assert len(data['semantic_results']) == 1

@pytest.mark.asyncio
async def test_api_load_throughput():
    """Measure API throughput under concurrent load"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        start = time.perf_counter()
        count = 50 # Increased count since it's mocked
        
        tasks = [
            ac.post("/search", json={"question": f"Test Query {i}", "top_k": 1})
            for i in range(count)
        ]
        
        responses = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start
        
        for r in responses:
            assert r.status_code == 200
            
        requests_per_sec = count / duration
        print(f"\n[PERF] API Throughput (Mocked): {requests_per_sec:.1f} req/s")
        
        assert requests_per_sec > 100, "API throughput significantly below target"

@pytest.mark.asyncio
async def test_invalid_requests():
    """Regression: Verify error handling for malformed input"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/search", json={"top_k": 5})
        assert resp.status_code == 422 
        
        resp = await ac.post("/search", json={"question": "test", "scope": "invalid"})
        assert resp.status_code == 422
