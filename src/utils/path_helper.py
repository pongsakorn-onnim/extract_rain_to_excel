from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_directory_exists(path: Path) -> None:
    """
    Checks if a directory exists, creates it if not.
    """
    if not path.exists():
        logger.debug(f"Creating directory: {path}")
        path.mkdir(parents=True, exist_ok=True)