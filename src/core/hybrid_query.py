# python
# ===== File: HybridQuery.py =====
"""
Hybrid query engine that combines definition extraction and semantic search.
Automatically routes queries to the best search strategy.
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path for imports
TOOL_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TOOL_ROOT / "src"))

from core.query_intent import QueryIntentAnalyzer, QueryType, EntityType
from core.definition_extractor import DefinitionExtractor, DefinitionResult
from core.filtered_search import FilteredSearch
from core import query_engine


def hybrid_query(
    question: str,
    top_k: int = 5,
    dry_run: bool = False,
    show_reasoning: bool = False,
    json_out: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Perform hybrid query using both definition extraction and semantic search.

    Args:
        question: User query
        top_k: Number of results to return
        dry_run: Skip API call
        show_reasoning: Show query analysis reasoning
        json_out: Output as JSON
        **kwargs: Additional args passed to semantic search

    Returns:
        Dictionary with results and metadata
    """
    timing = {}
    t_start = time.perf_counter()

    # Analyze query intent
    t0 = time.perf_counter()
    analyzer = QueryIntentAnalyzer()
    intent = analyzer.analyze(question)
    timing['intent_analysis_s'] = time.perf_counter() - t0

    if show_reasoning:
        print(f"\n=== Query Analysis ===")
        print(f"Type: {intent.query_type.value}")
        if intent.entity_name:
            print(f"Entity: {intent.entity_type.value} {intent.entity_name}")
        print(f"Confidence: {intent.confidence:.2f}")
        print(f"Reasoning: {intent.reasoning}")
        if intent.enhanced_query != question:
            print(f"Enhanced query: {intent.enhanced_query}")
        print()

    results = {
        'question': question,
        'intent': {
            'type': intent.query_type.value,
            'entity_type': intent.entity_type.value if intent.entity_type else None,
            'entity_name': intent.entity_name,
            'confidence': intent.confidence,
            'reasoning': intent.reasoning,
            'enhanced_query': intent.enhanced_query
        },
        'definition_results': [],
        'semantic_results': [],
        'combined_results': [],
        'timing': timing
    }

    # Route based on intent
    if intent.query_type == QueryType.DEFINITION:
        # Pure definition extraction
        t1 = time.perf_counter()
        def_results = _extract_definitions(intent)
        timing['definition_extraction_s'] = time.perf_counter() - t1

        results['definition_results'] = [_format_def_result(r) for r in def_results]
        results['combined_results'] = results['definition_results']

    elif intent.query_type == QueryType.HYBRID:
        # Try definition extraction first, supplement with semantic search
        t1 = time.perf_counter()
        def_results = _extract_definitions(intent)
        timing['definition_extraction_s'] = time.perf_counter() - t1

        t2 = time.perf_counter()
        # Use enhanced query for better semantic results
        sem_results = _semantic_search(
            intent.enhanced_query,
            top_k=top_k,
            timing=timing,
            intent=intent,  # Pass intent for entity boosting
            **kwargs
        )
        timing['semantic_search_s'] = time.perf_counter() - t2

        results['definition_results'] = [_format_def_result(r) for r in def_results]
        results['semantic_results'] = sem_results

        # Combine results: definitions first, then semantic
        combined = results['definition_results'][:top_k]
        if len(combined) < top_k:
            # Add semantic results to fill up to top_k
            remaining = top_k - len(combined)
            combined.extend(sem_results[:remaining])
        results['combined_results'] = combined

    else:  # SEMANTIC
        # Pure semantic search
        t1 = time.perf_counter()
        sem_results = _semantic_search(
            intent.enhanced_query,
            top_k=top_k,
            timing=timing,
            intent=intent,  # Pass intent for potential entity boosting
            **kwargs
        )
        timing['semantic_search_s'] = time.perf_counter() - t1

        results['semantic_results'] = sem_results
        results['combined_results'] = sem_results

    timing['total_s'] = time.perf_counter() - t_start
    results['timing'] = timing

    return results


