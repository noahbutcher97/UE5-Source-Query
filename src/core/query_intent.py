# python
# ===== File: QueryIntent.py =====
"""
Analyzes user queries to determine the best search strategy.
Routes to definition extraction for structured queries or semantic search for conceptual questions.
"""
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


class QueryType(Enum):
    """Type of query detected"""
    DEFINITION = "definition"      # Extract exact struct/class/enum/function
    SEMANTIC = "semantic"          # Semantic search for concepts
    HYBRID = "hybrid"              # Use both approaches


class EntityType(Enum):
    """C++ entity types"""
    STRUCT = "struct"
    CLASS = "class"
    ENUM = "enum"
    FUNCTION = "function"
    UNKNOWN = "unknown"


@dataclass
class QueryIntent:
    """Result of query analysis"""
    query_type: QueryType
    entity_type: Optional[EntityType]
    entity_name: Optional[str]
    confidence: float  # 0.0 to 1.0

    # Enhanced query for semantic search (if needed)
    enhanced_query: str

    # Explanation for debugging
    reasoning: str


class QueryIntentAnalyzer:
    """Analyzes queries to determine optimal search strategy"""

    # Patterns for detecting definition queries
    DEFINITION_PATTERNS = [
        # "struct FHitResult", "class AActor", "enum ECollisionChannel"
        re.compile(r'\b(struct|class|enum)\s+([A-Z_]\w+)', re.IGNORECASE),

        # "FHitResult struct", "AActor class"
        re.compile(r'\b([A-Z_]\w+)\s+(struct|class|enum)', re.IGNORECASE),

        # "define FHitResult", "definition of FHitResult"
        re.compile(r'\b(define|definition\s+of)\s+([A-Z_]\w+)', re.IGNORECASE),

        # "what is FHitResult", "show me AActor"
        re.compile(r'\b(what\s+is|show\s+me|find)\s+([A-Z_]\w+)', re.IGNORECASE),
    ]

    # Function query patterns
    FUNCTION_PATTERNS = [
        # "LineTraceSingleByChannel function"
        re.compile(r'\b([A-Z]\w+)\s+function', re.IGNORECASE),

        # "function LineTraceSingleByChannel"
        re.compile(r'\bfunction\s+([A-Z]\w+)', re.IGNORECASE),
    ]

    # UE5 naming conventions
    STRUCT_PREFIX = re.compile(r'^F[A-Z]')     # FVector, FHitResult
    CLASS_PREFIX = re.compile(r'^[UAI][A-Z]')  # UObject, AActor, IInterface
    ENUM_PREFIX = re.compile(r'^E[A-Z]')       # ECollisionChannel

    # Keywords that suggest conceptual/semantic search
    CONCEPTUAL_KEYWORDS = [
        'how', 'why', 'when', 'where', 'explain', 'describe',
        'difference between', 'compare', 'best practice',
        'example', 'tutorial', 'guide', 'work', 'works', 'working'
    ]

    # Keywords that suggest definition search
    DEFINITION_KEYWORDS = [
        'members', 'fields', 'properties', 'methods', 'functions',
        'definition', 'declare', 'declared', 'signature',
        'parameters', 'return type', 'inherit', 'base class'
    ]

    def analyze(self, query: str) -> QueryIntent:
        """Analyze query and determine best search strategy"""
        query_lower = query.lower()

        # Try to detect definition queries
        definition_result = self._check_definition_query(query, query_lower)
        if definition_result:
            return definition_result

        # Check for conceptual query indicators
        is_conceptual = any(kw in query_lower for kw in self.CONCEPTUAL_KEYWORDS)
        has_definition_hints = any(kw in query_lower for kw in self.DEFINITION_KEYWORDS)

        # Try to extract entity names from query
        entity_candidates = self._extract_entity_names(query)

        # NEW: Detect bare entity names (single UE5 entity with minimal context)
        # Examples: "FHitResult", "AActor", "UStaticMeshComponent"
        if entity_candidates and not is_conceptual:
            entity_name, entity_type = entity_candidates[0]

            # Check if query is mostly just the entity name (bare lookup)
            # Strip common words and see if entity name dominates
            query_words = query.split()
            significant_words = [w for w in query_words if len(w) > 2 and w.lower() not in ['the', 'what', 'where', 'find', 'show']]

            is_bare_entity = (
                len(significant_words) <= 2 and  # Query is very short
                entity_name in query and         # Entity name is present
                entity_type != EntityType.UNKNOWN  # Valid UE5 entity type detected
            )

            if is_bare_entity:
                # Bare entity name - treat as definition query
                return QueryIntent(
                    query_type=QueryType.DEFINITION,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    confidence=0.85,
                    enhanced_query=query,
                    reasoning=f"Bare entity name detected: {entity_type.value} {entity_name}"
                )

        if entity_candidates and has_definition_hints and not is_conceptual:
            # Query like "FHitResult members" - try hybrid approach
            entity_name, entity_type = entity_candidates[0]
            enhanced = self._enhance_query(query, entity_name, entity_type)

            return QueryIntent(
                query_type=QueryType.HYBRID,
                entity_type=entity_type,
                entity_name=entity_name,
                confidence=0.7,
                enhanced_query=enhanced,
                reasoning=f"Detected entity '{entity_name}' with definition keywords, using hybrid search"
            )

        if is_conceptual:
            # Conceptual query - use semantic search
            return QueryIntent(
                query_type=QueryType.SEMANTIC,
                entity_type=None,
                entity_name=None,
                confidence=0.9,
                enhanced_query=query,
                reasoning="Conceptual question detected, using semantic search"
            )

        # Default to semantic search with possible query enhancement
        enhanced = query
        if entity_candidates:
            entity_name, entity_type = entity_candidates[0]
            enhanced = self._enhance_query(query, entity_name, entity_type)

        return QueryIntent(
            query_type=QueryType.SEMANTIC,
            entity_type=None,
            entity_name=None,
            confidence=0.5,
            enhanced_query=enhanced,
            reasoning="No strong indicators, defaulting to semantic search"
        )

    def _check_definition_query(self, query: str, query_lower: str) -> Optional[QueryIntent]:
        """Check if query explicitly requests a definition"""

        # Check struct/class/enum patterns
        for pattern in self.DEFINITION_PATTERNS:
            match = pattern.search(query)
            if match:
                # Extract entity type and name
                groups = match.groups()
                if len(groups) == 2:
                    # Determine which group is type and which is name
                    if groups[0].lower() in ['struct', 'class', 'enum', 'define', 'definition']:
                        entity_type_str = groups[0].lower()
                        entity_name = groups[1]
                    else:
                        entity_type_str = groups[1].lower()
                        entity_name = groups[0]

                    # Map to EntityType
                    entity_type = EntityType.UNKNOWN
                    if entity_type_str in ['struct', 'define', 'definition']:
                        entity_type = EntityType.STRUCT
                    elif entity_type_str == 'class':
                        entity_type = EntityType.CLASS
                    elif entity_type_str == 'enum':
                        entity_type = EntityType.ENUM

                    # Verify against naming convention if possible
                    if entity_type == EntityType.UNKNOWN:
                        entity_type = self._infer_entity_type(entity_name)

                    return QueryIntent(
                        query_type=QueryType.DEFINITION,
                        entity_type=entity_type,
                        entity_name=entity_name,
                        confidence=0.95,
                        enhanced_query=query,
                        reasoning=f"Explicit definition query detected: {entity_type.value} {entity_name}"
                    )

        # Check function patterns
        for pattern in self.FUNCTION_PATTERNS:
            match = pattern.search(query)
            if match:
                func_name = match.group(1)
                return QueryIntent(
                    query_type=QueryType.DEFINITION,
                    entity_type=EntityType.FUNCTION,
                    entity_name=func_name,
                    confidence=0.9,
                    enhanced_query=query,
                    reasoning=f"Function definition query detected: {func_name}"
                )

        return None

    def _extract_entity_names(self, query: str) -> List[Tuple[str, EntityType]]:
        """Extract potential UE5 entity names from query"""
        candidates = []

        # Find words matching UE5 naming conventions
        words = re.findall(r'\b[A-Z]\w+\b', query)

        for word in words:
            entity_type = self._infer_entity_type(word)
            if entity_type != EntityType.UNKNOWN:
                candidates.append((word, entity_type))

        return candidates

    def _infer_entity_type(self, name: str) -> EntityType:
        """Infer entity type from UE5 naming convention"""
        if self.STRUCT_PREFIX.match(name):
            return EntityType.STRUCT
        elif self.CLASS_PREFIX.match(name):
            return EntityType.CLASS
        elif self.ENUM_PREFIX.match(name):
            return EntityType.ENUM
        elif name[0].isupper():  # Could be a function
            return EntityType.FUNCTION
        return EntityType.UNKNOWN

    def _enhance_query(self, query: str, entity_name: str, entity_type: EntityType) -> str:
        """Enhance query with code-specific keywords for better semantic search"""
        keywords = []
        query_lower = query.lower()

        # Base keywords by entity type
        if entity_type == EntityType.STRUCT:
            keywords = ['struct', 'UPROPERTY', 'fields']
            # Add specific common members if asking about members/fields
            if any(kw in query_lower for kw in ['member', 'field', 'propert']):
                keywords.append('members')
        elif entity_type == EntityType.CLASS:
            keywords = ['class', 'UCLASS', 'UFUNCTION']
            if any(kw in query_lower for kw in ['method', 'function']):
                keywords.append('methods')
        elif entity_type == EntityType.ENUM:
            keywords = ['enum', 'UENUM']
            if 'value' in query_lower:
                keywords.append('values')
        elif entity_type == EntityType.FUNCTION:
            keywords = ['function', 'UFUNCTION']
            if 'param' in query_lower or 'arg' in query_lower:
                keywords.append('parameters')
            if 'return' in query_lower:
                keywords.append('returns')

        # Extract mentioned member names from query (capitalized words that might be members)
        mentioned_members = []
        words = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', query)
        for word in words:
            if word != entity_name:  # Don't duplicate entity name
                mentioned_members.append(word)

        # Add keywords that aren't already in the query
        additional = [kw for kw in keywords if kw.lower() not in query_lower]

        # Build enhanced query
        enhanced = query
        if additional:
            enhanced = f"{query} {' '.join(additional)}"

        # Add mentioned members for better context
        if mentioned_members:
            enhanced = f"{enhanced} {' '.join(mentioned_members)}"

        return enhanced


def main():
    """Test the query intent analyzer"""
    analyzer = QueryIntentAnalyzer()

    test_queries = [
        "struct FHitResult",
        "FHitResult struct",
        "class AActor",
        "what is FHitResult",
        "FHitResult members",
        "how does collision detection work",
        "show me the UWorld class",
        "LineTraceSingleByChannel function",
        "explain physics simulation in UE5",
        "FVector fields and properties",
        "difference between AActor and UObject",
        "ECollisionChannel enum values",
    ]

    print("=== Query Intent Analysis ===\n")
    for query in test_queries:
        intent = analyzer.analyze(query)
        print(f"Query: {query}")
        print(f"  Type: {intent.query_type.value}")
        if intent.entity_name:
            print(f"  Entity: {intent.entity_type.value} {intent.entity_name}")
        print(f"  Confidence: {intent.confidence:.2f}")
        if intent.enhanced_query != query:
            print(f"  Enhanced: {intent.enhanced_query}")
        print(f"  Reasoning: {intent.reasoning}")
        print()


if __name__ == "__main__":
    main()