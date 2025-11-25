# python
"""
Debug semantic search to understand why FHitResult chunks score low.
"""
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

TOOL_ROOT = Path(__file__).parent.parent.parent

# Load data
vectors_path = TOOL_ROOT / "data" / "vector_store.npz"
meta_path = TOOL_ROOT / "data" / "vector_meta_enriched.json"

embeddings = np.load(vectors_path)["embeddings"]
metadata = json.loads(meta_path.read_text())['items']

# Load model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Query
query = "FHitResult members struct UPROPERTY fields"
print(f"Query: {query}\n")

# Encode query
qvec = model.encode([query], normalize_embeddings=True)[0]

# Calculate similarities for ALL chunks
similarities = embeddings @ qvec

# Find FHitResult chunks
fhitresult_indices = [
    i for i, m in enumerate(metadata)
    if 'FHitResult' in m.get('entities', [])
]

print(f"Total chunks: {len(metadata)}")
print(f"FHitResult chunks: {len(fhitresult_indices)}\n")

# Show top 10 overall scores
print("=== Top 10 Overall (Before Boosting) ===")
top_indices = np.argsort(-similarities)[:10]
for rank, idx in enumerate(top_indices, 1):
    m = metadata[idx]
    has_fhitresult = 'FHitResult' in m.get('entities', [])
    marker = "✓ FHitResult" if has_fhitresult else ""
    print(f"{rank}. score={similarities[idx]:.3f} | {Path(m['path']).name} chunk {m['chunk_index']+1} {marker}")

# Show FHitResult chunk scores
print("\n=== FHitResult Chunks (sorted by score) ===")
fhitresult_scores = [(i, similarities[i]) for i in fhitresult_indices]
fhitresult_scores.sort(key=lambda x: -x[1])

for rank, (idx, score) in enumerate(fhitresult_scores[:10], 1):
    m = metadata[idx]
    overall_rank = np.where(np.argsort(-similarities) == idx)[0][0] + 1
    print(f"{rank}. score={score:.3f} (overall rank: {overall_rank}) | {Path(m['path']).name} chunk {m['chunk_index']+1}/{m['total_chunks']}")
    print(f"   Entities: {m.get('entities', [])}")
    print(f"   Has UPROPERTY: {m.get('has_uproperty')}")

# Calculate what boost would be needed
print("\n=== Analysis ===")
top_non_fhitresult_score = max(similarities[i] for i in top_indices if i not in fhitresult_indices)
best_fhitresult_score = max(similarities[i] for i in fhitresult_indices)
print(f"Best non-FHitResult score: {top_non_fhitresult_score:.3f}")
print(f"Best FHitResult score: {best_fhitresult_score:.3f}")
print(f"Current boost: 20% (1.2x)")
print(f"Boosted FHitResult score: {best_fhitresult_score * 1.2:.3f}")
print(f"Boost needed to beat top result: {top_non_fhitresult_score / best_fhitresult_score:.2f}x ({(top_non_fhitresult_score / best_fhitresult_score - 1) * 100:.0f}%)")

print("\n=== Root Cause ===")
print("The general-purpose NLP model (all-MiniLM-L6-v2) doesn't understand:")
print("- C++ code syntax")
print("- UE5 naming conventions (F*, U*, A* prefixes)")
print("- Technical struct definitions")
print("\nIt matches on natural language words like 'members', 'fields' which")
print("appear in unrelated files (MemberReference.h, ConstraintInstance.h)")
print("\nSolution: Phase 3 - Upgrade to unixcoder-base (code-specific model)")
