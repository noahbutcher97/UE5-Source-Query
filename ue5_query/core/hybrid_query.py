import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from ue5_query.core.query_intent import QueryIntentAnalyzer, QueryType, EntityType
from ue5_query.core.definition_extractor import DefinitionExtractor, DefinitionResult
from ue5_query.core.filtered_search import FilteredSearch
from ue5_query.core import query_engine
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
    def __init__(self, tool_root: Path, config_manager: Optional[ConfigManager] = None):
        self.tool_root = tool_root
        self.config_manager = config_manager or ConfigManager(tool_root)

        # Load embeddings and metadata once
        self.embeddings, self.meta = query_engine.load_store()
        
        # Load model once
        self.embed_model_name = self.config_manager.get('EMBED_MODEL', query_engine.DEFAULT_EMBED_MODEL)
        self.model = query_engine.get_model(self.embed_model_name)

        self.analyzer = QueryIntentAnalyzer()

        # Initialize DefinitionExtractor with all indexed files
        # It will filter by scope internally during query
        definition_file_paths = list(set(Path(item['path']) for item in self.meta))
        self.definition_extractor = DefinitionExtractor(definition_file_paths)

        # Initialize FilteredSearch once
        self.filtered_search = FilteredSearch(self.embeddings, self.meta)
        
        # Initialize Reranker (lazy load)
        self.reranker = SearchReranker() if SearchReranker else None

        # Chunking config (must match build_embeddings.py defaults)
        self.use_semantic_chunking = self.config_manager.get("SEMANTIC_CHUNKING", "1") == "1"
        self.chunk_size = int(self.config_manager.get("CHUNK_SIZE", "2000" if self.use_semantic_chunking else "1500"))
        self.chunk_overlap = int(self.config_manager.get("CHUNK_OVERLAP", "200"))
        
        self.chunker = None
        if self.use_semantic_chunking:
            try:
                self.chunker = SemanticChunker(max_chunk_size=self.chunk_size, overlap=self.chunk_overlap)
            except ImportError:
                pass

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
        except Exception as e:
            logger.warning(f"Failed to fetch chunk {chunk_index} from {file_path}: {e}")
        
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
    ) -> Dict[str, Any]:
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
            print() # Keep one newline for visual separation in console if needed, or remove

        results = {
            'question': question,
            'intent': {
                'type': intent.query_type.value,
                'entity_type': intent.entity_type.value if intent.entity_type else None,
                'entity_name': intent.entity_name,
                'confidence': intent.confidence,
                'reasoning': intent.reasoning,
                'enhanced_query': intent.enhanced_query,
                'scope': scope,
                'expanded_terms': expanded_terms
            },
            'definition_results': [],
            'semantic_results': [],
            'combined_results': [],
            'timing': timing
        }

        # Route based on intent
        # Check if expansion reveals new entities (upgrading Semantic -> Hybrid)
        expanded_has_entities = False
        if expanded_terms and intent.query_type == QueryType.SEMANTIC:
             for term in expanded_terms:
                 # Check for UE5 prefixes (F, U, A, I, E) followed by uppercase
                 if len(term) > 2 and term[0] in 'FUAIE' and term[1].isupper():
                     expanded_has_entities = True
                     if show_reasoning:
                        logger.info(f"Expansion found entity '{term}', upgrading to HYBRID search")
                     break

        is_file_query = "File/Location" in intent.reasoning

        if intent.query_type == QueryType.DEFINITION:
            t1 = time.perf_counter()
            def_results = self._extract_definitions(intent, scope, expanded_terms)
            timing['definition_extraction_s'] = time.perf_counter() - t1

            results['definition_results'] = [self._format_def_result(r) for r in def_results]
            
            # SEMANTIC FALLBACK:
            # If no definitions found, or if we want to be robust, run a quick semantic search 
            # to see if we missed the "concept".
            # Especially useful if the regex failed but the concept exists (e.g. "physical constraints").
            if not def_results or len(def_results) < 3:
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
                 results['semantic_results'] = sem_results
                 
                 # Merge: Add semantic results if they look like the target entity name
                 # Or just append them as "related matches"
                 combined = results['definition_results'][:]
                 def_files = {r['file_path'] for r in combined}
                 
                 for s in sem_results:
                     if s['path'] not in def_files:
                         combined.append(s)
                 
                 results['combined_results'] = combined[:top_k]
            else:
                 results['combined_results'] = results['definition_results']

        elif intent.query_type == QueryType.HYBRID or expanded_has_entities:
            t1 = time.perf_counter()
            def_results = self._extract_definitions(intent, scope, expanded_terms)
            timing['definition_extraction_s'] = time.perf_counter() - t1

            t2 = time.perf_counter()
            # Use expanded query for semantic search
            sem_query = expanded_query_str if expanded_query_str else intent.enhanced_query
            sem_results = self._semantic_search(
                sem_query,
                top_k=top_k,
                timing=timing,
                intent=intent,
                scope=scope,
                embed_model_name=embed_model_name,
                use_reranker=use_reranker,
                original_query=question, # Pass original query for re-ranking
                deduplicate_files=is_file_query,
                **kwargs
            )
            timing['semantic_search_s'] = time.perf_counter() - t2

            results['definition_results'] = [self._format_def_result(r) for r in def_results]
            results['semantic_results'] = sem_results

            # Combine results: definitions first, then semantic (deduplicate if needed)
            combined_deduped = []
            def_paths = {Path(r['file_path']).resolve() for r in results['definition_results']}

            for r in results['definition_results']:
                combined_deduped.append(r)
            
            for r in sem_results:
                sem_path = Path(r['path']).resolve()
                # Only add semantic result if its path is not already covered by a definition result
                if sem_path not in def_paths:
                    combined_deduped.append(r)
            
            results['combined_results'] = combined_deduped[:top_k]

        else:  # SEMANTIC
            t1 = time.perf_counter()
            # Use expanded query for semantic search
            sem_query = expanded_query_str if expanded_query_str else intent.enhanced_query
            sem_results = self._semantic_search(
                sem_query,
                top_k=top_k,
                timing=timing,
                intent=intent,
                scope=scope,
                embed_model_name=embed_model_name,
                use_reranker=use_reranker,
                original_query=question, # Pass original query for re-ranking
                deduplicate_files=is_file_query,
                **kwargs
            )
            timing['semantic_search_s'] = time.perf_counter() - t1

            results['semantic_results'] = sem_results
            results['combined_results'] = results['semantic_results']

        timing['total_s'] = time.perf_counter() - t_start
        results['timing'] = timing

        return results

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

        # Filter files by scope for definition extraction
        scoped_meta = [item for item in self.meta if scope == 'all' or item.get('origin', 'engine') == scope]
        definition_file_paths = list(set(Path(item['path']) for item in scoped_meta))
        
        # Reinitialize DefinitionExtractor for each query to ensure fresh file list for current scope
        scoped_extractor = DefinitionExtractor(definition_file_paths)

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

    def _semantic_search(self, query: str, top_k: int, timing: dict, intent=None, scope: str = "engine", embed_model_name: str = None, use_reranker: bool = False, original_query: str = None, deduplicate_files: bool = False, **kwargs) -> List[Dict[str, Any]]:
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
                # Currently we rely on metadata + reading file on demand
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

    def _format_def_result(self, result: DefinitionResult) -> Dict[str, Any]:
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


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid query engine combining definition extraction and semantic search",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("question", nargs="+", help="Your query")
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
    question = " ".join(args.question)

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

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results, show_reasoning=args.show_reasoning)


if __name__ == "__main__":
    main()
