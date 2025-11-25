# python
# ===== File: MetadataEnricher.py =====
"""
Enriches vector metadata with entity information for better search.
Detects structs, classes, enums, functions in each chunk and tags them.
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict


@dataclass
class ChunkMetadata:
    """Enhanced metadata for a code chunk"""
    # Existing fields
    path: str
    chunk_index: int
    total_chunks: int
    chunk_size: int
    chunk_overlap: int
    chars: int
    sha256: str

    # NEW: Entity detection
    entities: List[str]  # ["FHitResult", "FVector", ...]
    entity_types: List[str]  # ["struct", "class", ...]
    has_uproperty: bool
    has_ufunction: bool
    has_uclass: bool
    has_ustruct: bool
    has_uenum: bool
    is_header: bool
    is_implementation: bool


class MetadataEnricher:
    """Enriches chunk metadata with entity information"""

    # Regex patterns for entity detection
    STRUCT_PATTERN = re.compile(r'\bstruct\s+(?:\w+_API\s+)?([A-Z_]\w+)', re.MULTILINE)
    CLASS_PATTERN = re.compile(r'\bclass\s+(?:\w+_API\s+)?([UAI][A-Z]\w+)', re.MULTILINE)
    ENUM_PATTERN = re.compile(r'\benum\s+(?:class\s+)?([A-Z_]\w+)', re.MULTILINE)
    FUNCTION_PATTERN = re.compile(r'\b([A-Z]\w+)\s*\([^)]*\)\s*(?:const)?\s*(?:override)?\s*[{;]', re.MULTILINE)

    # UE5 macro detection
    UPROPERTY_PATTERN = re.compile(r'\bUPROPERTY\s*\(')
    UFUNCTION_PATTERN = re.compile(r'\bUFUNCTION\s*\(')
    UCLASS_PATTERN = re.compile(r'\bUCLASS\s*\(')
    USTRUCT_PATTERN = re.compile(r'\bUSTRUCT\s*\(')
    UENUM_PATTERN = re.compile(r'\bUENUM\s*\(')

    def enrich_chunk(self, chunk_text: str, existing_meta: Dict) -> ChunkMetadata:
        """Enrich a single chunk with entity metadata"""

        # Extract entities
        entities = set()
        entity_types = []

        # Find structs
        for match in self.STRUCT_PATTERN.finditer(chunk_text):
            name = match.group(1)
            if name not in ['if', 'for', 'while']:  # Avoid false positives
                entities.add(name)
                entity_types.append('struct')

        # Find classes
        for match in self.CLASS_PATTERN.finditer(chunk_text):
            name = match.group(1)
            entities.add(name)
            entity_types.append('class')

        # Find enums
        for match in self.ENUM_PATTERN.finditer(chunk_text):
            name = match.group(1)
            entities.add(name)
            entity_types.append('enum')

        # Detect UE5 macros
        has_uproperty = bool(self.UPROPERTY_PATTERN.search(chunk_text))
        has_ufunction = bool(self.UFUNCTION_PATTERN.search(chunk_text))
        has_uclass = bool(self.UCLASS_PATTERN.search(chunk_text))
        has_ustruct = bool(self.USTRUCT_PATTERN.search(chunk_text))
        has_uenum = bool(self.UENUM_PATTERN.search(chunk_text))

        # File type detection
        path = existing_meta['path']
        is_header = path.endswith('.h') or path.endswith('.hpp')
        is_implementation = path.endswith('.cpp') or path.endswith('.c')

        return ChunkMetadata(
            path=existing_meta['path'],
            chunk_index=existing_meta['chunk_index'],
            total_chunks=existing_meta['total_chunks'],
            chunk_size=existing_meta.get('chunk_size', 1500),
            chunk_overlap=existing_meta.get('chunk_overlap', 200),
            chars=existing_meta.get('chars', 0),
            sha256=existing_meta.get('sha256', ''),
            entities=sorted(entities),
            entity_types=sorted(set(entity_types)),
            has_uproperty=has_uproperty,
            has_ufunction=has_ufunction,
            has_uclass=has_uclass,
            has_ustruct=has_ustruct,
            has_uenum=has_uenum,
            is_header=is_header,
            is_implementation=is_implementation
        )

    def enrich_metadata_file(self, meta_path: Path, output_path: Path = None):
        """Enrich entire metadata file"""
        if output_path is None:
            output_path = meta_path.parent / "vector_meta_enriched.json"

        # Load existing metadata
        meta_data = json.loads(meta_path.read_text())
        items = meta_data['items']

        print(f"Enriching {len(items)} chunks...")

        enriched_items = []
        for i, item in enumerate(items):
            if i % 1000 == 0:
                print(f"  Processed {i}/{len(items)}...")

            # Load chunk text
            try:
                file_path = Path(item['path'])
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                    # Extract chunk
                    chunk_size = item.get('chunk_size', 1500)
                    chunk_overlap = item.get('chunk_overlap', 200)
                    step = chunk_size - chunk_overlap
                    start = item['chunk_index'] * step
                    chunk_text = content[start:start + chunk_size]

                    # Enrich metadata
                    enriched = self.enrich_chunk(chunk_text, item)
                    enriched_items.append(asdict(enriched))
                else:
                    # File doesn't exist, keep original metadata
                    enriched_items.append(item)
            except Exception as e:
                print(f"Error processing {item['path']}: {e}")
                enriched_items.append(item)

        # Save enriched metadata
        enriched_meta = {
            **meta_data,
            'items': enriched_items,
            'enriched': True
        }

        output_path.write_text(json.dumps(enriched_meta, indent=2))
        print(f"\nEnriched metadata saved to: {output_path}")

        # Print statistics
        total_entities = sum(len(item.get('entities', [])) for item in enriched_items)
        chunks_with_entities = sum(1 for item in enriched_items if item.get('entities'))
        chunks_with_uproperty = sum(1 for item in enriched_items if item.get('has_uproperty'))
        chunks_with_uclass = sum(1 for item in enriched_items if item.get('has_uclass'))

        print(f"\nStatistics:")
        print(f"  Total chunks: {len(enriched_items)}")
        print(f"  Chunks with entities: {chunks_with_entities}")
        print(f"  Total entities detected: {total_entities}")
        print(f"  Chunks with UPROPERTY: {chunks_with_uproperty}")
        print(f"  Chunks with UCLASS: {chunks_with_uclass}")


def main():
    """Enrich existing metadata"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python metadata_enricher.py <vector_meta.json> [output.json]")
        print("\nExample:")
        print("  python metadata_enricher.py data/vector_meta.json")
        print("  python metadata_enricher.py data/vector_meta.json data/vector_meta_enriched.json")
        return

    meta_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not meta_path.exists():
        print(f"Error: {meta_path} not found")
        return

    enricher = MetadataEnricher()
    enricher.enrich_metadata_file(meta_path, output_path)


if __name__ == "__main__":
    main()