def _extract_definitions(intent) -> List[DefinitionResult]:
    """Extract definitions based on intent"""
    if not intent.entity_name or not intent.entity_type:
        return []

    # Load file list from metadata
    meta_path = TOOL_ROOT / "data" / "vector_meta.json"
    if not meta_path.exists():
        return []

    meta = json.loads(meta_path.read_text())
    file_paths = list(set(Path(item['path']) for item in meta['items']))

    extractor = DefinitionExtractor(file_paths)

    # Route to appropriate extractor
    if intent.entity_type == EntityType.STRUCT:
        return extractor.extract_struct(intent.entity_name)
    elif intent.entity_type == EntityType.CLASS:
        return extractor.extract_class(intent.entity_name)
    elif intent.entity_type == EntityType.ENUM:
        return extractor.extract_enum(intent.entity_name)
    elif intent.entity_type == EntityType.FUNCTION:
        return extractor.extract_function(intent.entity_name)

    return []


def _semantic_search(query: str, top_k: int, timing: dict, intent=None, **kwargs) -> List[Dict[str, Any]]:
    """
    Perform semantic search with optional filtered search and entity boosting.

    If enriched metadata exists and intent has entity information,
    uses FilteredSearch for relevance boosting.
    """
    # Load embeddings and metadata
    embeddings, meta = query_engine.load_store()

    # Check for enriched metadata
    enriched_meta_path = TOOL_ROOT / "data" / "vector_meta_enriched.json"
    use_filtered_search = enriched_meta_path.exists()

    if use_filtered_search:
        enriched_meta = json.loads(enriched_meta_path.read_text())['items']
        timing['using_filtered_search'] = True
    else:
        enriched_meta = meta
        timing['using_filtered_search'] = False

    # Encode query
    t0 = time.perf_counter()
    model = query_engine.get_model(kwargs.get('embed_model_name', query_engine.DEFAULT_EMBED_MODEL))
    qvec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    timing['embed_s'] = time.perf_counter() - t0

    # Perform search
    t1 = time.perf_counter()

    if use_filtered_search and intent and intent.entity_name:
        # Use FilteredSearch with entity boosting
        search = FilteredSearch(embeddings, enriched_meta)

        # Extract entity names for boosting
        boost_entities = [intent.entity_name] if intent.entity_name else []

        results = search.search(
            qvec,
            top_k=top_k,
            boost_entities=boost_entities,
            boost_macros=True,  # Boost UE5 macro chunks
            query_type=intent.query_type.value if intent else None  # Pass query type for header prioritization
        )

        # Convert FilteredSearch results to query_engine format
        hits = []
        for r in results:
            hits.append({
                'path': r['path'],
                'chunk_index': r['chunk_index'],
                'total_chunks': r['total_chunks'],
                'score': r['score'],
                'boosted': True
            })
    else:
        # Fall back to standard semantic search
        hits = query_engine.select(qvec, embeddings, meta, top_k)
        for hit in hits:
            hit['boosted'] = False

    timing['select_s'] = time.perf_counter() - t1

    return hits


def _format_def_result(result: DefinitionResult) -> Dict[str, Any]:
    """Format definition result for output"""
    return {
        'type': 'definition',
        'file_path': result.file_path,
        'line_start': result.line_start,
        'line_end': result.line_end,
        'entity_type': result.entity_type,
        'entity_name': result.entity_name,
        'definition': result.definition[:500],  # Truncate for display
        'members': result.members[:10],  # First 10 members
        'total_members': len(result.members),
        'match_quality': result.match_quality
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
            print(f"    Members: {res['total_members']}")
            if res['members']:
                print(f"    First members: {', '.join(res['members'][:5])}")

    if results['semantic_results']:
        print(f"\n=== Semantic Results ({len(results['semantic_results'])}) ===")
        for i, res in enumerate(results['semantic_results'], 1):
            path = Path(res['path']).name
            print(f"[{i}] score={res['score']:.3f} | {path} | chunk {res['chunk_index']+1}/{res['total_chunks']}")

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

    args = parser.parse_args()
    question = " ".join(args.question)

    # Perform hybrid query
    results = hybrid_query(
        question=question,
        top_k=args.top_k,
        dry_run=args.dry_run,
        show_reasoning=args.show_reasoning,
        json_out=args.json,
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