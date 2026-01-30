"""Progress reporting component for video frame stitcher."""

from typing import Optional


class ProgressReporter:
    """Reports progress information during video processing."""
    
    def __init__(self):
        """Initialize the progress reporter."""
        self._extraction_frames = {}  # Track frames extracted per camera
        self._stitching_count = 0
    
    def start_extraction(self, camera_id: str, total_segments: int) -> None:
        """
        Report start of extraction phase.
        
        Args:
            camera_id: Camera identifier (cam0 or cam1)
            total_segments: Total number of video segments to process
        """
        print(f"\n{'='*60}")
        print(f"Starting frame extraction for {camera_id}")
        print(f"Total segments to process: {total_segments}")
        print(f"{'='*60}")
        self._extraction_frames[camera_id] = 0
    
    def update_extraction(self, camera_id: str, segment_number: int, frames_extracted: int) -> None:
        """
        Update extraction progress.
        
        Args:
            camera_id: Camera identifier (cam0 or cam1)
            segment_number: Current segment number being processed
            frames_extracted: Number of frames extracted from this segment
        """
        self._extraction_frames[camera_id] = self._extraction_frames.get(camera_id, 0) + frames_extracted
        print(f"  [{camera_id}] Segment {segment_number}: {frames_extracted} frames extracted "
              f"(Total: {self._extraction_frames[camera_id]})")
    
    def complete_extraction(self, camera_id: str, total_frames: int) -> None:
        """
        Report completion of extraction phase.
        
        Args:
            camera_id: Camera identifier (cam0 or cam1)
            total_frames: Total number of frames extracted
        """
        print(f"\n{'-'*60}")
        print(f"Extraction complete for {camera_id}")
        print(f"Total frames extracted: {total_frames}")
        print(f"{'-'*60}\n")
    
    def start_stitching(self, total_pairs: int) -> None:
        """
        Report start of stitching phase.
        
        Args:
            total_pairs: Total number of frame pairs to stitch
        """
        print(f"\n{'='*60}")
        print(f"Starting frame stitching")
        print(f"Total frame pairs to stitch: {total_pairs}")
        print(f"{'='*60}")
        self._stitching_count = 0
    
    def update_stitching(self, frames_stitched: int, total_pairs: int) -> None:
        """
        Update stitching progress.
        
        Args:
            frames_stitched: Number of frames stitched so far
            total_pairs: Total number of frame pairs to stitch
        """
        self._stitching_count = frames_stitched
        percentage = (frames_stitched / total_pairs * 100) if total_pairs > 0 else 0
        print(f"  Progress: {frames_stitched}/{total_pairs} frames stitched ({percentage:.1f}%)")
    
    def complete_stitching(self, total_stitched: int) -> None:
        """
        Report completion of stitching phase.
        
        Args:
            total_stitched: Total number of frames stitched
        """
        print(f"\n{'-'*60}")
        print(f"Stitching complete")
        print(f"Total frames stitched: {total_stitched}")
        print(f"{'-'*60}\n")
    
    def report_warning(self, message: str) -> None:
        """
        Report a warning message.
        
        Args:
            message: Warning message to display
        """
        print(f"WARNING: {message}")
    
    def report_error(self, message: str) -> None:
        """
        Report an error message.
        
        Args:
            message: Error message to display
        """
        print(f"ERROR: {message}")
    
    def report_frame_count_validation(self, cam0_total: int, cam1_total: int, 
                                     difference_percent: float, absolute_diff: int, 
                                     threshold: float) -> None:
        """
        Report frame count validation results with detailed information.
        
        Args:
            cam0_total: Total frame count for cam0
            cam1_total: Total frame count for cam1
            difference_percent: Percentage difference between frame counts
            absolute_diff: Absolute difference in frame counts
            threshold: Configured threshold percentage
        """
        print(f"\n{'='*60}")
        print(f"WARNING: Frame count difference detected!")
        print(f"{'='*60}")
        print(f"  cam0 total frames: {cam0_total:,}")
        print(f"  cam1 total frames: {cam1_total:,}")
        print(f"  Difference: {absolute_diff:,} frames ({difference_percent:.2f}%)")
        print(f"  Threshold: {threshold:.2f}%")
        print(f"\nThis may indicate synchronization issues between cameras.")
        print(f"{'='*60}\n")
    
    def prompt_user_continue(self, message: str = "Continue with frame extraction? (y/n): ") -> bool:
        """
        Prompt user for yes/no confirmation.
        
        Args:
            message: Prompt message to display
            
        Returns:
            True if user confirms (y/Y), False otherwise (n/N or any other input)
        """
        try:
            response = input(message).strip().lower()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            return False
    
    def get_extraction_count(self, camera_id: str) -> int:
        """
        Get the current extraction count for a camera.
        
        Args:
            camera_id: Camera identifier (cam0 or cam1)
            
        Returns:
            Number of frames extracted for the camera
        """
        return self._extraction_frames.get(camera_id, 0)
    
    def get_stitching_count(self) -> int:
        """
        Get the current stitching count.
        
        Returns:
            Number of frames stitched
        """
        return self._stitching_count
