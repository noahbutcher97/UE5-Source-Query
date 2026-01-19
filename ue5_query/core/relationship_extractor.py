"""
Relationship Extractor - Extract C++ code relationships (inheritance, composition, dependencies)

Analyzes C++ code to build relationship graphs showing:
- Inheritance hierarchies (class Foo : public Bar)
- Composition relationships (member variables)
- Dependencies (#include directives)
- Usage patterns (where entities are used)

Author: AI-assisted development
Date: 2025-12-02
Version: 1.0.0
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum


class RelationshipType(Enum):
    """Types of code relationships"""
    INHERITS = "inherits"           # Child inherits from Parent
    CONTAINS = "contains"           # Class contains Member variable
    USES = "uses"                   # Class uses Type (parameter/return)
    DEPENDS_ON = "depends_on"       # File depends on Header
    IMPLEMENTS = "implements"       # Class implements Interface
    OVERRIDES = "overrides"         # Method overrides Virtual


class RelationshipExtractor:
    """
    Extract relationships from C++ code definitions.

    Capabilities:
    - Parse inheritance (single and multiple)
    - Extract member variables with types
    - Identify UE5-specific patterns (UPROPERTY, components)
    - Build queryable relationship graphs
    """

    # Regex patterns for inheritance
    INHERITANCE_PATTERN = re.compile(
        r'(?:class|struct)\s+(?:\w+_API\s+)?(\w+)\s*:\s*(.+?)\s*\{',
        re.MULTILINE
    )
    PARENT_PATTERN = re.compile(
        r'(?:public|protected|private)?\s*(\w+)',
    )

    # Regex patterns for member variables
    UPROPERTY_MEMBER = re.compile(
        r'UPROPERTY\([^)]*\)\s+([A-Z]\w+(?:<[^>]+>)?(?:\*)*)\s+(\w+)\s*;',
        re.MULTILINE
    )
    REGULAR_MEMBER = re.compile(
        r'^\s+([A-Z]\w+(?:<[^>]+>)?(?:\*)*)\s+(\w+)\s*;\s*(?://.*)?$',
        re.MULTILINE
    )

    # UE5-specific patterns
    UE5_COMPONENT_PATTERN = re.compile(r'U\w*Component\*?\s+(\w+)')
    UE5_OBJECT_PATTERN = re.compile(r'U[A-Z]\w+\*?\s+(\w+)')

    # Include dependencies
    INCLUDE_PATTERN = re.compile(r'#include\s+[<"]([^>"]+)[>"]')

    def __init__(self, script_dir: Path):
        """
        Initialize relationship extractor.

        Args:
            script_dir: Root directory of the project
        """
        self.script_dir = script_dir
        self.graph = {}  # Entity -> Relationships mapping

    def extract_inheritance(self, entity_name: str, definition: str) -> List[str]:
        """
        Extract parent classes from C++ inheritance syntax.

        Handles:
        - class Foo : public Bar
        - class Foo : public Bar, private Baz
        - struct Foo : Bar
        - UCLASS() class Foo : public Bar

        Args:
            entity_name: Name of the entity being analyzed
            definition: Complete code definition

        Returns:
            List of parent class names
        """
        parents = []

        # Find inheritance declaration
        match = self.INHERITANCE_PATTERN.search(definition)
        if not match:
            return parents

        inheritance_list = match.group(2)

        # Extract individual parents (handle multiple inheritance)
        parent_matches = self.PARENT_PATTERN.findall(inheritance_list)
        for parent in parent_matches:
            # Filter out access specifiers that might have been captured
            if parent not in ['public', 'protected', 'private']:
                parents.append(parent)

        return parents

    def extract_composition(self, entity_name: str, definition: str) -> List[Dict]:
        """
        Extract member variables and their types.

        Handles:
        - UPROPERTY() members
        - Regular C++ members
        - Templates (TArray, TMap, etc.)
        - Pointers (U*)
        - UE5 components

        Args:
            entity_name: Name of the entity being analyzed
            definition: Complete code definition

        Returns:
            List of dicts with 'name', 'type', and 'ue5_macro' keys
        """
        members = []
        seen_names = set()  # Avoid duplicates

        # Extract UPROPERTY members (prioritize these)
        for match in self.UPROPERTY_MEMBER.finditer(definition):
            member_type = match.group(1)
            member_name = match.group(2)

            if member_name not in seen_names:
                members.append({
                    'name': member_name,
                    'type': member_type,
                    'ue5_macro': 'UPROPERTY',
                    'is_component': 'Component' in member_type,
                    'is_pointer': '*' in member_type
                })
                seen_names.add(member_name)

        # Extract regular members (non-UPROPERTY)
        for match in self.REGULAR_MEMBER.finditer(definition):
            member_type = match.group(1)
            member_name = match.group(2)

            # Skip if already found as UPROPERTY
            if member_name in seen_names:
                continue

            # Only include types that start with capital letter (C++ convention)
            # This filters out keywords like 'int', 'float', 'bool'
            if member_type[0].isupper():
                members.append({
                    'name': member_name,
                    'type': member_type,
                    'ue5_macro': None,
                    'is_component': 'Component' in member_type,
                    'is_pointer': '*' in member_type
                })
                seen_names.add(member_name)

        return members

    def extract_dependencies(self, file_content: str) -> List[str]:
        """
        Extract #include dependencies from file content.

        Args:
            file_content: Raw file content

        Returns:
            List of included header paths
        """
        includes = []

        for match in self.INCLUDE_PATTERN.finditer(file_content):
            include_path = match.group(1)
            includes.append(include_path)

        return includes

    def build_relationship_graph(
        self,
        entity_name: str,
        definition: str,
        file_path: Optional[str] = None
    ) -> Dict:
        """
        Build complete relationship graph for an entity.

        Process:
        1. Extract inheritance relationships
        2. Extract composition relationships
        3. Build structured graph

        Args:
            entity_name: Name of the entity (e.g., "FHitResult")
            definition: Complete code definition
            file_path: Optional file path where entity is defined

        Returns:
            Dict with relationship information
        """
        # Extract relationships
        parents = self.extract_inheritance(entity_name, definition)
        members = self.extract_composition(entity_name, definition)

        # Build graph
        graph = {
            'entity': entity_name,
            'inherits': parents,
            'contains': members,
            'defined_in': file_path or "unknown",
            'has_ue5_macros': any(m['ue5_macro'] for m in members),
            'has_components': any(m['is_component'] for m in members),
            'member_count': len(members),
            'parent_count': len(parents)
        }

        # Cache for future lookups
        self.graph[entity_name] = graph

        return graph

    def format_relationship_tree(
        self,
        entity_name: str,
        graph: Dict,
        depth: int = 2
    ) -> str:
        """
        Format relationships as ASCII tree.

        Example output:
        FHitResult
        ├─ Inherits: (none)
        ├─ Contains (8 members):
        │  ├─ FVector ImpactPoint (UPROPERTY)
        │  ├─ FVector ImpactNormal (UPROPERTY)
        │  └─ float Time
        └─ Defined in: Engine/Source/.../HitResult.h

        Args:
            entity_name: Entity name
            graph: Relationship graph from build_relationship_graph()
            depth: Tree depth (currently not used, reserved for future)

        Returns:
            Formatted ASCII tree string
        """
        lines = []
        lines.append(f"{entity_name}")

        # Inheritance
        if graph['inherits']:
            parents_str = ", ".join(graph['inherits'])
            lines.append(f"+-- Inherits: {parents_str}")
        else:
            lines.append("+-- Inherits: (none)")

        # Composition
        members = graph['contains']
        if members:
            lines.append(f"+-- Contains ({len(members)} members):")
            for i, member in enumerate(members):
                is_last = (i == len(members) - 1)
                prefix = "+--" if is_last else "+--"

                # Build member description
                member_desc = f"{member['type']} {member['name']}"
                if member['ue5_macro']:
                    member_desc += f" ({member['ue5_macro']})"
                if member['is_component']:
                    member_desc += " [Component]"

                lines.append(f"|   {prefix} {member_desc}")
        else:
            lines.append("+-- Contains: (no members)")

        # File location
        lines.append(f"+-- Defined in: {graph['defined_in']}")

        return "\n".join(lines)

    def format_relationship_json(self, graph: Dict) -> Dict:
        """
        Format relationships as JSON-serializable dict.

        Args:
            graph: Relationship graph

        Returns:
            Clean JSON-serializable dict
        """
        return {
            'entity': graph['entity'],
            'relationships': {
                'inherits': graph['inherits'],
                'contains': [
                    {
                        'name': m['name'],
                        'type': m['type'],
                        'macro': m['ue5_macro'],
                        'is_component': m['is_component'],
                        'is_pointer': m['is_pointer']
                    }
                    for m in graph['contains']
                ],
            },
            'metadata': {
                'defined_in': graph['defined_in'],
                'has_ue5_macros': graph['has_ue5_macros'],
                'has_components': graph['has_components'],
                'member_count': graph['member_count'],
                'parent_count': graph['parent_count']
            }
        }


def extract_entity_name(question: str) -> Optional[str]:
    """
    Extract entity name from natural language question.

    Handles:
    - "FHitResult relationships"
    - "show relationships for AActor"
    - "what does UChaosWheeledVehicleMovementComponent contain"

    Args:
        question: Natural language question

    Returns:
        Extracted entity name or None
    """
    # Pattern: Capital letter followed by alphanumeric (UE5 naming convention)
    pattern = r'\b([A-Z][A-Za-z0-9_]+)\b'
    matches = re.findall(pattern, question)

    # Return first match that looks like a UE5 entity
    # (starts with F, A, U, E, T)
    for match in matches:
        if match[0] in ['F', 'A', 'U', 'E', 'T']:
            return match

    # Fallback: return first capitalized word
    if matches:
        return matches[0]

    return None
