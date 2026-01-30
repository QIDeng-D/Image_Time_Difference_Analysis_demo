"""Frame extraction components for Video Frame Stitcher."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable, Optional
import cv2
import numpy as np
import logging
from PIL import Image

from src.error_handling import (
    VideoFileError, FrameExtractionError, OutputDirectoryError,
    log_error, log_warning, validate_output_directory
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFrame:
    """Metadata for an extracted frame.
    
    Attributes:
        global_frame_number: Continuous frame number across all video segments
        camera_id: Camera identifier ('cam0' or 'cam1')
        file_path: Path to the extracted frame image file
    """
    global_frame_number: int
    camera_id: str
    file_path: Path


class FrameExtractor:
    """Extracts frames from video segments at specified intervals with global frame numbering.
    
    This class processes video segments sequentially, maintaining continuous frame numbering
    across all segments. Frames are extracted at positions determined by the sampling interval
    (e.g., frame 1, 101, 201, ... for interval 100).
    
    Attributes:
        sampling_interval: Number of frames between each extracted frame
        output_format: Image format for saved frames ('png' or 'jpg')
    """
    
    def __init__(self, sampling_interval: int, output_format: str, 
                 enable_overlay: bool = True, overlay_font_size: int = 32, 
                 overlay_position: str = "top-left"):
        """Initialize the FrameExtractor.
        
        Args:
            sampling_interval: Number of frames between each extracted frame (must be >= 1)
            output_format: Image format for saved frames ('png', 'jpg', or 'jpeg')
            enable_overlay: Enable frame number overlay on images
            overlay_font_size: Font size for frame number overlay text
            overlay_position: Position of overlay ('top-left', 'top-right', 'bottom-left', 'bottom-right')
            
        Raises:
            ValueError: If sampling_interval < 1 or output_format is invalid
        """
        if sampling_interval < 1:
            raise ValueError("sampling_interval must be >= 1")
        
        # Normalize output format
        normalized_format = output_format.lower()
        if normalized_format not in ['png', 'jpg', 'jpeg']:
            raise ValueError("output_format must be 'png', 'jpg', or 'jpeg'")
        
        self.sampling_interval = sampling_interval
        self.output_format = normalized_format
        self.enable_overlay = enable_overlay
        self.overlay_font_size = overlay_font_size
        self.overlay_position = overlay_position
    
    def _open_video(self, video_path: Path):
        """Open a video file and return the capture object.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            cv2.VideoCapture object or None if failed to open
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Unable to open video file: {video_path}")
                return None
            return cap
        except Exception as e:
            logger.error(f"Error opening video {video_path}: {e}")
            return None
    
    def should_extract_frame(self, global_frame_number: int) -> bool:
        """Determine if a frame at given global number should be extracted.
        
        Frames are extracted at positions: 1, 1+N, 1+2N, 1+3N, ...
        where N is the sampling interval.
        
        Args:
            global_frame_number: The global frame number (1-indexed)
            
        Returns:
            True if the frame should be extracted, False otherwise
        """
        if global_frame_number < 1:
            return False
        
        # Extract frame if it's at position 1, 1+N, 1+2N, etc.
        # This is equivalent to: (global_frame_number - 1) % sampling_interval == 0
        return (global_frame_number - 1) % self.sampling_interval == 0
    
    def add_frame_number_overlay(self, frame: np.ndarray, frame_number: int) -> np.ndarray:
        """Add frame number overlay to the frame image.
        
        Adds a text overlay showing the global frame number in the format "Frame: XXXXX".
        Uses white text with black outline for maximum visibility on any background.
        
        Args:
            frame: Input frame as numpy array (BGR format)
            frame_number: Global frame number to display
            
        Returns:
            Frame with overlay applied (new array, original is not modified)
        """
        if not self.enable_overlay:
            return frame
        
        # Create a copy to avoid modifying the original
        frame_with_overlay = frame.copy()
        
        # Format the text
        text = f"Frame: {frame_number:05d}"
        
        # Font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.overlay_font_size / 32.0  # Scale relative to default size 32
        thickness = max(1, int(font_scale * 2))
        outline_thickness = thickness + 2
        
        # Get text size for positioning
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Calculate position based on configuration
        height, width = frame_with_overlay.shape[:2]
        margin = 10
        
        if self.overlay_position == "top-left":
            x = margin
            y = text_height + margin
        elif self.overlay_position == "top-right":
            x = width - text_width - margin
            y = text_height + margin
        elif self.overlay_position == "bottom-left":
            x = margin
            y = height - margin
        elif self.overlay_position == "bottom-right":
            x = width - text_width - margin
            y = height - margin
        else:
            # Default to top-left
            x = margin
            y = text_height + margin
        
        # Draw black outline first (for contrast)
        cv2.putText(frame_with_overlay, text, (x, y), font, font_scale, 
                   (0, 0, 0), outline_thickness, cv2.LINE_AA)
        
        # Draw white text on top
        cv2.putText(frame_with_overlay, text, (x, y), font, font_scale, 
                   (255, 255, 255), thickness, cv2.LINE_AA)
        
        return frame_with_overlay
    
    def save_frame(self, frame: np.ndarray, global_frame_number: int, 
                   output_dir: Path, camera_id: str) -> Path:
        """Save a frame with proper naming convention.
        
        Saves the frame to the output directory with a filename
        following the pattern: frame_XXXX.{ext} where XXXX is the zero-padded
        global frame number. Applies frame number overlay if enabled.
        
        Args:
            frame: The frame image as a numpy array
            global_frame_number: The global frame number for filename
            output_dir: Output directory for extracted frames (already includes camera subdirectory)
            camera_id: Camera identifier (for logging purposes)
            
        Returns:
            Path to the saved frame file
            
        Raises:
            ValueError: If frame is None or empty
            IOError: If the frame cannot be saved
        """
        if frame is None or frame.size == 0:
            raise ValueError("Frame is None or empty")
        
        # Apply frame number overlay if enabled
        frame_to_save = self.add_frame_number_overlay(frame, global_frame_number)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Format filename with zero-padding (minimum 4 digits)
        filename = f"frame_{global_frame_number:04d}.{self.output_format}"
        file_path = output_dir / filename
        
        # Save the frame
        try:
            success = cv2.imwrite(str(file_path), frame_to_save)
            if not success:
                raise IOError(f"cv2.imwrite returned False for {file_path}")
        except Exception as e:
            raise IOError(f"Failed to save frame to {file_path}: {str(e)}")
        
        return file_path
    
    def extract_frames(self, video_segments: List['VideoSegment'], output_dir: Path,
                      camera_id: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ExtractedFrame]:
        """Extract frames from video segments maintaining global frame numbering.
        
        Processes video segments sequentially, maintaining continuous frame numbering
        across all segments. Extracts frames at positions determined by the sampling
        interval.
        
        Args:
            video_segments: List of video segments sorted by segment number
            output_dir: Directory to save extracted frames
            camera_id: Camera identifier for subdirectory organization
            progress_callback: Optional function to report progress (frames_extracted, total_frames)
            
        Returns:
            List of ExtractedFrame metadata for all extracted frames
            
        Raises:
            ValueError: If video_segments is empty or output_dir is invalid
            OutputDirectoryError: If output directory cannot be created or accessed
        """
        if not video_segments:
            raise ValueError("video_segments list is empty")
        
        if not output_dir:
            raise ValueError("output_dir must be specified")
        
        # Validate output directory
        try:
            validate_output_directory(output_dir)
        except OutputDirectoryError as e:
            log_error(e, f"Frame extraction for {camera_id}")
            raise
        
        extracted_frames = []
        global_frame_number = 0
        total_frames = sum(seg.frame_count for seg in video_segments)
        
        # Process each video segment in order
        for segment in video_segments:
            try:
                # Open the video file
                cap = cv2.VideoCapture(str(segment.file_path))
                if not cap.isOpened():
                    # Log error and skip this segment
                    error = VideoFileError(
                        segment.file_path,
                        "open",
                        "Video file cannot be opened or is corrupted"
                    )
                    log_error(error, f"Segment {segment.segment_number}")
                    global_frame_number += segment.frame_count
                    continue
                
                # Process each frame in the segment
                local_frame_number = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    local_frame_number += 1
                    global_frame_number += 1
                    
                    # Check if this frame should be extracted
                    if self.should_extract_frame(global_frame_number):
                        try:
                            # Save the frame
                            file_path = self.save_frame(frame, global_frame_number, 
                                                       output_dir, camera_id)
                            
                            # Create metadata
                            extracted_frame = ExtractedFrame(
                                global_frame_number=global_frame_number,
                                camera_id=camera_id,
                                file_path=file_path
                            )
                            extracted_frames.append(extracted_frame)
                            
                            # Report progress if callback provided
                            if progress_callback:
                                progress_callback(len(extracted_frames), total_frames)
                        
                        except Exception as e:
                            # Log error and continue with next frame
                            error = FrameExtractionError(
                                global_frame_number,
                                segment.file_path,
                                str(e)
                            )
                            log_error(error)
                            continue
                
                # Release the video capture
                cap.release()
            
            except Exception as e:
                # Log error and skip this segment
                error = VideoFileError(
                    segment.file_path,
                    "process",
                    str(e)
                )
                log_error(error, f"Segment {segment.segment_number}")
                global_frame_number += segment.frame_count
                continue
        
        return extracted_frames
