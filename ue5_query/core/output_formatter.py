
# python
# ===== File: output_formatter.py =====
"""
Structured output formatting for hybrid query results.
Supports JSON, JSONL, XML, Markdown, and Code-only formats for AI agent consumption.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats"""
    TEXT = "text"           # Human-readable (default)
    JSON = "json"           # Structured JSON
    JSONL = "jsonl"         # JSON Lines (one object per line)
    XML = "xml"             # XML format
    MARKDOWN = "markdown"   # Enhanced markdown
    CODE = "code"           # Just code snippets
    PATH = "path"           # Just file paths


class OutputFormatter:
    """Format hybrid query results for different consumers (humans vs AI agents)"""

    @staticmethod
    def format(
        results: Dict[str, Any],
        format_type: OutputFormat = OutputFormat.TEXT,
        include_code: bool = True,
        max_snippet_lines: int = 1000
    ) -> str:
        """
        Format query results according to specified format.

        Args:
            results: HybridQueryEngine.query() result dictionary
            format_type: Output format (TEXT, JSON, JSONL, XML, MARKDOWN, CODE, PATH)
            include_code: Include code snippets (default: True)
            max_snippet_lines: Max lines per code snippet (default: 50)

        Returns:
            Formatted string output
        """
        if format_type == OutputFormat.JSON:
            return OutputFormatter._to_json(results, include_code)
        elif format_type == OutputFormat.JSONL:
            return OutputFormatter._to_jsonl(results, include_code)
        elif format_type == OutputFormat.XML:
            return OutputFormatter._to_xml(results, include_code)
        elif format_type == OutputFormat.MARKDOWN:
            return OutputFormatter._to_markdown(results, include_code, max_snippet_lines)
        elif format_type == OutputFormat.CODE:
            return OutputFormatter._to_code_only(results, max_snippet_lines)
        elif format_type == OutputFormat.PATH:
            return OutputFormatter._to_path(results)
        else:
            # TEXT format - use existing print_results logic
            return OutputFormatter._to_text(results)

    @staticmethod
    def _to_json(results: Dict[str, Any], include_code: bool) -> str:
        """Format as structured JSON"""
        # Safely extract intent with defaults
        intent = results.get("intent", {})
        if not isinstance(intent, dict):
            intent = {}

        output = {
            "query": {
                "question": str(results.get("question", "")),
                "intent": intent,
            },
            "results": {
                "definitions": [],
                "semantic": [],
                "combined": results.get("combined_results", [])
            },
            "timing": results.get("timing", {}),
            "metadata": {
                "total_results": len(results.get("combined_results", [])),
                "definition_count": len(results.get("definition_results", [])),
                "semantic_count": len(results.get("semantic_results", []))
            }
        }

        # Add definition results
        for def_result in results.get("definition_results", []):
            if not isinstance(def_result, dict):
                continue  # Skip malformed results

            # Extract match_quality safely - it might be string or float
            match_quality = def_result.get("match_quality", 0.0)
            if isinstance(match_quality, str):
                try:
                    match_quality = float(match_quality)
                except (ValueError, TypeError):
                    match_quality = 0.0

            item = {
                "type": "definition",
                "entity_type": str(def_result.get("entity_type", "")),
                "entity_name": str(def_result.get("entity_name", "")),
                "file_path": str(def_result.get("file_path", "")),
                "line_start": int(def_result.get("line_start", 0)),
                "line_end": int(def_result.get("line_end", 0)),
                "match_quality": float(match_quality),
                "members_count": int(def_result.get("total_members", len(def_result.get("members", [])))),
                "origin": str(def_result.get("origin", "engine"))
            }

            if include_code:
                item["definition"] = str(def_result.get("definition", ""))
                members = def_result.get("members", [])
                item["members"] = [str(m) for m in members] if isinstance(members, list) else []

            output["results"]["definitions"].append(item)

        # Add semantic results
        for sem_result in results.get("semantic_results", []):
            if not isinstance(sem_result, dict):
                continue  # Skip malformed results

            item = {
                "type": "semantic",
                "path": str(sem_result.get("path", "")),
                "chunk_index": int(sem_result.get("chunk_index", 0)),
                "total_chunks": int(sem_result.get("total_chunks", 1)),
                "score": float(sem_result.get("score", 0.0)),
                "origin": str(sem_result.get("origin", "engine"))
            }

            # Add enriched metadata if available
            if "entities" in sem_result and sem_result["entities"]:
                entities = sem_result["entities"]
                item["entities"] = [str(e) for e in entities] if isinstance(entities, list) else []

            if "entity_type" in sem_result and sem_result["entity_type"]:
                item["entity_type"] = str(sem_result["entity_type"])

            output["results"]["semantic"].append(item)

        return json.dumps(output, indent=2)

    @staticmethod
    def _to_jsonl(results: Dict[str, Any], include_code: bool) -> str:
        """Format as JSON Lines (one object per line for streaming)"""
        lines = []

        # Query metadata
        lines.append(json.dumps({
            "type": "query_metadata",
            "question": results.get("question", ""),
            "intent": results.get("intent", {}),
            "timestamp": results.get("timing", {})
        }))

        # Definition results - def_result is already a dict
        for def_result in results.get("definition_results", []):
            item = {
                "type": "definition",
                "entity_type": def_result.get("entity_type", ""),
                "entity_name": def_result.get("entity_name", ""),
                "file_path": def_result.get("file_path", ""),
                "line_start": def_result.get("line_start", 0),
                "line_end": def_result.get("line_end", 0),
                "match_quality": def_result.get("match_quality", 0.0),
                "origin": def_result.get("origin", "engine")
            }

            if include_code:
                item["definition"] = def_result.get("definition", "")
                item["members"] = def_result.get("members", [])

            lines.append(json.dumps(item))

        # Semantic results
        for sem_result in results.get("semantic_results", []):
            item = {
                "type": "semantic",
                "path": sem_result.get("path", ""),
                "chunk_index": sem_result.get("chunk_index", 0),
                "score": sem_result.get("score", 0.0),
                "origin": sem_result.get("origin", "engine")
            }

            if "entities" in sem_result and sem_result["entities"]:
                item["entities"] = sem_result["entities"]

            lines.append(json.dumps(item))

        # Timing
        lines.append(json.dumps({
            "type": "timing",
            **results.get("timing", {})
        }))

        return "\n".join(lines)

    @staticmethod
    def _to_xml(results: Dict[str, Any], include_code: bool) -> str:
        """Format as XML for legacy integrations"""
        root = ET.Element("query_result")

        # Query element
        query_elem = ET.SubElement(root, "query")
        question_elem = ET.SubElement(query_elem, "question")
        question_elem.text = results.get("question", "")

        intent = results.get("intent", {})
        intent_elem = ET.SubElement(query_elem, "intent")
        for key, value in intent.items():
            elem = ET.SubElement(intent_elem, key)
            elem.text = str(value) if value is not None else ""

        # Results element
        results_elem = ET.SubElement(root, "results")

        # Definitions - def_result is already a dict
        defs_elem = ET.SubElement(results_elem, "definitions")
        for def_result in results.get("definition_results", []):
            def_elem = ET.SubElement(defs_elem, "definition")

            entity_type_elem = ET.SubElement(def_elem, "entity_type")
            entity_type_elem.text = def_result.get("entity_type", "")

            entity_name_elem = ET.SubElement(def_elem, "entity_name")
            entity_name_elem.text = def_result.get("entity_name", "")

            file_path_elem = ET.SubElement(def_elem, "file_path")
            file_path_elem.text = def_result.get("file_path", "")

            line_start_elem = ET.SubElement(def_elem, "line_start")
            line_start_elem.text = str(def_result.get("line_start", 0))

            line_end_elem = ET.SubElement(def_elem, "line_end")
            line_end_elem.text = str(def_result.get("line_end", 0))

            match_quality = def_result.get("match_quality", 0.0)
            if isinstance(match_quality, (int, float)):
                match_quality_elem = ET.SubElement(def_elem, "match_quality")
                match_quality_elem.text = f"{match_quality:.2f}"

            origin_elem = ET.SubElement(def_elem, "origin")
            origin_elem.text = def_result.get("origin", "engine")

            if include_code:
                definition = def_result.get("definition", "")
                if definition:
                    code_elem = ET.SubElement(def_elem, "definition")
                    code_elem.text = definition

                members = def_result.get("members", [])
                if members:
                    members_elem = ET.SubElement(def_elem, "members")
                    for member in members[:10]:  # Limit to avoid huge XML
                        member_elem = ET.SubElement(members_elem, "member")
                        member_elem.text = str(member)

        # Semantic results
        sem_elem = ET.SubElement(results_elem, "semantic")
        for sem_result in results.get("semantic_results", []):
            result_elem = ET.SubElement(sem_elem, "result")

            path_elem = ET.SubElement(result_elem, "path")
            path_elem.text = sem_result.get("path", "")

            score_elem = ET.SubElement(result_elem, "score")
            score_elem.text = f"{sem_result.get('score', 0.0):.3f}"

            origin_elem = ET.SubElement(result_elem, "origin")
            origin_elem.text = sem_result.get("origin", "engine")

            if "entities" in sem_result and sem_result["entities"]:
                entities_elem = ET.SubElement(result_elem, "entities")
                for entity in sem_result["entities"]:
                    entity_elem = ET.SubElement(entities_elem, "entity")
                    entity_elem.text = str(entity) if entity is not None else ""

        # Timing
        timing_elem = ET.SubElement(root, "timing")
        for key, value in results.get("timing", {}).items():
            if isinstance(value, (int, float)):
                time_elem = ET.SubElement(timing_elem, key)
                time_elem.text = f"{value:.3f}"

        return ET.tostring(root, encoding='unicode', method='xml')

    @staticmethod
    def _to_markdown(results: Dict[str, Any], include_code: bool, max_lines: int) -> str:
        """Format as enhanced markdown"""
        lines = []

        # Header
        question = results.get("question", "")
        lines.append(f"# Query: {question}")
        lines.append("")

        # Intent
        intent = results.get("intent", {})
        intent_type = intent.get("query_type", "unknown")
        confidence = intent.get("confidence", 0.0)
        lines.append(f"**Intent:** {intent_type} (confidence: {confidence:.2f})")
        lines.append("")

        # Definition results
        def_results = results.get("definition_results", [])
        if def_results:
            lines.append(f"## Definitions ({len(def_results)})")
            lines.append("")

            for i, def_result in enumerate(def_results, 1):
                if not isinstance(def_result, dict):
                    continue  # Skip malformed results

                # def_result is already a dict from hybrid_query._format_def_result
                entity_type = str(def_result.get("entity_type", ""))
                entity_name = str(def_result.get("entity_name", ""))
                file_path = str(def_result.get("file_path", ""))
                line_start = def_result.get("line_start", 0)
                line_end = def_result.get("line_end", 0)

                # Handle match_quality which might be string or float
                match_quality = def_result.get("match_quality", 0.0)
                if isinstance(match_quality, str):
                    try:
                        match_quality = float(match_quality)
                    except (ValueError, TypeError):
                        match_quality = 0.0

                members = def_result.get("members", [])
                if not isinstance(members, list):
                    members = []

                definition = str(def_result.get("definition", ""))

                lines.append(f"### {i}. {entity_type} `{entity_name}`")
                lines.append(f"**File:** `{file_path}:{line_start}-{line_end}`")
                lines.append(f"**Match Quality:** {match_quality:.2f}")

                if members:
                    member_strs = [str(m) for m in members[:5]]
                    lines.append(f"**Members ({len(members)}):** {', '.join(member_strs)}")
                    if len(members) > 5:
                        lines.append(f"... and {len(members) - 5} more")

                if include_code and definition:
                    lines.append("")
                    lines.append("```cpp")
                    all_code_lines = definition.split('\n')
                    code_lines = all_code_lines[:max_lines]
                    lines.extend(code_lines)
                    if len(all_code_lines) > max_lines:
                        remaining_lines = len(all_code_lines) - max_lines
                        lines.append(f"... ({remaining_lines} more lines)")
                    lines.append("```")

                lines.append("")

        # Semantic results
        sem_results = results.get("semantic_results", [])
        if sem_results:
            lines.append(f"## Semantic Matches ({len(sem_results)})")
            lines.append("")

            for i, sem_result in enumerate(sem_results, 1):
                path = Path(sem_result.get("path", "")).name
                score = sem_result.get("score", 0.0)
                origin = sem_result.get("origin", "engine")

                lines.append(f"{i}. **{path}** (score: {score:.3f}, origin: {origin})")

                if "entities" in sem_result and sem_result["entities"]:
                    entities = ", ".join(sem_result["entities"][:5])
                    lines.append(f"   - Entities: {entities}")

            lines.append("")

        # Timing
        timing = results.get("timing", {})
        if timing:
            lines.append("## Performance")
            for key, value in timing.items():
                lines.append(f"- {key}: {value:.3f}s")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _to_code_only(results: Dict[str, Any], max_lines: int) -> str:
        """Extract just code snippets (useful for context building)"""
        snippets = []

        # Definition code - def_result is already a dict
        for def_result in results.get("definition_results", []):
            entity_type = def_result.get("entity_type", "")
            entity_name = def_result.get("entity_name", "")
            file_path = def_result.get("file_path", "")
            line_start = def_result.get("line_start", 0)
            definition = def_result.get("definition", "")

            if not definition:
                continue

            header = f"// {entity_type} {entity_name}"
            location = f"// File: {file_path}:{line_start}"

            all_code_lines = definition.split('\n')
            code_lines = all_code_lines[:max_lines]
            code = '\n'.join(code_lines)

            if len(all_code_lines) > max_lines:
                remaining = len(all_code_lines) - max_lines
                code += f"\n// ... ({remaining} more lines)"

            snippet = f"{header}\n{location}\n{code}\n"
            snippets.append(snippet)

        return "\n".join(snippets) if snippets else "// No code snippets available"

    @staticmethod
    def _to_path(results: Dict[str, Any]) -> str:
        """Extract just file paths (useful for file opening integrations)"""
        paths = []

        # Prioritize definition results
        for def_result in results.get("definition_results", []):
            file_path = def_result.get("file_path", "")
            if file_path and file_path not in paths:
                paths.append(file_path)

        # Fallback to semantic results if no definitions found
        if not paths:
            for sem_result in results.get("semantic_results", []):
                file_path = sem_result.get("path", "")
                if file_path and file_path not in paths:
                    paths.append(file_path)

        return "\n".join(paths) if paths else "No files found"

    @staticmethod
    def _to_text(results: Dict[str, Any]) -> str:
        """Format as human-readable text (default format)"""
        # Import here to avoid circular dependency
        from ue5_query.core.hybrid_query import print_results

        # Capture print output to string
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            print_results(results, show_reasoning=False)
            output = buffer.getvalue()
        finally:
            sys.stdout = old_stdout

        return output


