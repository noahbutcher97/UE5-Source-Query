from typing import List, Optional, TypedDict, Union, Dict

class DefinitionResultDict(TypedDict):
    type: str
    file_path: str
    line_start: int
    line_end: int
    entity_type: str
    entity_name: str
    definition: str
    members: List[str]
    total_members: int
    match_quality: float
    origin: str
    module: Optional[str]
    include: Optional[str]

class SemanticResultDict(TypedDict):
    path: str
    chunk_index: int
    total_chunks: int
    score: float
    boosted: bool
    origin: str
    entities: List[str]
    text_snippet: Optional[str]

class IntentDict(TypedDict):
    type: str
    entity_type: Optional[str]
    entity_name: Optional[str]
    confidence: float
    reasoning: str
    enhanced_query: str
    scope: str
    expanded_terms: List[str]
    is_file_search: bool

class QueryResult(TypedDict):
    question: str
    intent: IntentDict
    definition_results: List[DefinitionResultDict]
    semantic_results: List[SemanticResultDict]
    combined_results: List[Union[DefinitionResultDict, SemanticResultDict]]
    timing: Dict[str, float]
