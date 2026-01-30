"""Directory management utilities for Video Frame Stitcher."""

from pathlib import Path
from typing import List
import logging

from src.error_handling import OutputDirectoryError

logger = logging.getLogger(__name__)


def create_output_structure(base_dir: Path, subdirs: List[str] = None) -> None:
    """Create output directory structure with optional subdirectories.
    
    Args:
        base_dir: Base output directory path
        subdirs: Optional list of subdirectory names to create
        
    Raises:
        OutputDirectoryError: If directories cannot be created
    """
    try:
        # Create base directory
        base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {base_dir}")
        
        # Create subdirectories if specified
        if subdirs:
            for subdir in subdirs:
                subdir_path = base_dir / subdir
                subdir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created subdirectory: {subdir_path}")
    
    except PermissionError as e:
        raise OutputDirectoryError(
            base_dir,
            "create",
            f"Permission denied: {e}"
        )
    except OSError as e:
        raise OutputDirectoryError(
            base_dir,
            "create",
            f"OS error: {e}"
        )


def ensure_directory_exists(directory: Path) -> None:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
        
    Raises:
        OutputDirectoryError: If directory cannot be created
    """
    if directory.exists():
        if not directory.is_dir():
            raise OutputDirectoryError(
                directory,
                "validate",
                "Path exists but is not a directory"
            )
        return
    
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {directory}")
    except PermissionError as e:
        raise OutputDirectoryError(
            directory,
            "create",
            f"Permission denied: {e}"
        )
    except OSError as e:
        raise OutputDirectoryError(
            directory,
            "create",
            f"OS error: {e}"
        )


def setup_extraction_directories(base_dir: Path) -> dict:
    """Set up directory structure for frame extraction.
    
    Creates the base extraction directory with cam0 and cam1 subdirectories.
    
    Args:
        base_dir: Base directory for extracted frames
        
    Returns:
        Dictionary with paths: {'base': Path, 'cam0': Path, 'cam1': Path}
        
    Raises:
        OutputDirectoryError: If directories cannot be created
    """
    # Create base directory
    ensure_directory_exists(base_dir)
    
    # Create camera subdirectories
    cam0_dir = base_dir / 'cam0'
    cam1_dir = base_dir / 'cam1'
    
    ensure_directory_exists(cam0_dir)
    ensure_directory_exists(cam1_dir)
    
    logger.info(f"Set up extraction directories: {base_dir} (cam0, cam1)")
    
    return {
        'base': base_dir,
        'cam0': cam0_dir,
        'cam1': cam1_dir
    }


def setup_stitching_directory(output_dir: Path) -> Path:
    """Set up directory for stitched output frames.
    
    Args:
        output_dir: Directory for stitched frames
        
    Returns:
        Path to the created directory
        
    Raises:
        OutputDirectoryError: If directory cannot be created
    """
    ensure_directory_exists(output_dir)
    logger.info(f"Set up stitching directory: {output_dir}")
    return output_dir


def validate_directory_writable(directory: Path) -> bool:
    """Check if a directory is writable.
    
    Args:
        directory: Directory path to check
        
    Returns:
        True if directory is writable, False otherwise
    """
    if not directory.exists() or not directory.is_dir():
        return False
    
    # Try to create and delete a test file
    test_file = directory / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
        return True
    except (PermissionError, OSError):
        return False


def get_directory_info(directory: Path) -> dict:
    """Get information about a directory.
    
    Args:
        directory: Directory path to inspect
        
    Returns:
        Dictionary with directory information:
        - exists: bool
        - is_directory: bool
        - is_writable: bool
        - file_count: int (if exists)
    """
    info = {
        'exists': directory.exists(),
        'is_directory': False,
        'is_writable': False,
        'file_count': 0
    }
    
    if info['exists']:
        info['is_directory'] = directory.is_dir()
        
        if info['is_directory']:
            info['is_writable'] = validate_directory_writable(directory)
            
            # Count files (not subdirectories)
            try:
                info['file_count'] = sum(1 for item in directory.iterdir() if item.is_file())
            except (PermissionError, OSError):
                info['file_count'] = -1  # Indicates error counting
    
    return info
