import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict, Union

from ue5_query.core.query_intent import QueryIntentAnalyzer, QueryType, EntityType
from ue5_query.core.definition_extractor import DefinitionExtractor, DefinitionResult
from ue5_query.core.filtered_search import FilteredSearch
from ue5_query.core import query_engine
from ue5_query.core.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, DEFAULT_EMBED_MODEL, DEFAULT_SEMANTIC_CHUNKING, UE5_ENTITY_PREFIXES
from ue5_query.core.types import QueryResult, DefinitionResultDict, SemanticResultDict, IntentDict
from ue5_query.utils.config_manager import ConfigManager
from ue5_query.utils.logger import get_project_logger
from ue5_query.core.query_expansion import QueryExpander
from ue5_query.utils.semantic_chunker import SemanticChunker
from ue5_query.utils.ue_path_utils import UEPathUtils

# Try importing reranker (optional dependency)
try:
    from ue5_query.core.reranker import SearchReranker
except ImportError:
    SearchReranker = None

logger = get_project_logger(__name__)

# Determine tool root relative to this file (installed package location)
TOOL_ROOT = Path(__file__).resolve().parent.parent.parent

class HybridQueryEngine:
    """
    Hybrid query engine that combines definition extraction and semantic search.
    Automatically routes queries to the best search strategy.
    Keeps resources loaded in memory for faster subsequent queries.
    """
    def __init__(self, tool_root: Path, embeddings=None, metadata=None, model=None, config_manager: Optional[ConfigManager] = None):
        self.tool_root = tool_root
        self.config_manager = config_manager or ConfigManager(tool_root)

        # Dependency Injection / Lazy Loading
        self.embeddings = embeddings
        self.meta = metadata
        self.model = model
        self.embed_model_name = self.config_manager.get('EMBED_MODEL', DEFAULT_EMBED_MODEL)

        # If dependencies are not provided, load them (Default Behavior)
        if self.embeddings is None or self.meta is None:
             self.embeddings, self.meta = query_engine.load_store()
        
        if self.model is None:
             self.model = query_engine.get_model(self.embed_model_name)

        self.analyzer = QueryIntentAnalyzer()

        # Initialize DefinitionExtractor with all indexed files
        # It will filter by scope internally during query
        # Pre-compute allowed files for each scope to avoid set construction per query
        self._scope_cache = {
            'all': set(),
            'engine': set(),
            'project': set()
        }
        
        # Pre-process metadata for faster lookups
        for item in self.meta:
            path_str = item['path']
            path_obj = Path(path_str)
            
            # 1. Add normalized path for fast string comparison in merge loop
            # Check if already present to avoid re-work (if loading from modified store)
            if 'path_norm' not in item:
                item['path_norm'] = os.path.normcase(os.path.abspath(path_str))
            
            # 2. Build scope cache for DefinitionExtractor (needs Path objects)
            self._scope_cache['all'].add(path_obj)
            origin = item.get('origin', 'engine')
            if origin in self._scope_cache:
                self._scope_cache[origin].add(path_obj)

        definition_file_paths = list(self._scope_cache['all'])
        self.definition_extractor = DefinitionExtractor(definition_file_paths)

        # Initialize FilteredSearch once
        self.filtered_search = FilteredSearch(self.embeddings, self.meta)
        
        # Initialize Reranker (lazy load)
        self.reranker = SearchReranker() if SearchReranker else None

        # Chunking config (must match build_embeddings.py defaults)
        self.use_semantic_chunking = self.config_manager.get("SEMANTIC_CHUNKING", "1" if DEFAULT_SEMANTIC_CHUNKING else "0") == "1"
        self.chunk_size = int(self.config_manager.get("CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE) if self.use_semantic_chunking else "1500"))
        self.chunk_overlap = int(self.config_manager.get("CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)))
        
        self.chunker = None
        if self.use_semantic_chunking:
            try:
                self.chunker = SemanticChunker(max_chunk_size=self.chunk_size, overlap=self.chunk_overlap)
            except ImportError:
                pass

    @classmethod
    def from_root(cls, tool_root: Path):
        """Factory method to create instance with default resource loading"""
        return cls(tool_root)

    def _get_chunk_text(self, file_path: str, chunk_index: int) -> str:
        """Retrieve the text for a specific chunk by re-reading and re-chunking."""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            
            text = path.read_text(encoding="utf-8", errors="ignore")
            
            if self.chunker:
                chunks = self.chunker.chunk(text, str(path))
            else:
                # Fallback char chunking (must match build_embeddings.py logic)
                chunks = []
                step = self.chunk_size - self.chunk_overlap
                for start in range(0, len(text), step):
                    chunk = text[start:start + self.chunk_size]
                    if len(chunk) < 300 and start != 0: break
                    chunks.append(chunk)
            
            if 0 <= chunk_index < len(chunks):
                return chunks[chunk_index]
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_index} from {file_path}: {e}")
        
        return ""

    def query(
        self,
        question: str,
        top_k: int = 5,
        dry_run: bool = False,
        show_reasoning: bool = False,
        scope: str = "engine",
        embed_model_name: Optional[str] = None, # Allow overriding global model for a specific query
        use_reranker: bool = False, # New: enable reranking
        **kwargs
    ) -> QueryResult:
        """
        Perform hybrid query using both definition extraction and semantic search.

        Args:
            question: User query
            top_k: Number of results to return
            dry_run: Skip API call
            show_reasoning: Show query analysis reasoning
            json_out: Output as JSON (handled by main or caller)
            scope: Search scope ('engine', 'project', 'all')
            embed_model_name: Override embedding model name for this query
            use_reranker: Enable cross-encoder re-ranking (slower but more precise)
            **kwargs: Additional args passed to semantic search

        Returns:
            Dictionary with results and metadata
        """
        # Guard clause for empty queries
        if not question or not question.strip():
            return self._empty_result(question)

        timing = {}
        t_start = time.perf_counter()

        # Analyze query intent
        t0 = time.perf_counter()
        intent = self.analyzer.analyze(question)
        timing['intent_analysis_s'] = time.perf_counter() - t0

        # Query Expansion (NEW)
        t_exp = time.perf_counter()
        expanded_terms = QueryExpander.expand(question)
        # Use expanded terms for semantic search (joined) and definitions (iteration)
        expanded_query_str = " ".join(expanded_terms) if len(expanded_terms) > 1 else intent.enhanced_query
        timing['expansion_s'] = time.perf_counter() - t_exp

        # Check for entity expansion (upgrading Semantic -> Hybrid)
        expanded_has_entities = False
        if expanded_terms and intent.query_type == QueryType.SEMANTIC:
             for term in expanded_terms:
                 # Check for UE5 prefixes (F, U, A, I, E) followed by uppercase
                 if len(term) > 2 and term.startswith(UE5_ENTITY_PREFIXES) and term[1].isupper():
                     expanded_has_entities = True
                     break
        
        if show_reasoning:
            logger.info("=== Query Analysis ===")
            logger.info(f"Type: {intent.query_type.value}")
            if intent.entity_name:
                logger.info(f"Entity: {intent.entity_type.value} {intent.entity_name}")
            logger.info(f"Confidence: {intent.confidence:.2f}")
            logger.info(f"Reasoning: {intent.reasoning}")
            logger.info(f"Scope: {scope}")
            if expanded_terms and len(expanded_terms) > 1:
                logger.info(f"Expanded: {expanded_terms}")
            elif intent.enhanced_query != question:
                logger.info(f"Enhanced query: {intent.enhanced_query}")
            if expanded_has_entities:
                logger.info(f"Expansion found entities, upgrading to HYBRID search")
            print() # Keep one newline for visual separation in console if needed, or remove

        # Robust check for file search flag
        is_file_query = getattr(intent, 'is_file_search', False)
        
        def_results = []
        sem_results = []
        
        # 1. Definition Search Strategy
        should_run_def = intent.query_type in (QueryType.DEFINITION, QueryType.HYBRID) or expanded_has_entities
        
        if should_run_def:
            t1 = time.perf_counter()
            raw_def_results = self._extract_definitions(intent, scope, expanded_terms)
            timing['definition_extraction_s'] = time.perf_counter() - t1
            def_results = [self._format_def_result(r) for r in raw_def_results]

        # 2. Semantic Search Strategy
        # Run if specifically requested (SEMANTIC/HYBRID) OR if Definition failed (Fallback)
        is_fallback = intent.query_type == QueryType.DEFINITION and (not def_results or len(def_results) < 3)
        should_run_sem = (intent.query_type in (QueryType.SEMANTIC, QueryType.HYBRID)) or is_fallback

        if should_run_sem:
            if is_fallback:
                logger.info(f"Fallback to semantic search (only {len(def_results)} definitions found)")
            
            t2 = time.perf_counter()
            sem_query = expanded_query_str if expanded_query_str else intent.enhanced_query
            sem_results = self._semantic_search(
                sem_query,
                top_k=top_k,
                timing=timing,
                intent=intent,
                scope=scope,
                embed_model_name=embed_model_name,
                use_reranker=use_reranker,
                original_query=question,
                deduplicate_files=is_file_query,
                **kwargs
            )
            timing['semantic_search_s'] = time.perf_counter() - t2

        # 3. Combine Results
        combined_results = []
        
        if def_results and sem_results:
             # Merge: definitions first, then unique semantic results
             combined_results = list(def_results) # Start with definitions
             
             # Create set of paths already in definitions for fast deduplication
             # Use normalized strings to avoid repeated filesystem calls
             def_paths_set = {os.path.normcase(os.path.normpath(r['file_path'])) for r in def_results}
             
             for r in sem_results:
                 # Check if path is already covered
                 sem_path_norm = os.path.normcase(os.path.normpath(r['path']))
                 if sem_path_norm not in def_paths_set:
                     combined_results.append(r)
             
             combined_results = combined_results[:top_k]
        elif def_results:
             combined_results = def_results[:top_k]
        elif sem_results:
             combined_results = sem_results
        
        timing['total_s'] = time.perf_counter() - t_start

        # Log event for M2M monitoring
        try:
            from ue5_query.utils.activity_logger import get_activity_logger
            get_activity_logger().log_event("query_executed", {
                "question": question[:100],
                "type": intent.query_type.value,
                "scope": scope,
                "duration_s": round(timing['total_s'], 3),
                "results_count": len(combined_results)
            })
        except: pass

        return {
            'question': question,
            'intent': {
                'type': intent.query_type.value,
                'entity_type': intent.entity_type.value if intent.entity_type else None,
                'entity_name': intent.entity_name,
                'confidence': intent.confidence,
                'reasoning': intent.reasoning,
                'enhanced_query': intent.enhanced_query,
                'scope': scope,
                'expanded_terms': expanded_terms,
                'is_file_search': is_file_query
            },
            'definition_results': def_results,
            'semantic_results': sem_results,
            'combined_results': combined_results,
            'timing': timing
        }

    def _empty_result(self, question: str) -> QueryResult:
        """Return an empty result structure for invalid queries."""
        return {
            'question': question,
            'intent': {
                'type': 'unknown',
                'entity_type': None,
                'entity_name': None,
                'confidence': 0.0,
                'reasoning': 'Empty or invalid query',
                'enhanced_query': question,
                'scope': 'unknown',
                'expanded_terms': [],
                'is_file_search': False
            },
            'definition_results': [],
            'semantic_results': [],
            'combined_results': [],
            'timing': {'total_s': 0.0}
        }

    def _extract_definitions(self, intent, scope: str = "engine", expanded_terms: List[str] = None) -> List[DefinitionResult]:
        """Extract definitions based on intent, with optional expansion"""
        entities_to_search = []
        
        # Add primary entity from intent
        if intent.entity_name:
            entities_to_search.append((intent.entity_name, intent.entity_type))
        
        # Add expanded entities with type inference
        if expanded_terms:
            for term in expanded_terms:
                # Skip if already added
                if any(e[0] == term for e in entities_to_search):
                    continue
                    
                # Infer type for expanded term
                # Accessing public method infer_entity_type from analyzer
                inferred_type = self.analyzer.infer_entity_type(term)
                
                # Only add if we successfully inferred a type (e.g. FVector -> STRUCT)
                if inferred_type != EntityType.UNKNOWN:
                    entities_to_search.append((term, inferred_type))

        if not entities_to_search:
            return []

        # Filter files by scope for definition extraction using pre-computed cache
        # Fallback to 'all' if scope not found (safety)
        allowed_files = self._scope_cache.get(scope, self._scope_cache['all'])

        # Re-instantiate to ensure fresh content reads
        scoped_extractor = DefinitionExtractor(list(allowed_files))
        
        all_results = []
        
        # Search for each entity term
        for entity_name, entity_type in entities_to_search:
            # Route to appropriate extractor with fuzzy matching enabled
            if entity_type == EntityType.STRUCT:
                all_results.extend(scoped_extractor.extract_struct(entity_name, fuzzy=True))
            elif entity_type == EntityType.CLASS:
                all_results.extend(scoped_extractor.extract_class(entity_name, fuzzy=True))
            elif entity_type == EntityType.ENUM:
                all_results.extend(scoped_extractor.extract_enum(entity_name, fuzzy=True))
            elif entity_type == EntityType.FUNCTION:
                all_results.extend(scoped_extractor.extract_function(entity_name, fuzzy=True))

        # Deduplicate and sort by quality
        seen = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: -x.match_quality):
            key = f"{r.file_path}:{r.line_start}"
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results

    def _semantic_search(self, query: str, top_k: int, timing: dict, intent=None, scope: str = "engine", embed_model_name: str = None, use_reranker: bool = False, original_query: str = None, deduplicate_files: bool = False, **kwargs) -> List[SemanticResultDict]:
        """
        Perform semantic search with optional filtered search and entity boosting.
        """
        # Metadata is now always enriched in self.meta
        enriched_meta = self.meta
        timing['using_filtered_search'] = True

        # Encode query
        t0 = time.perf_counter()
        current_embed_model_name = embed_model_name or self.embed_model_name
        # Check if the query needs a different model, if so, load it temporarily
        if current_embed_model_name != self.embed_model_name:
            current_model = query_engine.get_model(current_embed_model_name)
        else:
            current_model = self.model # Use the pre-loaded model

        qvec = current_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        timing['embed_s'] = time.perf_counter() - t0

        # Validate dimensions match
        if qvec.shape[0] != self.embeddings.shape[1]:
            raise ValueError(
                f"Dimension mismatch: Query vector has {qvec.shape[0]} dimensions (model: {current_embed_model_name}), "
                f"but vector store has {self.embeddings.shape[1]} dimensions. "
                f"Please rebuild the index with the correct model, or change the embedding model in Configuration."
            )

        # Perform search
        t1 = time.perf_counter()

        # Determine origin filter
        origin_filter = None
        if scope == 'engine': origin_filter = 'engine'
        elif scope == 'project': origin_filter = 'project'

        # Extract entity names for boosting
        boost_entities = [intent.entity_name] if intent and intent.entity_name else []

        # Use FilteredSearch with entity boosting
        # Reuse the pre-initialized filtered_search
        search = self.filtered_search 

        # Retrieve more candidates if re-ranking or deduplicating
        search_k = top_k * 10 if (use_reranker or deduplicate_files) else top_k

        results = search.search(
            qvec,
            top_k=search_k,
            boost_entities=boost_entities,
            boost_macros=True,  # Boost UE5 macro chunks
            query_type=intent.query_type.value if intent else None,
            origin=origin_filter,  # Pass scope filter
            query_text=query # Pass raw query for sparse scoring
        )

        # Convert FilteredSearch results to query_engine format
        hits = []
        seen_files = set()
        
        for r in results:
            path = r['path']
            if deduplicate_files:
                if path in seen_files:
                    continue
                seen_files.add(path)

            hits.append({
                'path': r['path'],
                'chunk_index': r['chunk_index'],
                'total_chunks': r['total_chunks'],
                'score': r['score'],
                'boosted': True,
                'origin': r.get('origin', 'engine'), # Ensure origin is passed
                'entities': r.get('entities', []),
                # If available, carry over text snippet for re-ranking
                'text_snippet': r.get('text_snippet')
            })
            
            if len(hits) >= search_k:
                break

        timing['select_s'] = time.perf_counter() - t1

        # Re-Ranking (Precision Phase)
        if use_reranker and self.reranker:
            t_rerank = time.perf_counter()
            # Hydrate hits with text
            for hit in hits:
                if 'text_snippet' not in hit:
                    hit['text_snippet'] = self._get_chunk_text(hit['path'], hit['chunk_index'])
            
            # Perform re-ranking
            ranked_hits = self.reranker.rerank(original_query or query, hits, top_k=top_k)
            timing['rerank_s'] = time.perf_counter() - t_rerank
            hits = ranked_hits
        else:
            hits = hits[:top_k]

        return hits

    def query_relationships(self, entity_name: str, depth: int = 2) -> Dict:
        """
        Query relationships for a given entity (Phase 5).

        Args:
            entity_name: Entity to query (e.g., "FHitResult", "AActor")
            depth: Relationship traversal depth (1-5) - reserved for future use

        Returns:
            Dict with relationship graph and formatted output
        """
        from ue5_query.core.relationship_extractor import RelationshipExtractor

        # Use the existing definition extractor (already initialized with file paths)
        definition_results = None

        # Try struct first (most common for data types like FHitResult)
        definition_results = self.definition_extractor.extract_struct(entity_name, fuzzy=True)

        # Try class if no struct found
        if not definition_results:
            definition_results = self.definition_extractor.extract_class(entity_name, fuzzy=True)

        # Try enum if still not found
        if not definition_results:
            definition_results = self.definition_extractor.extract_enum(entity_name, fuzzy=True)

        if not definition_results:
            return {
                "error": f"Entity '{entity_name}' not found",
                "entity": entity_name,
                "depth": depth
            }

        # Use first result
        def_result = definition_results[0]

        # Extract relationships
        rel_extractor = RelationshipExtractor(self.tool_root)
        graph = rel_extractor.build_relationship_graph(
            entity_name=def_result.entity_name,
            definition=def_result.definition,
            file_path=def_result.file_path
        )

        # Format as tree
        tree = rel_extractor.format_relationship_tree(
            entity_name=def_result.entity_name,
            graph=graph,
            depth=depth
        )

        # Format as JSON
        json_graph = rel_extractor.format_relationship_json(graph)

        return {
            "entity": def_result.entity_name,
            "entity_type": def_result.entity_type,
            "graph": json_graph,
            "tree": tree,
            "depth": depth,
            "file_path": def_result.file_path,
            "line_range": f"{def_result.line_start}-{def_result.line_end}"
        }

    def _format_def_result(self, result: DefinitionResult) -> DefinitionResultDict:
        """Format definition result for output"""
        # Calculate module and include path
        path_info = UEPathUtils.guess_module_and_include(result.file_path)
        
        return {
            'type': 'definition',
            'file_path': result.file_path,
            'line_start': result.line_start,
            'line_end': result.line_end,
            'entity_type': result.entity_type,
            'entity_name': result.entity_name,
            'definition': result.definition[:32000],  # Increased limit for full retrieval
            'members': result.members[:10],  # First 10 members
            'total_members': len(result.members),
            'match_quality': result.match_quality,
            'origin': result.origin if hasattr(result, 'origin') else 'engine', # Add origin
            'module': path_info['module'],
            'include': path_info['include']
        }

def print_results(results: Dict[str, Any], show_reasoning: bool = False):
    """Print results in human-readable format"""
    if show_reasoning:
        print(f"\n=== Query Analysis ===")
        intent = results['intent']
        print(f"Type: {intent['type']}")
        if intent['entity_name']:
            print(f"Entity: {intent['entity_type']} {intent['entity_name']}")
        print(f"Confidence: {intent['confidence']:.2f}")
        print(f"Reasoning: {intent['reasoning']}")
        if intent['enhanced_query'] != results['question']:
            print(f"Enhanced: {intent['enhanced_query']}")
        print()

    if results['definition_results']:
        print(f"\n=== Definition Results ({len(results['definition_results'])}) ===")
        for i, res in enumerate(results['definition_results'], 1):
            print(f"\n[{i}] {res['entity_type'].upper()} {res['entity_name']}")
            print(f"    File: {res['file_path']}")
            print(f"    Lines: {res['line_start']}-{res['line_end']}")
            print(f"    Members: {', '.join(res['members'][:5])}{'...' if len(res['members']) > 5 else ''}")
            print(f"    Origin: {res['origin']}") # Display origin

    if results['semantic_results']:
        print(f"\n=== Semantic Results ({len(results['semantic_results'])}) ===")
        for i, res in enumerate(results['semantic_results'], 1):
            path = Path(res['path']).name
            print(f"[{i}] score={res['score']:.3f} | {path} | chunk {res['chunk_index']+1}/{res['total_chunks']}")
            print(f"    Origin: {res['origin']}") # Display origin


    print(f"\n=== Timing ===")
    for key, val in results['timing'].items():
        print(f"{key}: {val:.3f}s")


def get_tool_schema():
    """Return the tool definition schema (OpenAI Function/MCP compatible)"""
    return {
        "name": "ue5_search",
        "description": "Hybrid semantic search and definition extraction for Unreal Engine 5 source code. Use this to find C++ classes, structs, functions, and documentation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The search query (e.g. 'How does FHitResult work?', 'UCharacterMovementComponent::PhysSlide')"
                },
                "scope": {
                    "type": "string",
                    "enum": ["engine", "project", "all"],
                    "default": "engine",
                    "description": "Limit search to Engine source, Project source, or All."
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return."
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "json", "code"],
                    "default": "text",
                    "description": "Output format. Use 'json' for programmatic parsing."
                }
            },
            "required": ["question"]
        },
        "capabilities": {
            "semantic_search": True,
            "exact_definition_lookup": True,
            "streaming": False
        }
    }

