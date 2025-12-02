# python
# ===== File: retrieval_server.py =====
"""
Search Server for UE5 Source Query.
Wraps HybridQueryEngine in a lightweight HTTP API for persistent caching.
"""
import sys
import json
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add parent to path for imports
TOOL_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TOOL_ROOT / "src"))

from core.hybrid_query import HybridQueryEngine

# Global engine instance
engine: HybridQueryEngine | None = None

class SearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            
            if parsed.path == "/health":
                return self._json({"status": "ok", "model": engine.embed_model_name})
            
            elif parsed.path == "/search":
                qs = parse_qs(parsed.query)
                
                # Parse parameters
                query_text = qs.get("q", [""])[0].strip()
                if not query_text:
                    return self._json({"error": "missing 'q' parameter"}, code=400)
                
                top_k = int(qs.get("top_k", ["5"])[0])
                scope = qs.get("scope", ["engine"])[0] # engine, project, all
                
                # Execute query via the engine
                # dry_run=False, show_reasoning=False (we return structured data)
                results = engine.query(
                    question=query_text,
                    top_k=top_k,
                    scope=scope,
                    dry_run=False,
                    show_reasoning=False
                )
                
                return self._json(results)
                
            else:
                self._json({"error": "not found"}, code=404)
                
        except Exception as e:
            self._json({"error": str(e)}, code=500)

    def log_message(self, format, *args):
        # Suppress default logging to keep console clean
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

def serve(host: str, port: int):
    print(f"[INFO] Search Server starting on http://{host}:{port}")
    print("[INFO] Loading models and index (this may take a few seconds)...")
    
    # Initialize engine (loads heavy resources once)
    global engine
    try:
        engine = HybridQueryEngine(TOOL_ROOT)
        print(f"[INFO] Engine ready. Using model: {engine.embed_model_name}")
    except Exception as e:
        print(f"[FATAL] Failed to initialize engine: {e}")
        sys.exit(1)

    server = ThreadingHTTPServer((host, port), SearchHandler)
    print(f"[INFO] Ready to accept queries.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopping...")
    finally:
        server.server_close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    args = ap.parse_args()
    
    serve(args.host, args.port)

if __name__ == "__main__":
    main()
