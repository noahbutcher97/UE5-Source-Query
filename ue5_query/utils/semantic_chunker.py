# python
"""
Semantic chunker for C++ code that respects structural boundaries.
Intelligently splits code at natural boundaries (functions, classes, structs)
while respecting a maximum chunk size.
"""
import re
from typing import List, Tuple
from pathlib import Path


class SemanticChunker:
    """
    Chunks C++ source code at semantic boundaries rather than arbitrary character counts.

    Features:
    - Respects function/class/struct definitions
    - Detects UE5 macro blocks (UCLASS, USTRUCT, UPROPERTY, etc.)
    - Falls back to paragraph/comment boundaries when needed
    - Configurable max chunk size (default 2000 chars)
    - Maintains overlap for context continuity
    """

    # Regex patterns for C++ structural boundaries
    PATTERNS = {
        # Function definitions (matches "ReturnType FunctionName(...) {" or "ReturnType ClassName::FunctionName(...) {")
        'function': re.compile(
            r'^\s*(?:(?:inline|static|virtual|explicit|constexpr|template\s*<[^>]*>)\s+)*'  # Modifiers
            r'(?:[\w:]+\s*(?:<[^>]*>)?)\s+'  # Return type
            r'[\w:]+\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?\s*\{',  # Function signature
            re.MULTILINE
        ),
        # Class/struct definitions
        'class': re.compile(
            r'^\s*(?:class|struct)\s+[\w_]+\s*(?::\s*public\s+[\w_]+)?\s*\{',
            re.MULTILINE
        ),
        # Enum definitions
        'enum': re.compile(
            r'^\s*(?:enum\s+class|enum)\s+[\w_]+\s*(?::\s*[\w_]+)?\s*\{',
            re.MULTILINE
        ),
        # UE5 macros (UCLASS, USTRUCT, etc.)
        'ue_macro': re.compile(
            r'^\s*U(?:CLASS|STRUCT|ENUM|FUNCTION|PROPERTY|INTERFACE)\s*\(',
            re.MULTILINE
        ),
        # Namespace
        'namespace': re.compile(
            r'^\s*namespace\s+[\w_]+\s*\{',
            re.MULTILINE
        ),
        # Comment blocks (/** */ or // -----)
        'comment_block': re.compile(
            r'^\s*(?:/\*\*|//\s*[-=]{5,})',
            re.MULTILINE
        ),
    }

    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 500, overlap: int = 200):
        """
        Args:
            max_chunk_size: Maximum characters per chunk (default 2000)
            min_chunk_size: Minimum chunk size before merging (default 500)
            overlap: Character overlap between chunks for context (default 200)
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, file_path: str = "") -> List[str]:
        """
        Split text into semantic chunks.

        Args:
            text: Source code text to chunk
            file_path: Optional file path for extension-based heuristics

        Returns:
            List of text chunks
        """
        # Small files don't need chunking
        if len(text) <= self.max_chunk_size:
            return [text]

        # Determine if this is a header or implementation file
        is_header = Path(file_path).suffix.lower() in {'.h', '.hpp', '.inl'} if file_path else False

        # Find all structural boundaries
        boundaries = self._find_boundaries(text)

        # Split text at boundaries
        chunks = self._split_at_boundaries(text, boundaries)

        # Post-process: merge small chunks, enforce max size
        chunks = self._post_process_chunks(chunks)

        return chunks

    def _find_boundaries(self, text: str) -> List[Tuple[int, str]]:
        """
        Find all semantic boundaries in the text.

        Returns:
            List of (position, boundary_type) tuples sorted by position
        """
        boundaries = []

        for boundary_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                boundaries.append((match.start(), boundary_type))

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Deduplicate: if multiple boundaries at same position, keep first
        if boundaries:
            deduplicated = [boundaries[0]]
            for pos, btype in boundaries[1:]:
                if pos != deduplicated[-1][0]:
                    deduplicated.append((pos, btype))
            boundaries = deduplicated

        return boundaries

    def _split_at_boundaries(self, text: str, boundaries: List[Tuple[int, str]]) -> List[str]:
        """
        Split text at semantic boundaries while respecting max chunk size.

        Strategy:
        1. Try to split at function/class boundaries
        2. If section too large, split at comment blocks
        3. If still too large, fall back to character-based split with overlap
        """
        if not boundaries:
            # No boundaries found, fall back to character-based chunking
            return self._fallback_chunk(text)

        chunks = []
        last_pos = 0

        for i, (pos, boundary_type) in enumerate(boundaries):
            # Get next boundary position for lookahead
            next_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)

            # Size of section from last_pos to current boundary
            section_size = pos - last_pos

            # If section fits in max size, continue accumulating
            if section_size < self.max_chunk_size:
                continue

            # Section is too large, need to split
            section = text[last_pos:pos]

            # If section itself is reasonable, emit it
            if section.strip():
                chunks.append(section)

            last_pos = pos

        # Handle remaining text
        if last_pos < len(text):
            remaining = text[last_pos:]
            if remaining.strip():
                chunks.append(remaining)

        return chunks if chunks else [text]

    def _post_process_chunks(self, chunks: List[str]) -> List[str]:
        """
        Post-process chunks: merge small chunks, split oversized chunks, add overlap.
        """
        if not chunks:
            return []

        processed = []
        i = 0

        while i < len(chunks):
            chunk = chunks[i]

            # If chunk is too large, split it further
            if len(chunk) > self.max_chunk_size:
                # Try splitting at paragraph boundaries (double newlines)
                sub_chunks = self._split_at_paragraphs(chunk)

                # If still too large, use character-based split
                final_chunks = []
                for sc in sub_chunks:
                    if len(sc) > self.max_chunk_size:
                        final_chunks.extend(self._fallback_chunk(sc))
                    else:
                        final_chunks.append(sc)

                processed.extend(final_chunks)
                i += 1
                continue

            # If chunk is too small and not the last chunk, try merging with next
            if i + 1 < len(chunks) and len(chunk) < self.min_chunk_size:
                merged = chunk + chunks[i + 1]

                # Only merge if combined size is reasonable
                if len(merged) <= self.max_chunk_size:
                    chunks[i + 1] = merged
                    i += 1
                    continue

            processed.append(chunk)
            i += 1

        # Add overlap between chunks for context
        if len(processed) > 1 and self.overlap > 0:
            processed = self._add_overlap(processed)

        return processed

    def _split_at_paragraphs(self, text: str) -> List[str]:
        """Split text at paragraph boundaries (double newlines)."""
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= self.max_chunk_size:
                current += para + "\n\n"
            else:
                if current.strip():
                    chunks.append(current)
                current = para + "\n\n"

        if current.strip():
            chunks.append(current)

        return chunks if chunks else [text]

    def _fallback_chunk(self, text: str) -> List[str]:
        """
        Fallback character-based chunking with overlap.
        Used when semantic chunking fails.
        """
        chunks = []
        step = self.max_chunk_size - self.overlap

        for start in range(0, len(text), step):
            chunk = text[start:start + self.max_chunk_size]

            # Don't emit tiny trailing chunks
            if len(chunk) < 300 and start != 0:
                # Merge with previous chunk if possible
                if chunks:
                    chunks[-1] += chunk
                break

            chunks.append(chunk)

        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        Add overlap between chunks by appending start of next chunk to end of previous.
        This helps maintain context across boundaries.
        """
        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = overlapped[-1]
            curr_chunk = chunks[i]

            # Take last `overlap` chars from current chunk
            overlap_text = curr_chunk[:self.overlap] if len(curr_chunk) > self.overlap else curr_chunk

            # Append to previous chunk (but don't exceed max size)
            if len(prev_chunk) + len(overlap_text) <= self.max_chunk_size:
                overlapped[-1] = prev_chunk + overlap_text

            overlapped.append(curr_chunk)

        return overlapped


