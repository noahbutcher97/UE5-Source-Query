"""
A/B Testing Framework for Search Metrics.
Validates recall and precision of search algorithms against a benchmark dataset.
"""
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Callable
from pathlib import Path

# Try universal import for engine
try:
    from ue5_query.core.hybrid_query import HybridQueryEngine
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from ue5_query.core.hybrid_query import HybridQueryEngine

@dataclass
class BenchmarkCase:
    query: str
    expected_matches: List[str]  # List of entity names or file paths expected
    min_rank: int = 5  # Expected to be within top K

class SearchEvaluator:
    """
    Evaluates search engine performance (Precision/Recall).
    """
    
    def __init__(self, engine: HybridQueryEngine):
        self.engine = engine

    def evaluate(self, cases: List[BenchmarkCase], top_k: int = 5, **query_kwargs) -> Dict[str, float]:
        """
        Run evaluation on a set of cases.
        
        Returns:
            Dict containing average precision, recall, and latency.
        """
        total_precision = 0.0
        total_recall = 0.0
        total_latency = 0.0
        
        print(f"Running evaluation on {len(cases)} cases (Top-K={top_k}, params={query_kwargs})...")
        
        for case in cases:
            start_time = time.perf_counter()
            results = self.engine.query(case.query, top_k=top_k, **query_kwargs)
            latency = time.perf_counter() - start_time
            total_latency += latency
            
            # Collect retrieved items (names and paths)
            retrieved_items = set()
            
            # Add definitions
            for r in results.get('definition_results', []):
                retrieved_items.add(r['entity_name'])
                retrieved_items.add(r['file_path'])
                
            # Add semantic results
            for r in results.get('semantic_results', []):
                retrieved_items.add(Path(r['path']).name) # file name
                retrieved_items.add(r['path']) # full path
                if 'entities' in r:
                    for e in r['entities']:
                        retrieved_items.add(e)

            # Calculate metrics for this case
            relevant_retrieved = 0
            for expected in case.expected_matches:
                # Check for exact or partial match in retrieved items
                # We use flexible matching for benchmarking to account for variations
                match_found = False
                for item in retrieved_items:
                    if expected.lower() in str(item).lower():
                        match_found = True
                        break
                if match_found:
                    relevant_retrieved += 1
            
            # Precision: Proportion of retrieved items that are relevant
            # (Note: In search, 'precision' often means "was the relevant item in the result list?")
            # Here we define Precision@K as: (Relevant items found) / K
            # But since K might be larger than expected matches, we normalize differently usually.
            # Let's use simple Binary Recall: "Was at least one expected item found?"
            # And Precision: "How much noise?"
            
            # Standard IR definitions:
            # Precision = (Relevant ∩ Retrieved) / Retrieved
            # Recall = (Relevant ∩ Retrieved) / Relevant
            
            n_retrieved = len(retrieved_items) if len(retrieved_items) > 0 else 1
            n_relevant = len(case.expected_matches)
            
            precision = relevant_retrieved / top_k # Precision@K
            recall = relevant_retrieved / n_relevant if n_relevant > 0 else 0.0
            
            total_precision += precision
            total_recall += recall
            
            # print(f"  Query: '{case.query}' | R: {recall:.2f} | P: {precision:.2f}")

        metrics = {
            "avg_precision": total_precision / len(cases),
            "avg_recall": total_recall / len(cases),
            "avg_latency_ms": (total_latency / len(cases)) * 1000
        }
        
        return metrics

def run_ab_test():
    """
    Run A/B test comparing current engine vs baseline (conceptual).
    Since we only have one engine active, this serves as a metric validation tool.
    """
    # Define a small benchmark suite
    # These should be adapted to the actual codebase content
    cases = [
        BenchmarkCase("FHitResult", ["FHitResult", "HitResult.h"]),
        BenchmarkCase("actor", ["AActor", "Actor.h"]),
        BenchmarkCase("vector math", ["FVector", "KismetMathLibrary"]),
        BenchmarkCase("trace", ["LineTraceSingle", "World.h"]),
        BenchmarkCase("array", ["TArray", "Array.h"]),
        # Fuzzy/Partial cases
        BenchmarkCase("FHitRes", ["FHitResult"]),
        BenchmarkCase("char mov", ["UCharacterMovementComponent"]),
    ]
    
    # Initialize engine
    # Assuming we are running from project root
    tool_root = Path(".").resolve()
    if not (tool_root / "ue5_query").exists():
        tool_root = tool_root.parent # Handle running from subdirectory
        
    try:
        engine = HybridQueryEngine(tool_root)
        evaluator = SearchEvaluator(engine)
        
        print("\n=== BASELINE (Sparse + Dense) ===")
        metrics_base = evaluator.evaluate(cases, use_reranker=False)
        print(f"Recall@5:    {metrics_base['avg_recall']:.2%}")
        print(f"Precision@5: {metrics_base['avg_precision']:.2%}")
        print(f"Latency:     {metrics_base['avg_latency_ms']:.1f} ms")

        print("\n=== RERANKED (Sparse + Dense + Cross-Encoder) ===")
        metrics_rerank = evaluator.evaluate(cases, use_reranker=True)
        print(f"Recall@5:    {metrics_rerank['avg_recall']:.2%}")
        print(f"Precision@5: {metrics_rerank['avg_precision']:.2%}")
        print(f"Latency:     {metrics_rerank['avg_latency_ms']:.1f} ms")
        
        # Validation against targets
        target_recall = 0.70
        
        print("\n=== Validation ===")
        if metrics_rerank['avg_recall'] >= target_recall:
            print(f"[PASS] Recall target met (> {target_recall:.0%})")
        else:
            print(f"[FAIL] Recall below target ({metrics_rerank['avg_recall']:.2%} < {target_recall:.0%})")
            
    except Exception as e:
        print(f"Failed to run test: {e}")

if __name__ == "__main__":
    run_ab_test()
