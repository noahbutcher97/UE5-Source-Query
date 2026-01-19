import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

from ue5_query.core.hybrid_query import HybridQueryEngine, print_results

# Resolve tool root relative to package location
TOOL_ROOT = Path(__file__).resolve().parent.parent.parent

def query_server(question: str, top_k: int, scope: str, port: int = 8765) -> dict | None:
    """Try to query the running server. Returns None if server is down."""
    params = {
        "q": question,
        "top_k": str(top_k),
        "scope": scope
    }
    url = f"http://127.0.0.1:{port}/search?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, ConnectionRefusedError):
        return None
    except Exception as e:
        # Server exists but returned error
        print(f"[WARN] Server query failed: {e}")
        return None
    return None

def main():
    parser = argparse.ArgumentParser(description="CLI Client for UE5 Source Query")
    parser.add_argument("question", nargs="*", help="Query text (not required if --batch-file used)")
    parser.add_argument("--top-k", type=int, default=5, help="Results to return")
    parser.add_argument("--scope", default="engine", choices=["engine", "project", "all"])

    # Output format options (NEW)
    parser.add_argument("--format", default="text",
                       choices=["text", "json", "jsonl", "xml", "markdown", "code"],
                       help="Output format: text (default), json, jsonl, xml, markdown, code")
    parser.add_argument("--no-code", action="store_true",
                       help="Exclude code from output (metadata only)")
    parser.add_argument("--max-lines", type=int, default=50,
                       help="Maximum lines per code snippet (default: 50)")

    # Filter options (NEW - Phase 2)
    parser.add_argument("--filter", type=str, default=None,
                       help="Filter results (e.g., 'type:struct AND macro:UPROPERTY')")

    # Relationship extraction (NEW - Phase 5)
    parser.add_argument("--relationships", action="store_true",
                       help="Extract and display code relationships (inheritance, composition)")
    parser.add_argument("--depth", type=int, default=2,
                       help="Relationship traversal depth (1-5, default: 2)")

    # Legacy option (deprecated but maintained for backwards compatibility)
    parser.add_argument("--json", action="store_true", help="Output raw JSON (deprecated, use --format json)")

    # Batch processing options (NEW - Phase 4)
    parser.add_argument("--batch-file", type=str, default=None,
                       help="Process multiple queries from JSONL file")
    parser.add_argument("--output", type=str, default=None,
                       help="Output file for batch results (default: stdout)")

    # Server options
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--no-server", action="store_true", help="Force local execution (ignore server)")

    args = parser.parse_args()

    # Handle batch mode
    if args.batch_file:
        from ue5_query.core.batch_query import BatchQueryRunner
        from pathlib import Path

        input_file = Path(args.batch_file)
        output_file = Path(args.output) if args.output else None

        if not input_file.exists():
            print(f"[ERROR] Batch file not found: {input_file}", file=sys.stderr)
            sys.exit(1)

        runner = BatchQueryRunner(TOOL_ROOT, verbose=not args.json)
        runner.run_batch_file(input_file, output_file)
        return

    # Normal single query mode
    if not args.question:
        print("[ERROR] Question required (unless using --batch-file)", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    question = " ".join(args.question)

    # Handle relationships mode (Phase 5)
    if args.relationships:
        from ue5_query.core.relationship_extractor import extract_entity_name
        # Note: HybridQueryEngine already imported at module level

        # Extract entity name from question
        entity_name = extract_entity_name(question)

        if not entity_name:
            print(f"[ERROR] Could not detect entity name in: '{question}'", file=sys.stderr)
            print("[HINT] Try format like: 'FHitResult' or 'AActor relationships'", file=sys.stderr)
            sys.exit(1)

        # Initialize engine and query relationships
        engine = HybridQueryEngine(TOOL_ROOT)
        results = engine.query_relationships(entity_name, depth=args.depth)

        # Check for error
        if "error" in results:
            print(f"[ERROR] {results['error']}", file=sys.stderr)
            sys.exit(1)

        # Format output
        if args.format == "json":
            import json
            print(json.dumps(results, indent=2))
        else:
            # Text/tree output
            print(f"\n{results['tree']}\n")
            print(f"File: {results['file_path']} (lines {results['line_range']})")

        return

    # 1. Try Server
    results = None
    if not args.no_server:
        results = query_server(question, args.top_k, args.scope, args.port)
        if results and not args.json:
            print(f"[INFO] Result from Search Server (Instant)")

    # 2. Fallback to Local
    if not results:
        if not args.no_server and not args.json:
            print("[INFO] Server unavailable. Starting local engine (Cold Start)...")

        # Initialize engine locally
        try:
            # Check for index existence first to give a friendly error
            data_dir = TOOL_ROOT / "data"
            if not (data_dir / "vector_store.npz").exists():
                print(f"\n[ERROR] Search index not found at: {data_dir}")
                print("\nYou must build the index before querying.")
                print("Run: launcher.bat -> Maintenance -> Rebuild Index")
                print("Or:  tools/rebuild-index.bat")
                sys.exit(1)

            engine = HybridQueryEngine(TOOL_ROOT)

            # Parse filter string if provided
            filter_kwargs = {}
            if args.filter:
                from ue5_query.core.filter_builder import FilterBuilder
                try:
                    parsed_filter = FilterBuilder.parse_and_validate(args.filter)
                    filter_kwargs = parsed_filter.to_search_kwargs()
                    if not args.json:
                        print(f"[INFO] Applied filters: {filter_kwargs}")
                except ValueError as e:
                    print(f"[ERROR] {e}", file=sys.stderr)
                    sys.exit(1)

            results = engine.query(
                question=question,
                top_k=args.top_k,
                scope=args.scope,
                show_reasoning=not args.json,
                **filter_kwargs  # Pass parsed filters to engine
            )
        except Exception as e:
            print(f"[ERROR] Engine failed: {e}")
            sys.exit(1)

    # 3. Output
    # Handle legacy --json flag
    if args.json and args.format == "text":
        args.format = "json"

    # Use OutputFormatter for all non-text formats
    if args.format != "text":
        from ue5_query.core.output_formatter import OutputFormatter, OutputFormat

        try:
            format_enum = OutputFormat[args.format.upper()]
            formatted = OutputFormatter.format(
                results,
                format_type=format_enum,
                include_code=not args.no_code,
                max_snippet_lines=args.max_lines
            )
            print(formatted)
        except Exception as e:
            print(f"[ERROR] Formatting failed: {e}", file=sys.stderr)
            # Fallback to raw JSON on error
            print(json.dumps(results, indent=2))
    else:
        # Default text output (human-readable)
        print_results(results, show_reasoning=False)  # Reasoning already printed if local

if __name__ == "__main__":
    main()
