"""Video discovery and segment management for Video Frame Stitcher."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import re
import cv2
import logging

from src.error_handling import (
    InputDirectoryError, VideoFileError,
    log_error, log_warning, validate_input_directory
)

logger = logging.getLogger(__name__)


@dataclass
class VideoSegment:
    """Metadata for a single video segment.
    
    Attributes:
        camera_id: Camera identifier ('cam0' or 'cam1')
        segment_number: Sequential segment number for ordering
        file_path: Path to the video file
        frame_count: Total number of frames in this video segment
    """
    camera_id: str
    segment_number: int
    file_path: Path
    frame_count: int
    
    def __lt__(self, other):
        """Enable sorting by segment number.
        
        Args:
            other: Another VideoSegment instance to compare with
            
        Returns:
            True if this segment's number is less than the other's
            
        Raises:
            TypeError: If other is not a VideoSegment instance
        """
        if not isinstance(other, VideoSegment):
            return NotImplemented
        return self.segment_number < other.segment_number


class VideoDiscovery:
    """Discovers and organizes video files by camera and segment number.
    
    This class scans a directory for video files matching specified patterns,
    extracts segment numbers, retrieves frame counts, and validates segment pairing
    between cameras.
    """
    
    @staticmethod
    def discover_videos(input_dir: Path, cam0_pattern: str, cam1_pattern: str) -> Dict[str, List[VideoSegment]]:
        """Discover video files and return them grouped by camera.
        
        Scans the input directory for video files matching the camera patterns,
        extracts segment numbers from filenames, retrieves frame counts, and
        organizes them by camera ID.
        
        Args:
            input_dir: Directory to scan for video files
            cam0_pattern: Glob pattern for cam0 videos (e.g., "stereo_cam0_sbs_*.mp4")
            cam1_pattern: Glob pattern for cam1 videos (e.g., "stereo_cam1_sbs_*.mp4")
            
        Returns:
            Dictionary with camera IDs as keys and sorted lists of VideoSegments as values.
            Example: {'cam0': [VideoSegment, ...], 'cam1': [VideoSegment, ...]}
            
        Raises:
            InputDirectoryError: If input_dir does not exist or is not accessible
        """
        # Validate input directory
        try:
            validate_input_directory(input_dir)
        except InputDirectoryError as e:
            log_error(e, "Video discovery")
            raise
        
        result = {'cam0': [], 'cam1': []}
        
        # Process cam0 videos
        for video_path in input_dir.glob(cam0_pattern):
            if video_path.is_file():
                segment_number = VideoDiscovery._extract_segment_number(video_path.name)
                if segment_number is not None:
                    frame_count = VideoDiscovery.get_frame_count(video_path)
                    if frame_count > 0:
                        segment = VideoSegment(
                            camera_id='cam0',
                            segment_number=segment_number,
                            file_path=video_path,
                            frame_count=frame_count
                        )
                        result['cam0'].append(segment)
                    else:
                        log_warning(
                            f"Skipping video file with 0 frames or unable to read frame count",
                            video_path
                        )
        
        # Process cam1 videos
        for video_path in input_dir.glob(cam1_pattern):
            if video_path.is_file():
                segment_number = VideoDiscovery._extract_segment_number(video_path.name)
                if segment_number is not None:
                    frame_count = VideoDiscovery.get_frame_count(video_path)
                    if frame_count > 0:
                        segment = VideoSegment(
                            camera_id='cam1',
                            segment_number=segment_number,
                            file_path=video_path,
                            frame_count=frame_count
                        )
                        result['cam1'].append(segment)
                    else:
                        log_warning(
                            f"Skipping video file with 0 frames or unable to read frame count",
                            video_path
                        )
        
        # Sort segments by segment number
        result['cam0'].sort()
        result['cam1'].sort()
        
        return result
    
    @staticmethod
    def _extract_segment_number(filename: str) -> int:
        """Extract segment number from filename.
        
        Looks for numeric patterns in the filename. Assumes the segment number
        is the last sequence of digits before the file extension.
        
        Args:
            filename: Name of the video file
            
        Returns:
            Segment number as integer, or None if no number found
        """
        # Remove file extension
        name_without_ext = Path(filename).stem
        
        # Find all sequences of digits
        numbers = re.findall(r'\d+', name_without_ext)
        
        if numbers:
            # Return the last number found (typically the segment number)
            return int(numbers[-1])
        
        return None
    
    @staticmethod
    def get_frame_count(video_path: Path) -> int:
        """Get total frame count from a video file.
        
        Uses OpenCV to open the video file and retrieve the frame count
        from the video metadata.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Total number of frames in the video, or 0 if the video cannot be opened
            or frame count cannot be determined
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                log_warning(f"Unable to open video file", video_path)
                return 0
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            return frame_count if frame_count > 0 else 0
        except Exception as e:
            log_warning(f"Error reading frame count: {e}", video_path)
            return 0
    
    @staticmethod
    def validate_segment_pairing(cam0_segments: List[VideoSegment], cam1_segments: List[VideoSegment]) -> List[str]:
        """Check for missing segment pairs and return list of warnings.
        
        Compares segment numbers between cam0 and cam1 to identify segments
        that exist for one camera but not the other.
        
        Args:
            cam0_segments: List of VideoSegments for cam0
            cam1_segments: List of VideoSegments for cam1
            
        Returns:
            List of warning messages for missing segment pairs.
            Empty list if all segments are properly paired.
        """
        warnings = []
        
        # Create sets of segment numbers for each camera
        cam0_numbers = {seg.segment_number for seg in cam0_segments}
        cam1_numbers = {seg.segment_number for seg in cam1_segments}
        
        # Find segments in cam0 but not in cam1
        missing_in_cam1 = cam0_numbers - cam1_numbers
        for seg_num in sorted(missing_in_cam1):
            warnings.append(f"Segment {seg_num} exists for cam0 but not for cam1")
        
        # Find segments in cam1 but not in cam0
        missing_in_cam0 = cam1_numbers - cam0_numbers
        for seg_num in sorted(missing_in_cam0):
            warnings.append(f"Segment {seg_num} exists for cam1 but not for cam0")
        
        return warnings
    
    @staticmethod
    def calculate_total_frame_counts(segments: Dict[str, List[VideoSegment]]) -> Dict[str, int]:
        """Calculate total frame count for each camera by summing all segments.
        
        Args:
            segments: Dictionary with camera IDs as keys and lists of VideoSegments as values
            
        Returns:
            Dictionary with camera IDs as keys and total frame counts as values.
            Example: {'cam0': 15000, 'cam1': 14200}
        """
        result = {}
        
        for camera_id, segment_list in segments.items():
            total_frames = sum(seg.frame_count for seg in segment_list)
            result[camera_id] = total_frames
        
        return result
    
    @staticmethod
    def validate_frame_count_difference(cam0_total: int, cam1_total: int, threshold_percent: float) -> tuple:
        """Check if frame count difference exceeds threshold.
        
        Calculates the absolute difference and percentage difference between
        cam0 and cam1 total frame counts, then compares against the threshold.
        
        Args:
            cam0_total: Total frame count for cam0
            cam1_total: Total frame count for cam1
            threshold_percent: Maximum allowed difference percentage (0-100)
            
        Returns:
            Tuple of (exceeds_threshold: bool, difference_percent: float, absolute_difference: int)
            
        Example:
            >>> validate_frame_count_difference(15000, 14200, 5.0)
            (True, 5.33, 800)  # Exceeds 5% threshold
        """
        # Handle edge case where both are zero
        if cam0_total == 0 and cam1_total == 0:
            return (False, 0.0, 0)
        
        # Calculate absolute difference
        absolute_diff = abs(cam0_total - cam1_total)
        
        # Calculate percentage difference relative to the larger value
        max_frames = max(cam0_total, cam1_total)
        if max_frames == 0:
            difference_percent = 0.0
        else:
            difference_percent = (absolute_diff / max_frames) * 100.0
        
        # Check if exceeds threshold
        exceeds_threshold = difference_percent > threshold_percent
        
        return (exceeds_threshold, difference_percent, absolute_diff)
