# python
# ===== File: DefinitionExtractor.py =====
"""
Precise C++ definition extraction using regex patterns.
Extracts complete definitions of structs, classes, enums, and functions from UE5 source code.
"""
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

@dataclass
class DefinitionResult:
    """Result of a definition extraction"""
    file_path: str
    line_start: int
    line_end: int
    definition: str
    entity_type: str  # 'struct', 'class', 'enum', 'function'
    entity_name: str
    members: List[str] = field(default_factory=list)
    match_quality: float = 1.0  # 0.0 to 1.0, for fuzzy matching

    def __str__(self):
        return f"{self.entity_type.upper()} {self.entity_name} @ {self.file_path}:{self.line_start}"


class DefinitionExtractor:
    """Extract exact C++ definitions from source files using regex"""

    # Regex patterns for different entity types
    # UE5-specific: Capture USTRUCT, UCLASS, UENUM, UFUNCTION macros

    STRUCT_PATTERN = re.compile(
        r'^\s*(USTRUCT\s*\([^)]*\)\s*)?'  # Optional USTRUCT macro
        r'struct\s+'                       # struct keyword
        r'(\w+_API\s+)?'                   # Optional API export (ENGINE_API, etc.)
        r'([A-Z_]\w*)'                     # Struct name (F-prefix)
        r'\s*(?::\s*public\s+\w+)?'       # Optional inheritance
        r'\s*\{',                          # Opening brace
        re.MULTILINE
    )

    CLASS_PATTERN = re.compile(
        r'^\s*(UCLASS\s*\([^)]*\)\s*)?'   # Optional UCLASS macro
        r'class\s+'                        # class keyword
        r'(\w+_API\s+)?'                   # Optional API export
        r'([UAI][A-Z]\w*)'                 # Class name (U/A/I-prefix)
        r'\s*(?::\s*public\s+[\w\s,]+)?'  # Optional inheritance (may be multiple)
        r'\s*\{',                          # Opening brace
        re.MULTILINE
    )

    ENUM_PATTERN = re.compile(
        r'^\s*(UENUM\s*\([^)]*\)\s*)?'    # Optional UENUM macro
        r'enum\s+'                         # enum keyword
        r'(?:class\s+)?'                   # Optional 'class' for enum class
        r'([A-Z_]\w*)'                     # Enum name (E-prefix typically)
        r'\s*(?::\s*\w+)?'                 # Optional underlying type
        r'\s*\{',                          # Opening brace
        re.MULTILINE
    )

    # Function/delegate patterns - more complex
    FUNCTION_PATTERN = re.compile(
        r'^\s*(UFUNCTION\s*\([^)]*\)\s*)?'  # Optional UFUNCTION macro
        r'(?:virtual\s+)?'                   # Optional virtual
        r'(?:static\s+)?'                    # Optional static
        r'(?:inline\s+)?'                    # Optional inline
        r'([\w:<>,\*&\s]+)'                  # Return type (can be complex)
        r'\s+(\w+)\s*\(',                    # Function name + open paren
        re.MULTILINE
    )

    # Delegate declaration pattern
    DELEGATE_PATTERN = re.compile(
        r'^\s*DECLARE_\w+_DELEGATE[^(]*\('  # DECLARE_DYNAMIC_MULTICAST_DELEGATE, etc.
        r'\s*(\w+)\s*,',                     # Delegate type name
        re.MULTILINE
    )

    def __init__(self, files: List[Path]):
        """Initialize with list of files to search"""
        self.files = files

    def extract_struct(self, name: str, fuzzy: bool = False) -> List[DefinitionResult]:
        """Extract struct definition(s) matching name"""
        return self._extract_entity(name, 'struct', self.STRUCT_PATTERN, fuzzy)

    def extract_class(self, name: str, fuzzy: bool = False) -> List[DefinitionResult]:
        """Extract class definition(s) matching name"""
        return self._extract_entity(name, 'class', self.CLASS_PATTERN, fuzzy)

    def extract_enum(self, name: str, fuzzy: bool = False) -> List[DefinitionResult]:
        """Extract enum definition(s) matching name"""
        return self._extract_entity(name, 'enum', self.ENUM_PATTERN, fuzzy)

    def extract_function(self, name: str, fuzzy: bool = False) -> List[DefinitionResult]:
        """Extract function definition(s) matching name"""
        results = []

        # Try function pattern
        func_results = self._extract_entity(name, 'function', self.FUNCTION_PATTERN, fuzzy, group_idx=2)
        results.extend(func_results)

        # Also try delegate pattern
        delegate_results = self._extract_entity(name, 'delegate', self.DELEGATE_PATTERN, fuzzy, group_idx=1)
        results.extend(delegate_results)

        return results

    def _extract_entity(
        self,
        name: str,
        entity_type: str,
        pattern: re.Pattern,
        fuzzy: bool,
        group_idx: int = -1  # Index of group containing entity name
    ) -> List[DefinitionResult]:
        """Generic entity extraction"""
        results = []
        name_lower = name.lower()

        for file_path in self.files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.splitlines()

                # Search for pattern matches
                for match in pattern.finditer(content):
                    # Extract entity name from capture groups
                    if group_idx < 0:
                        # Auto-detect: find last captured group with capital letter start
                        entity_name = None
                        for g in reversed(match.groups()):
                            if g and g[0].isupper():
                                entity_name = g
                                break
                    else:
                        entity_name = match.group(group_idx)

                    if not entity_name:
                        continue

                    # Check name match
                    match_quality = self._match_quality(name, entity_name, fuzzy)
                    if match_quality == 0.0:
                        continue

                    # Find line number of match
                    line_start = content[:match.start()].count('\n') + 1

                    # Extract complete definition (find closing brace)
                    definition, line_end = self._extract_definition_block(
                        content, match.end(), lines, line_start
                    )

                    if not definition:
                        continue

                    # Parse members/parameters
                    members = self._parse_members(definition, entity_type)

                    results.append(DefinitionResult(
                        file_path=str(file_path),
                        line_start=line_start,
                        line_end=line_end,
                        definition=definition,
                        entity_type=entity_type,
                        entity_name=entity_name,
                        members=members,
                        match_quality=match_quality
                    ))

            except (OSError, UnicodeDecodeError) as e:
                # Skip unreadable files
                continue

        # Sort by match quality (exact matches first)
        results.sort(key=lambda r: (-r.match_quality, r.file_path))
        return results

    def _match_quality(self, query: str, candidate: str, fuzzy: bool) -> float:
        """Calculate match quality (0.0 = no match, 1.0 = exact match)

        Handles UE5 naming conventions with prefix stripping:
        - F-prefix for structs (FHitResult)
        - U/A/I-prefix for classes (UObject, AActor, IInterface)
        - E-prefix for enums (ECollisionChannel)
        """
        query_lower = query.lower()
        candidate_lower = candidate.lower()

        # Exact match
        if query == candidate or query_lower == candidate_lower:
            return 1.0

        # Case-insensitive match
        if query_lower == candidate_lower:
            return 0.95

        # UE5 prefix handling - strip common prefixes and compare
        query_stripped = self._strip_ue_prefix(query)
        candidate_stripped = self._strip_ue_prefix(candidate)
        query_stripped_lower = query_stripped.lower()
        candidate_stripped_lower = candidate_stripped.lower()

        # Match without prefix (e.g., "HitResult" matches "FHitResult")
        if query_stripped_lower == candidate_stripped_lower:
            return 0.90  # High quality match

        # Query missing prefix but candidate has it (e.g., "hitresult" vs "FHitResult")
        if query_lower == candidate_stripped_lower:
            return 0.88

        # Candidate missing prefix but query has it (rare but possible)
        if query_stripped_lower == candidate_lower:
            return 0.85

        if not fuzzy:
            return 0.0  # Strict mode: no further fuzzy matching

        # Substring match (with prefix stripped)
        if query_stripped_lower in candidate_stripped_lower:
            ratio = len(query_stripped_lower) / len(candidate_stripped_lower)
            return 0.75 * ratio

        # Original substring match (fallback)
        if query_lower in candidate_lower:
            ratio = len(query_lower) / len(candidate_lower)
            return 0.70 * ratio

        # Prefix match (with UE prefix stripped)
        if candidate_stripped_lower.startswith(query_stripped_lower):
            ratio = len(query_stripped_lower) / len(candidate_stripped_lower)
            return 0.80 * ratio

        # Levenshtein distance on stripped names
        distance = self._levenshtein(query_stripped_lower, candidate_stripped_lower)
        max_len = max(len(query_stripped_lower), len(candidate_stripped_lower))

        if distance <= 2 and max_len > 3:  # Allow up to 2 typos
            similarity = 1.0 - (distance / max_len)
            return 0.65 * similarity

        # Levenshtein on original (fallback)
        distance_orig = self._levenshtein(query_lower, candidate_lower)
        max_len_orig = max(len(query_lower), len(candidate_lower))

        if distance_orig <= 2 and max_len_orig > 3:
            similarity = 1.0 - (distance_orig / max_len_orig)
            return 0.60 * similarity

        return 0.0

    def _strip_ue_prefix(self, name: str) -> str:
        """Strip common UE5 prefixes from entity names

        Examples:
        - FHitResult -> HitResult
        - UObject -> Object
        - AActor -> Actor
        - IInterface -> Interface
        - ECollisionChannel -> CollisionChannel
        """
        if len(name) < 2:
            return name

        # Check for UE5 prefix patterns
        if name[0] in 'FUAIE' and name[1].isupper():
            return name[1:]

        return name

    def _levenshtein(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _extract_definition_block(
        self,
        content: str,
        start_pos: int,
        lines: List[str],
        start_line: int
    ) -> Tuple[str, int]:
        """Extract complete definition block by matching braces"""
        # start_pos is right after the opening brace from regex match
        # We need to find that brace and track from there

        # Back up to find the opening brace (regex match ended at the brace)
        current_pos = start_pos - 1
        while current_pos >= 0 and content[current_pos] != '{':
            current_pos -= 1

        if current_pos < 0:
            return "", start_line

        # Now current_pos is at the opening brace
        opening_brace_pos = current_pos
        start_definition = current_pos
        current_pos += 1  # Move past opening brace
        brace_count = 1  # We've seen the opening brace

        # Match braces
        in_string = False
        in_comment = False
        escape_next = False

        while current_pos < len(content) and brace_count > 0:
            char = content[current_pos]
            prev_char = content[current_pos - 1] if current_pos > 0 else ''

            # Handle escape sequences
            if escape_next:
                escape_next = False
                current_pos += 1
                continue

            if char == '\\':
                escape_next = True
                current_pos += 1
                continue

            # Handle strings
            if char == '"' and not in_comment:
                in_string = not in_string

            # Handle comments
            if not in_string:
                if char == '/' and current_pos + 1 < len(content):
                    next_char = content[current_pos + 1]
                    if next_char == '/':
                        # Line comment - skip to end of line
                        while current_pos < len(content) and content[current_pos] != '\n':
                            current_pos += 1
                        continue
                    elif next_char == '*':
                        # Block comment - skip to */
                        in_comment = True
                        current_pos += 2
                        continue

                if in_comment and char == '*' and current_pos + 1 < len(content):
                    if content[current_pos + 1] == '/':
                        in_comment = False
                        current_pos += 2
                        continue

            # Count braces (only outside strings and comments)
            if not in_string and not in_comment:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

            current_pos += 1

        # Extract definition text
        end_definition = current_pos
        definition_text = content[start_definition-1:end_definition]  # Include braces

        # Calculate end line
        end_line = start_line + definition_text.count('\n')

        return definition_text.strip(), end_line

    def _parse_members(self, definition: str, entity_type: str) -> List[str]:
        """Parse members/fields from definition"""
        members = []

        if entity_type in ['struct', 'class']:
            # Extract UPROPERTY members
            uproperty_pattern = re.compile(
                r'UPROPERTY\s*\([^)]*\)\s*'  # UPROPERTY macro
                r'([\w:<>,\*&\s]+?)'          # Type
                r'\s+(\w+)\s*;',              # Member name
                re.MULTILINE | re.DOTALL
            )

            for match in uproperty_pattern.finditer(definition):
                member_type = match.group(1).strip()
                member_name = match.group(2).strip()
                members.append(f"{member_type} {member_name}")

            # Also extract non-UPROPERTY members (basic pattern)
            simple_member_pattern = re.compile(
                r'^\s*(?!UPROPERTY|UFUNCTION|//)' # Not a macro or comment
                r'([\w:<>,\*&\s]+?)'              # Type
                r'\s+(\w+)\s*;',                  # Member name
                re.MULTILINE
            )

            for match in simple_member_pattern.finditer(definition):
                member_type = match.group(1).strip()
                member_name = match.group(2).strip()
                # Skip if looks like function or macro
                if '(' not in member_type and not member_type.isupper():
                    member_info = f"{member_type} {member_name}"
                    if member_info not in members:
                        members.append(member_info)

        elif entity_type == 'enum':
            # Extract enum values
            enum_value_pattern = re.compile(
                r'^\s*(\w+)\s*(?:=\s*[^,}]+)?[,}]',  # Enum value with optional assignment
                re.MULTILINE
            )

            for match in enum_value_pattern.finditer(definition):
                value_name = match.group(1).strip()
                if value_name and not value_name.startswith('GENERATED'):
                    members.append(value_name)

        elif entity_type in ['function', 'delegate']:
            # Extract parameters
            # This is simplified - full C++ parameter parsing is complex
            param_section = definition.split('(', 1)
            if len(param_section) > 1:
                params = param_section[1].split(')', 1)[0]
                # Basic comma split (doesn't handle nested templates perfectly)
                for param in params.split(','):
                    param = param.strip()
                    if param and param != 'void':
                        members.append(param)

        return members


def main():
    """Test the definition extractor"""
    import sys
    from pathlib import Path

    if len(sys.argv) < 3:
        print("Usage: python DefinitionExtractor.py <entity_type> <entity_name> [--fuzzy]")
        print("Example: python DefinitionExtractor.py struct FHitResult")
        return

    entity_type = sys.argv[1].lower()
    entity_name = sys.argv[2]
    fuzzy = '--fuzzy' in sys.argv

    # Load file list from vector_meta.json
    import json
    tool_root = Path(__file__).parent.parent.parent
    meta_path = tool_root / "data" / "vector_meta.json"
    if not meta_path.exists():
        print(f"Error: vector_meta.json not found at {meta_path}")
        return

    meta = json.loads(meta_path.read_text())
    file_paths = list(set(Path(item['path']) for item in meta['items']))

    print(f"Searching {len(file_paths)} files for {entity_type} '{entity_name}'...")
    if fuzzy:
        print("(Using fuzzy matching)")

    extractor = DefinitionExtractor(file_paths)

    if entity_type == 'struct':
        results = extractor.extract_struct(entity_name, fuzzy)
    elif entity_type == 'class':
        results = extractor.extract_class(entity_name, fuzzy)
    elif entity_type == 'enum':
        results = extractor.extract_enum(entity_name, fuzzy)
    elif entity_type == 'function':
        results = extractor.extract_function(entity_name, fuzzy)
    else:
        print(f"Unknown entity type: {entity_type}")
        return

    if not results:
        print(f"No {entity_type} found matching '{entity_name}'")
        return

    print(f"\nFound {len(results)} result(s):\n")

    for i, result in enumerate(results, 1):
        print(f"=== Result {i}: {result.entity_name} (quality: {result.match_quality:.2f}) ===")
        print(f"File: {result.file_path}")
        print(f"Lines: {result.line_start}-{result.line_end}")
        print(f"\nDefinition:")
        print(result.definition[:500])  # First 500 chars
        if len(result.definition) > 500:
            print("...")
        print(f"\nMembers ({len(result.members)}):")
        for member in result.members[:10]:  # First 10 members
            print(f"  - {member}")
        if len(result.members) > 10:
            print(f"  ... and {len(result.members) - 10} more")
        print()


if __name__ == "__main__":
    main()