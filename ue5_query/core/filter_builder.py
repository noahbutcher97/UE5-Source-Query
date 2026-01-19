# python
# ===== File: filter_builder.py =====
"""
Filter string parser for hybrid queries.
Enables CLI syntax like: "type:struct AND macro:UPROPERTY"

Leverages existing FilteredSearch class for actual filtering logic.
"""
import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass


@dataclass
class ParsedFilter:
    """Parsed filter parameters ready for FilteredSearch"""
    # Entity filters
    entity: Optional[str] = None  # Specific entity name
    entity_type: Optional[str] = None  # struct, class, enum, function

    # Scope filter
    origin: Optional[str] = None  # engine, project

    # UE5 macro filters
    has_uproperty: Optional[bool] = None
    has_uclass: Optional[bool] = None
    has_ufunction: Optional[bool] = None
    has_ustruct: Optional[bool] = None

    # File type filter
    file_type: Optional[str] = None  # header, implementation

    # Boosting hints
    boost_entities: Optional[List[str]] = None
    boost_macros: bool = False

    def to_search_kwargs(self) -> Dict[str, Any]:
        """Convert to FilteredSearch.search() keyword arguments"""
        kwargs = {}

        if self.entity is not None:
            kwargs['entity'] = self.entity
        if self.entity_type is not None:
            kwargs['entity_type'] = self.entity_type
        if self.origin is not None:
            kwargs['origin'] = self.origin
        if self.has_uproperty is not None:
            kwargs['has_uproperty'] = self.has_uproperty
        if self.has_uclass is not None:
            kwargs['has_uclass'] = self.has_uclass
        if self.file_type is not None:
            kwargs['file_type'] = self.file_type
        if self.boost_entities is not None:
            kwargs['boost_entities'] = self.boost_entities
        if self.boost_macros:
            kwargs['boost_macros'] = True

        return kwargs


class FilterBuilder:
    """
    Parse filter strings into FilteredSearch parameters.

    Syntax:
        type:struct              - Filter by entity type
        macro:UPROPERTY          - Filter by UE5 macro
        origin:engine            - Filter by origin (engine/project)
        entity:FHitResult        - Filter to specific entity
        file:header              - Filter by file type
        boost:macros             - Enable macro boosting

    Operators:
        AND - All conditions must match
        OR  - Any condition must match (not yet supported)

    Examples:
        "type:struct AND macro:UPROPERTY"
        "type:class AND origin:engine"
        "entity:FHitResult AND file:header"
        "type:struct AND boost:macros"
    """

    # Pattern: key:value
    FILTER_PATTERN = re.compile(r'(\w+):(\w+)', re.IGNORECASE)

    @staticmethod
    def parse(filter_str: str) -> ParsedFilter:
        """
        Parse filter string into ParsedFilter.

        Args:
            filter_str: Filter string (e.g., "type:struct AND macro:UPROPERTY")

        Returns:
            ParsedFilter with populated fields

        Raises:
            ValueError: If filter string is malformed
        """
        if not filter_str or not filter_str.strip():
            return ParsedFilter()

        # Split by AND (OR not yet supported)
        parts = filter_str.split(' AND ')

        result = ParsedFilter()
        boost_entities_list = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Match key:value pattern
            match = FilterBuilder.FILTER_PATTERN.match(part)
            if not match:
                raise ValueError(f"Invalid filter syntax: '{part}'. Expected format: key:value")

            key = match.group(1).lower()
            value = match.group(2)

            # Parse based on key
            if key == 'type':
                # Entity type filter
                if value.lower() not in ['struct', 'class', 'enum', 'function', 'delegate']:
                    raise ValueError(f"Invalid entity type: '{value}'. Must be struct, class, enum, or function")
                result.entity_type = value.lower()

            elif key == 'macro':
                # UE5 macro filter
                macro_upper = value.upper()
                if macro_upper == 'UPROPERTY':
                    result.has_uproperty = True
                elif macro_upper == 'UCLASS':
                    result.has_uclass = True
                elif macro_upper == 'UFUNCTION':
                    result.has_ufunction = True
                elif macro_upper == 'USTRUCT':
                    result.has_ustruct = True
                else:
                    raise ValueError(f"Unknown macro: '{value}'. Supported: UPROPERTY, UCLASS, UFUNCTION, USTRUCT")

            elif key == 'origin':
                # Origin filter
                if value.lower() not in ['engine', 'project']:
                    raise ValueError(f"Invalid origin: '{value}'. Must be 'engine' or 'project'")
                result.origin = value.lower()

            elif key == 'entity':
                # Specific entity filter
                result.entity = value
                # Also add to boost list
                boost_entities_list.append(value)

            elif key == 'file':
                # File type filter
                if value.lower() not in ['header', 'implementation']:
                    raise ValueError(f"Invalid file type: '{value}'. Must be 'header' or 'implementation'")
                result.file_type = value.lower()

            elif key == 'boost':
                # Boosting hints
                if value.lower() == 'macros':
                    result.boost_macros = True
                elif value.lower() == 'entity' or value.lower() == 'entities':
                    # Boost entities mentioned in query (will be set by caller)
                    pass
                else:
                    raise ValueError(f"Invalid boost type: '{value}'. Supported: macros, entities")

            else:
                raise ValueError(f"Unknown filter key: '{key}'. Supported: type, macro, origin, entity, file, boost")

        # Set boost_entities if any were collected
        if boost_entities_list:
            result.boost_entities = boost_entities_list

        return result

    @staticmethod
    def parse_and_validate(filter_str: str) -> ParsedFilter:
        """
        Parse and validate filter string.
        Returns ParsedFilter or raises ValueError with helpful message.
        """
        try:
            return FilterBuilder.parse(filter_str)
        except ValueError as e:
            # Re-raise with additional context
            raise ValueError(f"Filter parse error: {e}\n\nSupported syntax:\n"
                           "  type:struct|class|enum|function\n"
                           "  macro:UPROPERTY|UCLASS|UFUNCTION|USTRUCT\n"
                           "  origin:engine|project\n"
                           "  entity:EntityName\n"
                           "  file:header|implementation\n"
                           "  boost:macros\n\n"
                           "Use AND to combine filters (OR not yet supported)")


def main():
    """Test filter parser"""
    test_cases = [
        "type:struct",
        "type:struct AND macro:UPROPERTY",
        "type:class AND origin:engine",
        "entity:FHitResult AND file:header",
        "type:struct AND boost:macros",
        "type:class AND macro:UCLASS AND origin:engine",
        # Error cases
        "invalid syntax",
        "type:invalid",
        "macro:UNKNOWN",
    ]

    print("=== Filter Builder Test ===\n")

    for test in test_cases:
        print(f"Input: {test}")
        try:
            result = FilterBuilder.parse(test)
            print(f"  [OK] Parsed successfully")
            print(f"    entity_type: {result.entity_type}")
            print(f"    has_uproperty: {result.has_uproperty}")
            print(f"    has_uclass: {result.has_uclass}")
            print(f"    origin: {result.origin}")
            print(f"    file_type: {result.file_type}")
            print(f"    boost_macros: {result.boost_macros}")

            # Show as search kwargs
            kwargs = result.to_search_kwargs()
            if kwargs:
                print(f"    search_kwargs: {kwargs}")
        except ValueError as e:
            print(f"  [ERROR] {e}")
        print()


if __name__ == "__main__":
    main()
