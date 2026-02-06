"""
Smoke test for FastAPI Server.
Starts server, pings health, and terminates.
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

def test_server():
    print("Starting API Server smoke test...")
    
    # 1. Start Server in background
    root = Path(__file__).resolve().parent.parent
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    
    process = subprocess.Popen(
        [str(python_exe), "-m", "uvicorn", "ue5_query.server.app:app", "--host", "127.0.0.1", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(root)
    )
    
    try:
        # 2. Wait for startup
        print("Waiting for server to initialize...")
        max_retries = 30
        online = False
        
        for i in range(max_retries):
            try:
                resp = requests.get("http://127.0.0.1:8001/health", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✓ Server Online! Status: {data['status']}")
                    online = True
                    break
            except:
                time.sleep(1)
                if i % 5 == 0 and i > 0: 
                    print(f"  Attempt {i}/{max_retries}...")
        
        if not online:
            print("✗ FAILED: Server timed out or failed to start.")
            return False

        # 3. Test Search
        print("Testing search endpoint...")
        search_resp = requests.post(
            "http://127.0.0.1:8001/search", 
            json={"question": "FHitResult", "top_k": 1},
            timeout=10
        )
        
        if search_resp.status_code == 200:
            print("✓ Search Successful!")
            return True
        else:
            print(f"✗ Search Failed: {search_resp.status_code}")
            return False

    finally:
        print("Shutting down server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)