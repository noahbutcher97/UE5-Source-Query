"""
UE5 Source Query - API Data Models (v2.1)
Defines Pydantic models for request validation and response serialization.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    """Request schema for semantic and hybrid search"""
    question: str = Field(..., description="The natural language query or entity name")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")
    scope: str = Field("all", pattern="^(engine|project|all)$", description="Search scope")
    use_reranker: bool = Field(False, description="Enable cross-encoder re-ranking (slower but more precise)")

class DefinitionResult(BaseModel):
    """Schema for a single code definition result"""
    type: str = "definition"
    file_path: str
    line_start: int
    line_end: int
    entity_type: str
    entity_name: str
    definition: str
    origin: str
    module: Optional[str] = None
    include: Optional[str] = None

class SemanticResult(BaseModel):
    """Schema for a single semantic search match"""
    path: str
    chunk_index: int
    total_chunks: int
    score: float
    origin: str

class SearchResponse(BaseModel):
    """Root response schema for search queries"""
    question: str
    intent: Dict[str, Any]
    definition_results: List[DefinitionResult]
    semantic_results: List[SemanticResult]
    timing: Dict[str, float]

class HealthStatus(BaseModel):
    """System health check response"""
    status: str
    database: bool
    embeddings: bool
    gpu: bool
    version: str
