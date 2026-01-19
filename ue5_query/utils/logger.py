import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Setup a standardized logger with console and optional file output.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional path to log file. If provided, logs will be written there.
        level: Logging level (default: logging.INFO)
        
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times if logger is reused
    if logger.handlers:
        return logger

    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (Optional)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024, # 5 MB
            backupCount=3
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

def get_project_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for the project, automatically finding the logs directory.
    """
    # Determine project root (relative to this file in src/utils/logger.py)
    # src/utils/logger.py -> src/utils -> src -> ROOT
    root_dir = Path(__file__).parent.parent.parent
    log_dir = root_dir / "logs"
    
    # Create logs directory if it doesn't exist
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Fallback to temp dir or just console if we can't write
            pass

    log_file = log_dir / "ue5query.log"
    return setup_logger(name, str(log_file))
