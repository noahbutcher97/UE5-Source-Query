# Constants for UE5 Source Query

# Chunking defaults
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_SEMANTIC_CHUNKING = True

# Model defaults
DEFAULT_EMBED_MODEL = "microsoft/unixcoder-base"

# UE5 Defaults
UE5_ENTITY_PREFIXES = ('F', 'U', 'A', 'I', 'E')

# Search defaults
DEFAULT_TOP_K = 5

# Deployment & Update Rules
# Files to ignore during updates/installs (e.g. caches, git repo metadata)
DEFAULT_EXCLUDES = [
    ".venv", ".git", "__pycache__", "*.pyc", "*.pyo", "*.pyd", 
    ".pytest_cache", ".coverage", "*.log", ".DS_Store", "Thumbs.db"
]

# Files specific to the Dev Repo that should NOT be pushed to deployments
DEPLOYMENT_EXCLUDES = [
    "ue5_query/research",
    "ue5_query/research/**",
    "docs/_archive",
    "docs/_archive/**",
    "ue5_query/indexing/BuildSourceIndex.ps1",
    "ue5_query/indexing/BuildSourceIndexAdmin.bat",
    "tests/DEPLOYMENT_TEST_RESULTS.md",
    "tools/setup-git-lfs.bat",
    "CLAUDE.md",
    "GEMINI.md",
]