def main():
    """Test semantic chunker on sample C++ code"""

    # Sample UE5 C++ code
    sample_code = """
// HitResult.h - Unreal Engine collision result

#include "CoreMinimal.h"
#include "UObject/ObjectMacros.h"

/**
 * Structure containing information about one hit of a trace, such as point of impact and surface normal at that point.
 */
USTRUCT(BlueprintType)
struct ENGINE_API FHitResult
{
    GENERATED_USTRUCT_BODY()

    /** Face index we hit (for complex hits with triangle meshes). */
    UPROPERTY()
    int32 FaceIndex;

    /** 'Time' of impact along trace direction (ranging from 0.0 to 1.0) if there is a hit, indicating time between TraceStart and TraceEnd. */
    UPROPERTY()
    float Time;

    /** The distance from the TraceStart to the Location in world space. */
    UPROPERTY()
    float Distance;

    /** The location in world space where the moving shape would end up against the impacted object. */
    UPROPERTY()
    FVector_NetQuantize Location;

    /** Location in world space of the actual contact of the trace shape with the impacted object. */
    UPROPERTY()
    FVector_NetQuantize ImpactPoint;

    /** Normal of the hit in world space, for the object that was swept. */
    UPROPERTY()
    FVector_NetQuantize Normal;

    /** Normal of the hit in world space, for the object that was hit by the sweep. */
    UPROPERTY()
    FVector_NetQuantize ImpactNormal;

    /** Start location of the trace. */
    UPROPERTY()
    FVector_NetQuantize TraceStart;

    /** End location of the trace. */
    UPROPERTY()
    FVector_NetQuantize TraceEnd;

    FHitResult()
    {
        Init();
    }

    explicit FHitResult(float InTime)
    {
        Init();
        Time = InTime;
    }

    void Init()
    {
        FMemory::Memzero(this, sizeof(FHitResult));
        Time = 1.f;
    }
};
    """

    chunker = SemanticChunker(max_chunk_size=500, min_chunk_size=200, overlap=50)
    chunks = chunker.chunk(sample_code, "HitResult.h")

    print(f"=== Semantic Chunking Test ===")
    print(f"Original size: {len(sample_code)} chars")
    print(f"Number of chunks: {len(chunks)}\n")

    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ({len(chunk)} chars) ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


if __name__ == "__main__":
    main()