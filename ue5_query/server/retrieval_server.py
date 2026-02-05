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
sys.path.insert(0, str(TOOL_ROOT))

from ue5_query.core.hybrid_query import HybridQueryEngine

# Global state
engine: HybridQueryEngine | None = None
init_error: str | None = None

class SearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            
            # --- Endpoints that work even if Engine failed ---
            
            if parsed.path == "/health":
                if engine:
                    return self._json({
                        "status": "ok", 
                        "model": engine.embed_model_name,
                        "index_chunks": len(engine.meta) if engine.meta else 0
                    })
                else:
                    return self._json({
                        "status": "degraded",
                        "error": init_error,
                        "message": "Engine failed to initialize. Check /config or logs."
                    }, code=503)
            
            elif parsed.path == "/config":
                from ue5_query.utils.agent_introspect import get_agent_config_data
                return self._json(get_agent_config_data())

            elif parsed.path == "/describe":
                from ue5_query.core.hybrid_query import get_tool_schema
                return self._json(get_tool_schema())

            # --- Endpoints requiring Engine ---

            elif parsed.path == "/search":
                if not engine:
                    return self._json({
                        "error": "Engine not ready",
                        "details": init_error
                    }, code=503)

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
    global engine, init_error
    try:
        engine = HybridQueryEngine(TOOL_ROOT)
        print(f"[INFO] Engine ready. Using model: {engine.embed_model_name}")
    except Exception as e:
        init_error = str(e)
        print(f"[WARN] Failed to initialize engine: {e}")
        print(f"[WARN] Server starting in DEGRADED mode. Search will be unavailable.")

    try:
        server = ThreadingHTTPServer((host, port), SearchHandler)
        print(f"[INFO] Ready to accept queries.")
        server.serve_forever()
    except OSError as e:
        print(f"[FATAL] Could not bind to port {port}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopping...")
    finally:
        if 'server' in locals():
            server.server_close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    args = ap.parse_args()
    
    serve(args.host, args.port)

if __name__ == "__main__":
    main()
