import re
from pathlib import Path
from typing import Tuple, Optional, List

def parse_index_progress(line: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse a line of output from the index build script to determine progress.
    
    Returns:
        (percentage, status_message) or (None, None) if no progress detected.
    """
    line = line.strip()
    
    # Progress stages and their approximate percentage ranges
    
    # Stage 1: Discovery (0-10%)
    if "Discovering" in line or "Finding" in line:
        return 5, "Discovering source files..."
    if "Found" in line and "files" in line:
        return 10, f"Discovered: {line}"

    # Stage 2: Chunking (10-30%)
    if "Chunking" in line or "Processing" in line:
        # Try to extract "Processing files (X/Y)..."
        match = re.search(r'(\d+)/(\d+)', line)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            # Map 0-100% of this stage to 10-30% total
            progress = 10 + (current / total * 20) if total > 0 else 15
            return int(progress), f"Processing files ({current}/{total})..."
        return 20, "Processing files..."

    # Stage 3: Embedding generation (30-90%)
    if "Embedding" in line or "batch" in line.lower():
        # Try to extract "batch X/Y" or percentage
        match = re.search(r'(\d+)/(\d+)', line)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            # Map 0-100% of this stage to 30-90% total
            progress = 30 + (current / total * 60) if total > 0 else 60
            return int(progress), f"Generating embeddings ({current}/{total})..."
        
        match = re.search(r'(\d+(?:\.\d+)?)%', line)
        if match:
            pct = float(match.group(1))
            progress = 30 + (pct * 0.6)
            return int(progress), f"Generating embeddings ({pct:.1f}%)..."
            
        return 60, "Generating embeddings..."

    # Stage 4: Saving (90-100%)
    if "Saving" in line or "Writing" in line:
        return 95, "Saving vector store..."
        
    if "Complete" in line or "SUCCESS" in line or "Done" in line:
        return 100, "Complete!"

    return None, None

def get_rebuild_command(script_dir: Path, force: bool = False, verbose: bool = True) -> List[str]:
    """
    Construct the command to run the rebuild-index script.
    
    Args:
        script_dir: The root directory containing 'tools'
        force: If True, adds --force (full rebuild). If False, defaults to incremental.
        verbose: If True, adds --verbose.
        
    Returns:
        List of command arguments.
    """
    script = script_dir / "tools" / "rebuild-index.bat"
    cmd = [str(script)]
    
    if verbose:
        cmd.append("--verbose")
        
    if force:
        cmd.append("--force")
    else:
        cmd.append("--incremental")
        
    return cmd
