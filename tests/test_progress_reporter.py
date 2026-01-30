"""Unit and property-based tests for progress reporting components."""

import pytest
from pathlib import Path
import tempfile
import shutil
import cv2
import numpy as np
from io import StringIO
import sys
from hypothesis import given, strategies as st, settings
from src.progress_reporter import ProgressReporter
from src.frame_extraction import FrameExtractor, ExtractedFrame
from src.frame_stitching import FrameStitcher
from src.video_discovery import VideoSegment


class TestProgressReporter:
    """Test suite for ProgressReporter class."""
    
    def test_progress_reporter_init(self):
        """Test creating a ProgressReporter instance."""
        reporter = ProgressReporter()
        
        assert reporter is not None
        assert reporter.get_extraction_count('cam0') == 0
        assert reporter.get_extraction_count('cam1') == 0
        assert reporter.get_stitching_count() == 0
    
    def test_start_extraction_displays_info(self, capsys):
        """Test that start_extraction displays correct information."""
        reporter = ProgressReporter()
        
        reporter.start_extraction('cam0', 5)
        
        captured = capsys.readouterr()
        assert 'Starting frame extraction for cam0' in captured.out
        assert 'Total segments to process: 5' in captured.out
    
    def test_update_extraction_increments_counter(self, capsys):
        """Test that update_extraction increments the frame counter."""
        reporter = ProgressReporter()
        
        reporter.start_extraction('cam0', 3)
        reporter.update_extraction('cam0', 1, 10)
        
        assert reporter.get_extraction_count('cam0') == 10
        
        reporter.update_extraction('cam0', 2, 15)
        
        assert reporter.get_extraction_count('cam0') == 25
        
        captured = capsys.readouterr()
        assert 'Segment 1: 10 frames extracted' in captured.out
        assert 'Segment 2: 15 frames extracted' in captured.out
        assert 'Total: 25' in captured.out
    
    def test_complete_extraction_displays_total(self, capsys):
        """Test that complete_extraction displays the total count."""
        reporter = ProgressReporter()
        
        reporter.start_extraction('cam0', 2)
        reporter.update_extraction('cam0', 1, 10)
        reporter.update_extraction('cam0', 2, 5)
        reporter.complete_extraction('cam0', 15)
        
        captured = capsys.readouterr()
        assert 'Extraction complete for cam0' in captured.out
        assert 'Total frames extracted: 15' in captured.out
    
    def test_start_stitching_displays_info(self, capsys):
        """Test that start_stitching displays correct information."""
        reporter = ProgressReporter()
        
        reporter.start_stitching(20)
        
        captured = capsys.readouterr()
        assert 'Starting frame stitching' in captured.out
        assert 'Total frame pairs to stitch: 20' in captured.out
    
    def test_update_stitching_increments_counter(self, capsys):
        """Test that update_stitching updates the counter."""
        reporter = ProgressReporter()
        
        reporter.start_stitching(10)
        reporter.update_stitching(5, 10)
        
        assert reporter.get_stitching_count() == 5
        
        captured = capsys.readouterr()
        assert 'Progress: 5/10 frames stitched' in captured.out
        assert '50.0%' in captured.out
    
    def test_complete_stitching_displays_total(self, capsys):
        """Test that complete_stitching displays the total count."""
        reporter = ProgressReporter()
        
        reporter.start_stitching(10)
        reporter.update_stitching(10, 10)
        reporter.complete_stitching(10)
        
        captured = capsys.readouterr()
        assert 'Stitching complete' in captured.out
        assert 'Total frames stitched: 10' in captured.out
    
    def test_report_warning_displays_message(self, capsys):
        """Test that report_warning displays warning message."""
        reporter = ProgressReporter()
        
        reporter.report_warning('Missing frame pair at frame 100')
        
        captured = capsys.readouterr()
        assert 'WARNING: Missing frame pair at frame 100' in captured.out
    
    def test_report_error_displays_message(self, capsys):
        """Test that report_error displays error message."""
        reporter = ProgressReporter()
        
        reporter.report_error('Failed to open video file')
        
        captured = capsys.readouterr()
        assert 'ERROR: Failed to open video file' in captured.out
    
    def test_multiple_cameras_tracked_separately(self):
        """Test that extraction counts are tracked separately for each camera."""
        reporter = ProgressReporter()
        
        reporter.start_extraction('cam0', 2)
        reporter.update_extraction('cam0', 1, 10)
        
        reporter.start_extraction('cam1', 2)
        reporter.update_extraction('cam1', 1, 15)
        
        assert reporter.get_extraction_count('cam0') == 10
        assert reporter.get_extraction_count('cam1') == 15
    
    def test_stitching_percentage_calculation(self, capsys):
        """Test that stitching percentage is calculated correctly."""
        reporter = ProgressReporter()
        
        reporter.start_stitching(100)
        reporter.update_stitching(25, 100)
        
        captured = capsys.readouterr()
        assert '25.0%' in captured.out
        
        reporter.update_stitching(50, 100)
        
        captured = capsys.readouterr()
        assert '50.0%' in captured.out
    
    def test_stitching_with_zero_pairs(self, capsys):
        """Test that stitching handles zero pairs gracefully."""
        reporter = ProgressReporter()
        
        reporter.start_stitching(0)
        reporter.update_stitching(0, 0)
        
        captured = capsys.readouterr()
        # Should not crash, percentage should be 0
        assert 'Progress: 0/0' in captured.out


# Property-Based Tests

