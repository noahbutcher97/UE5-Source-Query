# python
# ===== File: batch_query.py =====
"""
Batch query processing for efficient multi-query execution.
Enables AI agents to process multiple queries from JSONL input files.
"""
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
from dataclasses import dataclass, asdict

from ue5_query.core.hybrid_query import HybridQueryEngine
from ue5_query.core.filter_builder import FilterBuilder

# Resolve tool root relative to package location
TOOL_ROOT = Path(__file__).resolve().parent.parent.parent

@dataclass
class BatchQueryItem:
    """Single query item in a batch"""
    question: str
    top_k: int = 5
    scope: str = "engine"
    filter: Optional[str] = None
    show_reasoning: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchQueryItem':
        """Create from dictionary (JSONL line)"""
        return cls(
            question=data.get('question', ''),
            top_k=data.get('top_k', 5),
            scope=data.get('scope', 'engine'),
            filter=data.get('filter'),
            show_reasoning=data.get('show_reasoning', False)
        )


@dataclass
class BatchQueryResult:
    """Result of a single batch query"""
    query_id: int
    question: str
    status: str  # 'success', 'error'
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timing: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL output"""
        data = {
            'query_id': self.query_id,
            'question': self.question,
            'status': self.status
        }
        if self.results is not None:
            data['results'] = self.results
        if self.error is not None:
            data['error'] = self.error
        if self.timing is not None:
            data['timing'] = self.timing
        return data


class BatchQueryRunner:
    """
    Process multiple queries from JSONL input file.

    Features:
    - Stream processing (memory efficient)
    - Progress reporting
    - Error handling per query (continues on failure)
    - Filter support via FilterBuilder
    - Reuses engine instance (efficient)

    Input Format (JSONL):
        {"question": "FHitResult members", "top_k": 5, "scope": "engine"}
        {"question": "collision detection", "top_k": 3, "filter": "type:struct"}

    Output Format (JSONL):
        {"query_id": 0, "status": "success", "results": {...}, "timing": {...}}
        {"query_id": 1, "status": "success", "results": {...}, "timing": {...}}

    Usage:
        runner = BatchQueryRunner(tool_root)
        runner.run_batch_file('queries.jsonl', 'results.jsonl')
    """

    def __init__(self, tool_root: Path, verbose: bool = True):
        """
        Initialize batch query runner.

        Args:
            tool_root: Root directory of the tool
            verbose: Print progress to stderr
        """
        self.tool_root = tool_root
        self.verbose = verbose
        self.engine = None

    def _ensure_engine(self):
        """Lazy-load engine instance"""
        if self.engine is None:
            if self.verbose:
                print("[INFO] Loading query engine...", file=sys.stderr)
            self.engine = HybridQueryEngine(self.tool_root)

    def run_single_query(self, query_id: int, item: BatchQueryItem) -> BatchQueryResult:
        """
        Execute a single query from batch.

        Args:
            query_id: Unique ID for this query in the batch
            item: Query parameters

        Returns:
            BatchQueryResult with status and results/error
        """
        t_start = time.perf_counter()

        try:
            # Ensure engine is loaded
            self._ensure_engine()

            # Build filter kwargs if filter provided
            filter_kwargs = {}
            if item.filter:
                try:
                    parsed_filter = FilterBuilder.parse_and_validate(item.filter)
                    filter_kwargs = parsed_filter.to_search_kwargs()
                except ValueError as e:
                    return BatchQueryResult(
                        query_id=query_id,
                        question=item.question,
                        status='error',
                        error=f"Filter parse error: {e}"
                    )

            # Execute query
            results = self.engine.query(
                question=item.question,
                top_k=item.top_k,
                scope=item.scope,
                show_reasoning=item.show_reasoning,
                **filter_kwargs
            )

            # Calculate total time
            total_time = time.perf_counter() - t_start
            timing = results.get('timing', {})
            timing['batch_total_s'] = total_time

            return BatchQueryResult(
                query_id=query_id,
                question=item.question,
                status='success',
                results=results,
                timing=timing
            )

        except Exception as e:
            total_time = time.perf_counter() - t_start
            return BatchQueryResult(
                query_id=query_id,
                question=item.question,
                status='error',
                error=str(e),
                timing={'batch_total_s': total_time}
            )

    def run_batch_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
        output_stream: Optional[TextIO] = None
    ) -> List[BatchQueryResult]:
        """
        Process queries from JSONL input file.

        Args:
            input_file: Path to JSONL input file
            output_file: Path to JSONL output file (optional)
            output_stream: Output stream (default: stdout)

        Returns:
            List of BatchQueryResult objects
        """
        results = []

        # Open output stream
        if output_file:
            out = open(output_file, 'w', encoding='utf-8')
        elif output_stream:
            out = output_stream
        else:
            out = sys.stdout

        try:
            # Read and process queries
            with open(input_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse query item
                        data = json.loads(line)
                        item = BatchQueryItem.from_dict(data)

                        if self.verbose:
                            print(f"[{i}] Processing: {item.question[:50]}...", file=sys.stderr)

                        # Execute query
                        result = self.run_single_query(i, item)
                        results.append(result)

                        # Write result to output
                        out.write(json.dumps(result.to_dict()) + '\n')
                        out.flush()

                        if self.verbose:
                            status_emoji = "✓" if result.status == 'success' else "✗"
                            print(f"[{i}] {status_emoji} {result.status}", file=sys.stderr)

                    except json.JSONDecodeError as e:
                        if self.verbose:
                            print(f"[{i}] Error: Invalid JSON - {e}", file=sys.stderr)
                        # Write error result
                        error_result = BatchQueryResult(
                            query_id=i,
                            question="<parse error>",
                            status='error',
                            error=f"JSON parse error: {e}"
                        )
                        results.append(error_result)
                        out.write(json.dumps(error_result.to_dict()) + '\n')
                        out.flush()

            if self.verbose:
                success_count = sum(1 for r in results if r.status == 'success')
                error_count = len(results) - success_count
                print(f"\n[DONE] {len(results)} queries processed: {success_count} success, {error_count} errors", file=sys.stderr)

        finally:
            if output_file:
                out.close()

        return results

    def run_batch_list(
        self,
        queries: List[Dict[str, Any]],
        output_stream: Optional[TextIO] = None
    ) -> List[BatchQueryResult]:
        """
        Process queries from list of dictionaries.

        Args:
            queries: List of query dictionaries
            output_stream: Output stream (default: stdout)

        Returns:
            List of BatchQueryResult objects
        """
        results = []

        # Open output stream
        out = output_stream or sys.stdout

        for i, query_data in enumerate(queries):
            try:
                item = BatchQueryItem.from_dict(query_data)

                if self.verbose:
                    print(f"[{i}] Processing: {item.question[:50]}...", file=sys.stderr)

                # Execute query
                result = self.run_single_query(i, item)
                results.append(result)

                # Write result to output
                out.write(json.dumps(result.to_dict()) + '\n')
                out.flush()

                if self.verbose:
                    status_emoji = "✓" if result.status == 'success' else "✗"
                    print(f"[{i}] {status_emoji} {result.status}", file=sys.stderr)

            except Exception as e:
                if self.verbose:
                    print(f"[{i}] Error: {e}", file=sys.stderr)
                error_result = BatchQueryResult(
                    query_id=i,
                    question=query_data.get('question', '<unknown>'),
                    status='error',
                    error=str(e)
                )
                results.append(error_result)
                out.write(json.dumps(error_result.to_dict()) + '\n')
                out.flush()

        if self.verbose:
            success_count = sum(1 for r in results if r.status == 'success')
            error_count = len(results) - success_count
            print(f"\n[DONE] {len(results)} queries processed: {success_count} success, {error_count} errors", file=sys.stderr)

        return results


def main():
    """CLI interface for batch query processing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch query processor for UE5 Source Query",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", type=Path, help="Input JSONL file with queries")
    parser.add_argument("-o", "--output", type=Path, help="Output JSONL file (default: stdout)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    # Validate input file exists
    if not args.input_file.exists():
        print(f"[ERROR] Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Run batch processing
    runner = BatchQueryRunner(TOOL_ROOT, verbose=not args.quiet)
    runner.run_batch_file(args.input_file, args.output)


if __name__ == "__main__":
    main()
