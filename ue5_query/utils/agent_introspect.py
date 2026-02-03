import json
import os
import sys
from pathlib import Path

# Fix path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ue5_query.utils.config_manager import ConfigManager
from ue5_query.utils.source_manager import SourceManager
from ue5_query.indexing.build_embeddings import OUT_VECTORS, OUT_META

def get_agent_config_data():
    root = Path(__file__).resolve().parent.parent.parent
    config = ConfigManager(root)
    source_mgr = SourceManager(root / "ue5_query" / "indexing")
    
    # Calculate index stats
    index_exists = OUT_VECTORS.exists() and OUT_META.exists()
    index_size = 0
    chunk_count = 0
    
    if index_exists:
        try:
            index_size = (OUT_VECTORS.stat().st_size + OUT_META.stat().st_size) / (1024*1024)
            data = json.loads(OUT_META.read_text(encoding='utf-8'))
            chunk_count = len(data.get('items', []))
        except:
            pass

    return {
        "environment": {
            "root": str(root),
            "platform": sys.platform,
            "python_version": sys.version.split()[0]
        },
        "ue5": {
            "engine_root": config.get("UE_ENGINE_ROOT"),
            "engine_dirs_count": len(source_mgr.get_engine_dirs()),
            "project_dirs_count": len(source_mgr.get_project_dirs())
        },
        "index": {
            "exists": index_exists,
            "size_mb": round(index_size, 2),
            "chunk_count": chunk_count,
            "location": str(OUT_VECTORS.parent)
        },
        "models": {
            "embedding": config.get("EMBED_MODEL"),
            "llm": config.get("ANTHROPIC_MODEL")
        }
    }

def get_agent_config():
    print(json.dumps(get_agent_config_data(), indent=2))

if __name__ == "__main__":
    get_agent_config()