class TestProgressReporterProperties:
    """Property-based tests for progress reporting."""
    
    def create_test_video(self, path: Path, frame_count: int, width: int = 320, height: int = 240):
        """Create a simple test video with specified frame count."""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
        
        for i in range(frame_count):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
            out.write(frame)
        
        out.release()
    
    @settings(deadline=None, max_examples=50)
    @given(
        segment_frame_counts=st.lists(
            st.integers(min_value=1, max_value=50),
            min_size=1,
            max_size=3
        ),
        sampling_interval=st.integers(min_value=1, max_value=20)
    )
    def test_property_progress_counter_accuracy(self, segment_frame_counts, sampling_interval):
        """Property 12: Progress Counter Accuracy
        
        **Validates: Requirements 6.3, 6.4**
        
        For any execution of the system, the reported count of frames extracted 
        should equal the actual number of frame files created, and the reported 
        count of frames stitched should equal the actual number of stitched files created.
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create progress reporter
            reporter = ProgressReporter()
            
            # Create frame extractor
            extractor = FrameExtractor(sampling_interval=sampling_interval, output_format='png')
            
            # Create video segments for cam0
            cam0_segments = []
            for idx, frame_count in enumerate(segment_frame_counts):
                video_path = temp_dir / f'cam0_segment_{idx}.mp4'
                self.create_test_video(video_path, frame_count)
                
                segment = VideoSegment(
                    camera_id='cam0',
                    segment_number=idx,
                    file_path=video_path,
                    frame_count=frame_count
                )
                cam0_segments.append(segment)
            
            # Create video segments for cam1 (same structure)
            cam1_segments = []
            for idx, frame_count in enumerate(segment_frame_counts):
                video_path = temp_dir / f'cam1_segment_{idx}.mp4'
                self.create_test_video(video_path, frame_count)
                
                segment = VideoSegment(
                    camera_id='cam1',
                    segment_number=idx,
                    file_path=video_path,
                    frame_count=frame_count
                )
                cam1_segments.append(segment)
            
            # Extract frames for cam0
            output_dir = temp_dir / 'extracted'
            reporter.start_extraction('cam0', len(cam0_segments))
            
            # Extract all frames at once to maintain global frame numbering
            cam0_frames = extractor.extract_frames(cam0_segments, output_dir, 'cam0')
            
            # For progress reporting, we just report the total extracted
            # (In a real application, we'd report per-segment, but for this test we simplify)
            reporter.update_extraction('cam0', 0, len(cam0_frames))
            reporter.complete_extraction('cam0', len(cam0_frames))
            
            # Extract frames for cam1
            reporter.start_extraction('cam1', len(cam1_segments))
            
            # Extract all frames at once to maintain global frame numbering
            cam1_frames = extractor.extract_frames(cam1_segments, output_dir, 'cam1')
            
            # For progress reporting, we just report the total extracted
            reporter.update_extraction('cam1', 0, len(cam1_frames))
            reporter.complete_extraction('cam1', len(cam1_frames))
            
            # Verify extraction counts match actual files
            cam0_reported = reporter.get_extraction_count('cam0')
            cam0_actual = len(list((output_dir / 'cam0').glob('*.png'))) if (output_dir / 'cam0').exists() else 0
            
            assert cam0_reported == cam0_actual, \
                f"cam0: Reported {cam0_reported} frames extracted, but {cam0_actual} files exist"
            
            assert cam0_reported == len(cam0_frames), \
                f"cam0: Reported {cam0_reported} frames, but extracted {len(cam0_frames)} frames"
            
            cam1_reported = reporter.get_extraction_count('cam1')
            cam1_actual = len(list((output_dir / 'cam1').glob('*.png'))) if (output_dir / 'cam1').exists() else 0
            
            assert cam1_reported == cam1_actual, \
                f"cam1: Reported {cam1_reported} frames extracted, but {cam1_actual} files exist"
            
            assert cam1_reported == len(cam1_frames), \
                f"cam1: Reported {cam1_reported} frames, but extracted {len(cam1_frames)} frames"
            
            # Now test stitching
            stitcher = FrameStitcher(output_format='png')
            
            # Find matching frame pairs
            cam0_dict = {f.global_frame_number: f for f in cam0_frames}
            cam1_dict = {f.global_frame_number: f for f in cam1_frames}
            matching_numbers = set(cam0_dict.keys()) & set(cam1_dict.keys())
            
            reporter.start_stitching(len(matching_numbers))
            
            # Stitch frames
            stitched_output = temp_dir / 'stitched'
            stitched_output.mkdir(exist_ok=True)
            
            stitched_count = 0
            for frame_num in sorted(matching_numbers):
                cam0_frame = cam0_dict[frame_num]
                cam1_frame = cam1_dict[frame_num]
                
                output_path = stitched_output / f'frame_{frame_num:04d}.png'
                stitcher.stitch_pair(cam0_frame.file_path, cam1_frame.file_path, output_path)
                
                stitched_count += 1
                reporter.update_stitching(stitched_count, len(matching_numbers))
            
            reporter.complete_stitching(stitched_count)
            
            # Verify stitching counts match actual files
            stitched_reported = reporter.get_stitching_count()
            stitched_actual = len(list(stitched_output.glob('*.png')))
            
            assert stitched_reported == stitched_actual, \
                f"Reported {stitched_reported} frames stitched, but {stitched_actual} files exist"
            
            assert stitched_reported == len(matching_numbers), \
                f"Reported {stitched_reported} frames stitched, but expected {len(matching_numbers)}"
            
            # Verify all reported counts are non-negative
            assert cam0_reported >= 0, "cam0 extraction count should be non-negative"
            assert cam1_reported >= 0, "cam1 extraction count should be non-negative"
            assert stitched_reported >= 0, "Stitching count should be non-negative"
        
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
