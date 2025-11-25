# python
"""
Benchmark different embedding models for UE5 C++ code search.
Tests models on representative queries and measures relevance.
"""
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

# Test queries representing common use cases
TEST_QUERIES = [
    # Definition queries
    ("struct FHitResult", ["HitResult.h"]),
    ("class AActor", ["Actor.h"]),
    ("FVector struct", ["Vector.h"]),

    # Member queries
    ("FHitResult members ImpactPoint", ["HitResult.h"]),
    ("AActor properties", ["Actor.h"]),

    # Conceptual queries
    ("collision detection implementation", ["Collision", "Physics"]),
    ("vehicle physics simulation", ["WheeledVehicle", "ChaosVehicle"]),
    ("actor component lifecycle", ["ActorComponent.h"]),

    # Specific API queries
    ("LineTraceSingleByChannel function", ["CollisionQueryParams", "WorldCollision"]),
    ("GetActorLocation implementation", ["Actor.h", "Actor.cpp"]),
]

# Models to test
MODELS_TO_TEST = [
    {
        "name": "all-MiniLM-L6-v2",
        "path": "sentence-transformers/all-MiniLM-L6-v2",
        "description": "Current model - General purpose, 384 dims",
    },
    {
        "name": "unixcoder-base",
        "path": "microsoft/unixcoder-base",
        "description": "Code-specific, trained on CodeSearchNet, 768 dims",
    },
    {
        "name": "codebert-base",
        "path": "microsoft/codebert-base",
        "description": "Code-specific, BERT architecture, 768 dims",
    },
]


def load_test_data():
    """Load existing vector store for comparison"""
    tool_root = Path(__file__).parent.parent.parent
    vectors_path = tool_root / "data" / "vector_store.npz"
    meta_path = tool_root / "data" / "vector_meta.json"

    if not vectors_path.exists() or not meta_path.exists():
        print("Error: Vector store not found. Run build_embeddings.py first.")
        return None, None

    vectors = np.load(vectors_path)["embeddings"]
    metadata = json.loads(meta_path.read_text())["items"]

    return vectors, metadata


def test_model(model_name: str, model_path: str, queries: List[Tuple[str, List[str]]]) -> Dict:
    """Test a model on benchmark queries"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {model_name}")
    print(f"Path: {model_path}")
    print(f"{'=' * 60}")

    try:
        from sentence_transformers import SentenceTransformer

        # Load model
        print(f"Loading model...")
        t_start = time.perf_counter()
        model = SentenceTransformer(model_path)
        load_time = time.perf_counter() - t_start
        print(f"Model loaded in {load_time:.2f}s")

        # Get embedding dimension
        test_embedding = model.encode(["test"], normalize_embeddings=True)[0]
        dim = len(test_embedding)
        print(f"Embedding dimension: {dim}")

        # Test query encoding speed
        print(f"\nTesting query encoding speed...")
        test_queries_text = [q[0] for q in queries]
        t_start = time.perf_counter()
        embeddings = model.encode(test_queries_text, normalize_embeddings=True, show_progress_bar=False)
        encode_time = (time.perf_counter() - t_start) / len(test_queries_text)
        print(f"Average encoding time: {encode_time*1000:.1f}ms per query")

        results = {
            "model_name": model_name,
            "model_path": model_path,
            "dimension": dim,
            "load_time": load_time,
            "encode_time_ms": encode_time * 1000,
            "test_results": [],
        }

        # Test each query
        for query, expected_keywords in queries:
            query_vec = model.encode([query], normalize_embeddings=True)[0]
            results["test_results"].append({
                "query": query,
                "expected": expected_keywords,
                "embedding_norm": float(np.linalg.norm(query_vec)),
            })

        return results

    except Exception as e:
        print(f"Error testing {model_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run benchmark on all models"""
    print("=" * 60)
    print("UE5 C++ Code Embedding Model Benchmark")
    print("=" * 60)

    # Load test data
    print("\nLoading existing vector store...")
    vectors, metadata = load_test_data()

    if vectors is None:
        print("Skipping comparative analysis (no existing vectors)")
    else:
        print(f"Loaded {len(vectors)} existing embeddings ({vectors.shape[1]} dims)")

    # Test each model
    all_results = []

    for model_config in MODELS_TO_TEST:
        result = test_model(
            model_config["name"],
            model_config["path"],
            TEST_QUERIES
        )

        if result:
            result["description"] = model_config["description"]
            all_results.append(result)

            # Save intermediate results
            output_file = Path(__file__).parent / f"benchmark_{model_config['name']}.json"
            output_file.write_text(json.dumps(result, indent=2))
            print(f"\nResults saved to: {output_file}")

    # Summary comparison
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for result in all_results:
        print(f"\n{result['model_name']}:")
        print(f"  Dimension: {result['dimension']}")
        print(f"  Load time: {result['load_time']:.2f}s")
        print(f"  Query encoding: {result['encode_time_ms']:.1f}ms")
        print(f"  Description: {result['description']}")

    # Save combined results
    combined_file = Path(__file__).parent / "model_benchmark_results.json"
    combined_file.write_text(json.dumps({
        "models": all_results,
        "test_queries": [(q, exp) for q, exp in TEST_QUERIES],
    }, indent=2))

    print(f"\nCombined results saved to: {combined_file}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if all_results:
        # Find fastest
        fastest = min(all_results, key=lambda x: x['encode_time_ms'])
        print(f"\nFastest: {fastest['model_name']} ({fastest['encode_time_ms']:.1f}ms)")

        # Find code-specific models
        code_models = [r for r in all_results if 'code' in r['model_name'].lower() or 'code' in r['description'].lower()]
        if code_models:
            print(f"\nCode-specific models:")
            for model in code_models:
                print(f"  - {model['model_name']}: {model['description']}")

        print("\nNOTE: To fully evaluate accuracy, we need to rebuild the vector store")
        print("with each model and test on actual UE5 queries. This benchmark only")
        print("measures encoding speed and dimensions.")

        print("\nNext steps:")
        print("1. Choose a model based on this benchmark")
        print("2. Update build_embeddings.py MODEL_NAME")
        print("3. Rebuild vector store")
        print("4. Test actual search accuracy on UE5 queries")


if __name__ == "__main__":
    main()