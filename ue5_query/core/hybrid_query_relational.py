"""
UE5 Source Query - Relational Hybrid Query Engine (v2.1)
Coordinates semantic search, FTS5 definitions, and relational metadata filtering.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from ue5_query.core.query_intent import QueryIntentAnalyzer, QueryType, EntityType
from ue5_query.core.semantic_engine import SemanticSearchEngine
from ue5_query.core.relational_search import RelationalFilteredSearch
from ue5_query.utils.db_manager import DatabaseManager
from ue5_query.utils.config_manager import ConfigManager
from ue5_query.utils.logger import get_project_logger
from ue5_query.core.query_expansion import QueryExpander
from ue5_query.utils.ue_path_utils import UEPathUtils

logger = get_project_logger(__name__)

class RelationalHybridEngine:
    """
    Asynchronous Hybrid Query Engine utilizing SQLite for relational metadata.
    Designed for high-concurrency FastAPI environments.
    """
    
    def __init__(self, tool_root: Path, config_manager: Optional[ConfigManager] = None):
        self.tool_root = tool_root
        self.config_manager = config_manager or ConfigManager(tool_root)
        
        # Paths
        self.vector_dir = Path(self.config_manager.get('VECTOR_OUTPUT_DIR', str(tool_root / "data")))
        self.db_path = self.vector_dir / "ue5_query.db"
        
        # Components
        self.db = DatabaseManager(self.db_path)
        self.semantic_engine = SemanticSearchEngine(self.vector_dir)
        self.intent_analyzer = QueryIntentAnalyzer()
        
        # Search state
        self._is_ready = False

    async def initialize(self):
        """Prepare engines and load memory-mapped embeddings"""
        if self._is_ready:
            return
            
        logger.info("Initializing Relational Hybrid Engine...")
        # Load embeddings (IO intensive)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.semantic_engine.load_embeddings)
        
        # Link semantic engine to use the same DB manager
        self.rel_search = RelationalFilteredSearch(self.semantic_engine._embeddings, self.db)
        
        self._is_ready = True
        logger.info("Engine Ready.")

    async def query(
        self,
        question: str,
        top_k: int = 5,
        scope: str = "all",
        use_reranker: bool = False
    ) -> Dict[str, Any]:
        """
        Main query entry point (Async).
        """
        if not self._is_ready:
            await self.initialize()

        t_start = time.perf_counter()
        timing = {}

        # 1. Analyze Intent (CPU intensive regex)
        t0 = time.perf_counter()
        intent = self.intent_analyzer.analyze(question)
        timing['intent_analysis_s'] = time.perf_counter() - t0

        # 2. Query Expansion
        expanded_terms = QueryExpander.expand(question)
        
        # 3. Determine Relational Scope
        origin_filter = None
        if scope == 'engine': origin_filter = 'engine'
        elif scope == 'project': origin_filter = 'project'

        # 4. Search Execution
        def_results = []
        sem_results = []

        # A. Definition Search (FTS5 + Relational)
        if intent.query_type in (QueryType.DEFINITION, QueryType.HYBRID):
            t1 = time.perf_counter()
            # Use SQLite FTS5 for rapid definition lookup
            def_results = await self.db.search_definitions(intent.entity_name or question, limit=top_k)
            timing['definition_search_s'] = time.perf_counter() - t1

        # B. Semantic Search (NumPy + Relational Filters)
        if intent.query_type in (QueryType.SEMANTIC, QueryType.HYBRID) or not def_results:
            t2 = time.perf_counter()
            
            # Map scope to relational filters
            sem_results = await self.rel_search.search(
                query_vec=await self.semantic_engine.embed_query(question),
                top_k=top_k,
                origin=origin_filter,
                boost_entities=[intent.entity_name] if intent.entity_name else None,
                boost_macros=True,
                query_type=intent.query_type.value
            )
            timing['semantic_search_s'] = time.perf_counter() - t2

        # 5. Result Formatting
        # Convert DB rows to standard result dicts
        formatted_defs = [self._format_db_def(r) for r in def_results]
        formatted_sem = [self._format_db_chunk(r) for r in sem_results]

        timing['total_s'] = time.perf_counter() - t_start

        return {
            'question': question,
            'intent': {
                'type': intent.query_type.value,
                'entity_name': intent.entity_name,
                'scope': scope
            },
            'definition_results': formatted_defs,
            'semantic_results': formatted_sem,
            'timing': timing
        }

    def _format_db_def(self, row: Dict[str, Any]) -> Dict[str, Any]:
        path_info = UEPathUtils.guess_module_and_include(row['file_path'])
        return {
            'type': 'definition',
            'file_path': row['file_path'],
            'line_start': row['line_start'],
            'line_end': row['line_end'],
            'entity_type': row['entity_type'],
            'entity_name': row['entity_name'],
            'definition': row['content'],
            'origin': row.get('origin', 'engine'),
            'module': path_info['module'],
            'include': path_info['include']
        }

    def _format_db_chunk(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'path': row['path'],
            'chunk_index': row['chunk_index'],
            'total_chunks': row['total_chunks'],
            'score': row['score'],
            'origin': row['origin']
        }

    async def close(self):
        await self.db.close()

async def main():
    """CLI test for relational engine"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()

    engine = RelationalHybridEngine(Path.cwd())
    results = await engine.query(args.query)
    
    print(json.dumps(results, indent=2))
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
