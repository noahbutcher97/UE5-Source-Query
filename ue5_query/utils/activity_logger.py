import json
import time
import os
from pathlib import Path
from datetime import datetime

class ActivityLogger:
    """Centralized machine-readable event logging for AI agents"""
    def __init__(self, root_dir: Path):
        self.log_file = root_dir / "logs" / "activity.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_type: str, details: dict):
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except:
            pass # Fail silent, don't block main logic

# Global instance helper
_instance = None
def get_activity_logger():
    global _instance
    if _instance is None:
        # Determine root relative to this file
        root = Path(__file__).resolve().parent.parent.parent
        _instance = ActivityLogger(root)
    return _instance
