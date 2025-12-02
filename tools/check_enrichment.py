"""Check if metadata enrichment is working properly"""
import json
from pathlib import Path

# Load enriched metadata
enriched_path = Path("data/vector_meta_enriched.json")
if not enriched_path.exists():
    print("[ERROR] Enriched metadata not found!")
    print("Run: python src/indexing/metadata_enricher.py")
    exit(1)

with open(enriched_path) as f:
    meta = json.load(f)

items = meta['items']
print(f"Total chunks: {len(items)}")
print()

# Check enrichment quality
chunks_with_entities = [i for i in items if i.get('entities')]
chunks_with_macros = [i for i in items if i.get('ue5_macros')]
chunks_with_entity_type = [i for i in items if i.get('entity_type')]

print(f"Chunks with entities: {len(chunks_with_entities)}/{len(items)} ({100*len(chunks_with_entities)/len(items):.1f}%)")
print(f"Chunks with UE5 macros: {len(chunks_with_macros)}/{len(items)} ({100*len(chunks_with_macros)/len(items):.1f}%)")
print(f"Chunks with entity_type: {len(chunks_with_entity_type)}/{len(items)} ({100*len(chunks_with_entity_type)/len(items):.1f}%)")
print()

# Show sample enriched chunk
if chunks_with_entities:
    print("Sample enriched chunk:")
    sample = chunks_with_entities[0]
    print(f"  Path: {Path(sample['path']).name}")
    print(f"  Entities: {sample.get('entities', [])}")
    print(f"  Entity Type: {sample.get('entity_type', 'N/A')}")
    print(f"  UE5 Macros: {sample.get('ue5_macros', [])}")
    print()

# Show entity distribution
all_entities = {}
for item in chunks_with_entities:
    for entity in item.get('entities', []):
        all_entities[entity] = all_entities.get(entity, 0) + 1

print("Top 10 most common entities:")
for entity, count in sorted(all_entities.items(), key=lambda x: -x[1])[:10]:
    print(f"  {entity}: {count} chunks")
print()

# Check for FHitResult specifically
hitresult_chunks = [i for i in items if 'FHitResult' in i.get('entities', [])]
print(f"Chunks mentioning FHitResult: {len(hitresult_chunks)}")
if hitresult_chunks:
    print(f"  Example: {Path(hitresult_chunks[0]['path']).name}")
print()

print("[INFO] Enrichment Status:")
if len(chunks_with_entities) > len(items) * 0.1:  # At least 10% enriched
    print("  ✓ Metadata enrichment is working properly")
    print("  ✓ FilteredSearch can use entity boosting")
else:
    print("  ⚠ Low enrichment rate - may need to rebuild enrichment")
    print("  Run: python src/indexing/metadata_enricher.py")
