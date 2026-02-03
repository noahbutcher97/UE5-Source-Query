import os
from pathlib import Path
from typing import Optional, Dict

class AuthManager:
    """Unified authentication and credential validator"""
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def get_api_key(self) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY")

    def validate_setup(self) -> Dict[str, any]:
        """Verify all required credentials and paths exist"""
        key = self.get_api_key()
        
        status = {
            "auth_ok": False,
            "error": None,
            "provider": "Anthropic"
        }
        
        if not key:
            status["error"] = "ANTHROPIC_API_KEY environment variable not set."
        elif not key.startswith("sk-ant-"):
            status["error"] = "ANTHROPIC_API_KEY format is invalid (missing 'sk-ant-' prefix)."
        else:
            status["auth_ok"] = True
            
        return status

def check_auth(root: Path):
    mgr = AuthManager(root)
    return mgr.validate_setup()