def main():
    """Test output formatter with sample data"""
    from pathlib import Path
    from dataclasses import dataclass

    # Mock definition result
    @dataclass
    class MockDefResult:
        entity_type = "struct"
        entity_name = "FHitResult"
        file_path = "Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h"
        line_start = 42
        line_end = 150
        match_quality = 1.0
        definition = """struct ENGINE_API FHitResult
{
    UPROPERTY()
    float Time;

    UPROPERTY()
    FVector ImpactPoint;

    UPROPERTY()
    FVector ImpactNormal;
};"""
        members = ["float Time", "FVector ImpactPoint", "FVector ImpactNormal"]

    # Mock results
    mock_results = {
        "question": "FHitResult members",
        "intent": {
            "query_type": "hybrid",
            "confidence": 0.85,
            "entity_name": "FHitResult"
        },
        "definition_results": [MockDefResult()],
        "semantic_results": [
            {
                "path": "Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h",
                "chunk_index": 2,
                "total_chunks": 5,
                "score": 0.95,
                "origin": "engine",
                "entities": ["FHitResult", "FVector"]
            }
        ],
        "combined_results": [],
        "timing": {
            "intent_analysis": 0.002,
            "definition_extraction": 0.35,
            "semantic_search": 0.78,
            "total": 1.13
        }
    }

    print("=== Testing Output Formats ===\n")

    # Test JSON
    print("1. JSON Format:")
    print(OutputFormatter.format(mock_results, OutputFormat.JSON)[:500])
    print("...\n")

    # Test JSONL
    print("2. JSONL Format:")
    print(OutputFormatter.format(mock_results, OutputFormat.JSONL)[:300])
    print("...\n")

    # Test Markdown
    print("3. Markdown Format:")
    print(OutputFormatter.format(mock_results, OutputFormat.MARKDOWN)[:500])
    print("...\n")

    # Test Code-only
    print("4. Code-only Format:")
    print(OutputFormatter.format(mock_results, OutputFormat.CODE))


if __name__ == "__main__":
    main()