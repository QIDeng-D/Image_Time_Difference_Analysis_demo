"""Centralized error handling and validation for Video Frame Stitcher."""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VideoFrameStitcherError(Exception):
    """Base exception for Video Frame Stitcher errors."""
    pass


class InputDirectoryError(VideoFrameStitcherError):
    """Exception raised for input directory errors."""
    
    def __init__(self, directory: Path, reason: str):
        """Initialize InputDirectoryError.
        
        Args:
            directory: The problematic directory path
            reason: Description of the error
        """
        self.directory = directory
        self.reason = reason
        super().__init__(f"Input directory error for '{directory}': {reason}")


class VideoFileError(VideoFrameStitcherError):
    """Exception raised for video file errors."""
    
    def __init__(self, file_path: Path, operation: str, reason: str):
        """Initialize VideoFileError.
        
        Args:
            file_path: The problematic video file path
            operation: The operation that failed (e.g., 'open', 'read')
            reason: Description of the error
        """
        self.file_path = file_path
        self.operation = operation
        self.reason = reason
        super().__init__(f"Failed to {operation} video file '{file_path}': {reason}")


class FrameExtractionError(VideoFrameStitcherError):
    """Exception raised for frame extraction errors."""
    
    def __init__(self, frame_number: int, file_path: Path, reason: str):
        """Initialize FrameExtractionError.
        
        Args:
            frame_number: The frame number that failed to extract
            file_path: The video file being processed
            reason: Description of the error
        """
        self.frame_number = frame_number
        self.file_path = file_path
        self.reason = reason
        super().__init__(
            f"Failed to extract frame {frame_number} from '{file_path}': {reason}"
        )


class OutputDirectoryError(VideoFrameStitcherError):
    """Exception raised for output directory errors."""
    
    def __init__(self, directory: Path, operation: str, reason: str):
        """Initialize OutputDirectoryError.
        
        Args:
            directory: The problematic directory path
            operation: The operation that failed (e.g., 'create', 'write')
            reason: Description of the error
        """
        self.directory = directory
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Failed to {operation} output directory '{directory}': {reason}"
        )


class StitchingError(VideoFrameStitcherError):
    """Exception raised for frame stitching errors."""
    
    def __init__(self, frame_number: int, cam0_path: Optional[Path], 
                 cam1_path: Optional[Path], reason: str):
        """Initialize StitchingError.
        
        Args:
            frame_number: The frame number that failed to stitch
            cam0_path: Path to cam0 frame (if available)
            cam1_path: Path to cam1 frame (if available)
            reason: Description of the error
        """
        self.frame_number = frame_number
        self.cam0_path = cam0_path
        self.cam1_path = cam1_path
        self.reason = reason
        
        files_info = []
        if cam0_path:
            files_info.append(f"cam0: '{cam0_path}'")
        if cam1_path:
            files_info.append(f"cam1: '{cam1_path}'")
        
        files_str = ", ".join(files_info) if files_info else "missing files"
        super().__init__(
            f"Failed to stitch frame {frame_number} ({files_str}): {reason}"
        )


def validate_input_directory(input_dir: Path) -> None:
    """Validate that the input directory exists and is accessible.
    
    Args:
        input_dir: Path to the input directory
        
    Raises:
        InputDirectoryError: If the directory doesn't exist or is not accessible
    """
    if not input_dir.exists():
        raise InputDirectoryError(input_dir, "Directory does not exist")
    
    if not input_dir.is_dir():
        raise InputDirectoryError(input_dir, "Path is not a directory")
    
    # Check if directory is readable
    try:
        list(input_dir.iterdir())
    except PermissionError:
        raise InputDirectoryError(input_dir, "Permission denied - cannot read directory")
    except OSError as e:
        raise InputDirectoryError(input_dir, f"OS error: {e}")


def validate_output_directory(output_dir: Path) -> None:
    """Validate and create output directory if needed.
    
    Args:
        output_dir: Path to the output directory
        
    Raises:
        OutputDirectoryError: If the directory cannot be created or accessed
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise OutputDirectoryError(
            output_dir, "create", "Permission denied - cannot create directory"
        )
    except OSError as e:
        raise OutputDirectoryError(
            output_dir, "create", f"OS error: {e}"
        )
    
    # Verify directory is writable
    if not output_dir.exists():
        raise OutputDirectoryError(
            output_dir, "create", "Directory was not created successfully"
        )
    
    # Test write permissions
    test_file = output_dir / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        raise OutputDirectoryError(
            output_dir, "write", "Permission denied - directory is not writable"
        )
    except OSError as e:
        raise OutputDirectoryError(
            output_dir, "write", f"OS error: {e}"
        )


def log_error(error: Exception, context: str = "") -> None:
    """Log an error with appropriate context.
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
    """
    if isinstance(error, VideoFrameStitcherError):
        # Our custom errors already have detailed messages
        logger.error(f"{context}: {error}" if context else str(error))
    else:
        # Generic errors need more context
        error_type = type(error).__name__
        logger.error(f"{context}: {error_type}: {error}" if context else f"{error_type}: {error}")


def log_warning(message: str, file_path: Optional[Path] = None) -> None:
    """Log a warning message with optional file context.
    
    Args:
        message: Warning message
        file_path: Optional file path related to the warning
    """
    if file_path:
        logger.warning(f"{message} (file: '{file_path}')")
    else:
        logger.warning(message)