def print_tool_schema():
    print(json.dumps(get_tool_schema(), indent=2))

def main():
    parser = argparse.ArgumentParser(
        description="Hybrid query engine combining definition extraction and semantic search",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("question", nargs="*", help="Your query (optional if using --describe)")
    parser.add_argument("--describe", action="store_true", help="Output machine-readable tool schema")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Skip API call")
    parser.add_argument("--show-reasoning", action="store_true", help="Show query analysis reasoning")
    parser.add_argument("--pattern", default="", help="Filter files by path substring")
    parser.add_argument("--extensions", default="", help="Filter by extensions (e.g., .cpp,.h)")
    parser.add_argument("--scope", choices=["engine", "project", "all"], default="engine", help="Search scope (default: engine)")
    parser.add_argument("--model", default=None, help="Override embedding model name")
    parser.add_argument("--use-reranker", action="store_true", help="Enable re-ranking (slower, higher precision)")

    args = parser.parse_args()

    # Handle Introspection
    if args.describe:
        print_tool_schema()
        sys.exit(0)

    if not args.question:
        parser.print_help()
        sys.exit(1)

    question = " ".join(args.question)

    try:
        # Instantiate the engine
        engine = HybridQueryEngine(TOOL_ROOT)

        # Perform hybrid query
        results = engine.query(
            question=question,
            top_k=args.top_k,
            dry_run=args.dry_run,
            show_reasoning=args.show_reasoning,
            scope=args.scope,
            embed_model_name=args.model,
            use_reranker=args.use_reranker,
            # Pass other args if needed by semantic search, etc.
            pattern=args.pattern,
            extensions=args.extensions
        )

        # Check if results found
        has_results = bool(results.get('definition_results') or results.get('semantic_results'))

        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_results(results, show_reasoning=args.show_reasoning)
        
        # Exit code 0 if results found, 2 if empty (but valid execution)
        sys.exit(0 if has_results else 2)

    except Exception as e:
        # Exit code 1 for runtime errors
        if args.json:
            print(json.dumps({"error": str(e), "status": "error"}))
        else:
            logger.error(f"Query execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
