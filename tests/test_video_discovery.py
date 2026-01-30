"""Unit tests for VideoDiscovery class."""

import pytest
from pathlib import Path
import tempfile
import shutil
import cv2
import numpy as np
from hypothesis import given, strategies as st, settings
from src.video_discovery import VideoDiscovery, VideoSegment


class TestVideoDiscovery:
    """Test suite for VideoDiscovery class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup after test
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_video(self):
        """Create a sample video file for testing."""
        def _create_video(path: Path, frame_count: int = 10, width: int = 640, height: int = 480):
            """Create a simple test video with specified frame count."""
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
            
            for i in range(frame_count):
                # Create a simple frame with a different color for each frame
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
                out.write(frame)
            
            out.release()
        
        return _create_video
    
    def test_discover_videos_with_matching_files(self, temp_dir, sample_video):
        """Test discovering videos with files matching both camera patterns."""
        # Create test video files
        cam0_file1 = temp_dir / "stereo_cam0_sbs_0001.mp4"
        cam0_file2 = temp_dir / "stereo_cam0_sbs_0002.mp4"
        cam1_file1 = temp_dir / "stereo_cam1_sbs_0001.mp4"
        cam1_file2 = temp_dir / "stereo_cam1_sbs_0002.mp4"
        
        sample_video(cam0_file1, frame_count=100)
        sample_video(cam0_file2, frame_count=150)
        sample_video(cam1_file1, frame_count=100)
        sample_video(cam1_file2, frame_count=150)
        
        # Discover videos
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.mp4",
            "stereo_cam1_sbs_*.mp4"
        )
        
        # Verify results
        assert 'cam0' in result
        assert 'cam1' in result
        assert len(result['cam0']) == 2
        assert len(result['cam1']) == 2
        
        # Verify cam0 segments
        assert result['cam0'][0].camera_id == 'cam0'
        assert result['cam0'][0].segment_number == 1
        assert result['cam0'][0].frame_count == 100
        assert result['cam0'][1].segment_number == 2
        assert result['cam0'][1].frame_count == 150
        
        # Verify cam1 segments
        assert result['cam1'][0].camera_id == 'cam1'
        assert result['cam1'][0].segment_number == 1
        assert result['cam1'][1].segment_number == 2
    
    def test_discover_videos_sorted_by_segment_number(self, temp_dir, sample_video):
        """Test that discovered videos are sorted by segment number."""
        # Create files in non-sequential order
        cam0_file3 = temp_dir / "stereo_cam0_sbs_0003.mp4"
        cam0_file1 = temp_dir / "stereo_cam0_sbs_0001.mp4"
        cam0_file2 = temp_dir / "stereo_cam0_sbs_0002.mp4"
        
        sample_video(cam0_file3, frame_count=50)
        sample_video(cam0_file1, frame_count=50)
        sample_video(cam0_file2, frame_count=50)
        
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.mp4",
            "stereo_cam1_sbs_*.mp4"
        )
        
        # Verify segments are sorted
        assert len(result['cam0']) == 3
        assert result['cam0'][0].segment_number == 1
        assert result['cam0'][1].segment_number == 2
        assert result['cam0'][2].segment_number == 3
    
    def test_discover_videos_with_no_matching_files(self, temp_dir):
        """Test discovering videos when no files match the patterns."""
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.mp4",
            "stereo_cam1_sbs_*.mp4"
        )
        
        assert result['cam0'] == []
        assert result['cam1'] == []
    
    def test_discover_videos_with_non_matching_files(self, temp_dir, sample_video):
        """Test that non-matching files are ignored."""
        # Create files that don't match the pattern
        other_file = temp_dir / "other_video.mp4"
        sample_video(other_file, frame_count=50)
        
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.mp4",
            "stereo_cam1_sbs_*.mp4"
        )
        
        assert result['cam0'] == []
        assert result['cam1'] == []
    
    def test_discover_videos_with_invalid_directory(self):
        """Test that InputDirectoryError is raised for non-existent directory."""
        from src.error_handling import InputDirectoryError
        
        non_existent = Path("/non/existent/directory")
        
        with pytest.raises(InputDirectoryError, match="Directory does not exist"):
            VideoDiscovery.discover_videos(
                non_existent,
                "stereo_cam0_sbs_*.mp4",
                "stereo_cam1_sbs_*.mp4"
            )
    
    def test_discover_videos_with_file_instead_of_directory(self, temp_dir):
        """Test that InputDirectoryError is raised when path is a file, not a directory."""
        from src.error_handling import InputDirectoryError
        
        file_path = temp_dir / "test.txt"
        file_path.write_text("test")
        
        with pytest.raises(InputDirectoryError, match="Path is not a directory"):
            VideoDiscovery.discover_videos(
                file_path,
                "stereo_cam0_sbs_*.mp4",
                "stereo_cam1_sbs_*.mp4"
            )
    
    def test_discover_videos_supports_avi_format(self, temp_dir, sample_video):
        """Test that AVI format is supported."""
        cam0_file = temp_dir / "stereo_cam0_sbs_0001.avi"
        sample_video(cam0_file, frame_count=50)
        
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.avi",
            "stereo_cam1_sbs_*.avi"
        )
        
        assert len(result['cam0']) == 1
        assert result['cam0'][0].file_path.suffix == '.avi'
    
    def test_get_frame_count_with_valid_video(self, temp_dir, sample_video):
        """Test getting frame count from a valid video file."""
        video_path = temp_dir / "test_video.mp4"
        sample_video(video_path, frame_count=42)
        
        frame_count = VideoDiscovery.get_frame_count(video_path)
        
        assert frame_count == 42
    
    def test_get_frame_count_with_non_existent_file(self):
        """Test getting frame count from non-existent file returns 0."""
        non_existent = Path("/non/existent/video.mp4")
        
        frame_count = VideoDiscovery.get_frame_count(non_existent)
        
        assert frame_count == 0
    
    def test_get_frame_count_with_invalid_video(self, temp_dir):
        """Test getting frame count from invalid video file returns 0."""
        invalid_video = temp_dir / "invalid.mp4"
        invalid_video.write_text("This is not a video file")
        
        frame_count = VideoDiscovery.get_frame_count(invalid_video)
        
        assert frame_count == 0
    
    def test_validate_segment_pairing_with_perfect_pairs(self):
        """Test validation when all segments are perfectly paired."""
        cam0_segments = [
            VideoSegment('cam0', 1, Path('cam0_1.mp4'), 100),
            VideoSegment('cam0', 2, Path('cam0_2.mp4'), 100),
            VideoSegment('cam0', 3, Path('cam0_3.mp4'), 100),
        ]
        cam1_segments = [
            VideoSegment('cam1', 1, Path('cam1_1.mp4'), 100),
            VideoSegment('cam1', 2, Path('cam1_2.mp4'), 100),
            VideoSegment('cam1', 3, Path('cam1_3.mp4'), 100),
        ]
        
        warnings = VideoDiscovery.validate_segment_pairing(cam0_segments, cam1_segments)
        
        assert warnings == []
    
    def test_validate_segment_pairing_with_missing_cam1_segment(self):
        """Test validation when cam1 is missing a segment."""
        cam0_segments = [
            VideoSegment('cam0', 1, Path('cam0_1.mp4'), 100),
            VideoSegment('cam0', 2, Path('cam0_2.mp4'), 100),
            VideoSegment('cam0', 3, Path('cam0_3.mp4'), 100),
        ]
        cam1_segments = [
            VideoSegment('cam1', 1, Path('cam1_1.mp4'), 100),
            VideoSegment('cam1', 3, Path('cam1_3.mp4'), 100),
        ]
        
        warnings = VideoDiscovery.validate_segment_pairing(cam0_segments, cam1_segments)
        
        assert len(warnings) == 1
        assert "Segment 2 exists for cam0 but not for cam1" in warnings[0]
    
    def test_validate_segment_pairing_with_missing_cam0_segment(self):
        """Test validation when cam0 is missing a segment."""
        cam0_segments = [
            VideoSegment('cam0', 1, Path('cam0_1.mp4'), 100),
            VideoSegment('cam0', 3, Path('cam0_3.mp4'), 100),
        ]
        cam1_segments = [
            VideoSegment('cam1', 1, Path('cam1_1.mp4'), 100),
            VideoSegment('cam1', 2, Path('cam1_2.mp4'), 100),
            VideoSegment('cam1', 3, Path('cam1_3.mp4'), 100),
        ]
        
        warnings = VideoDiscovery.validate_segment_pairing(cam0_segments, cam1_segments)
        
        assert len(warnings) == 1
        assert "Segment 2 exists for cam1 but not for cam0" in warnings[0]
    
    def test_validate_segment_pairing_with_multiple_missing_segments(self):
        """Test validation with multiple missing segments on both sides."""
        cam0_segments = [
            VideoSegment('cam0', 1, Path('cam0_1.mp4'), 100),
            VideoSegment('cam0', 2, Path('cam0_2.mp4'), 100),
            VideoSegment('cam0', 5, Path('cam0_5.mp4'), 100),
        ]
        cam1_segments = [
            VideoSegment('cam1', 1, Path('cam1_1.mp4'), 100),
            VideoSegment('cam1', 3, Path('cam1_3.mp4'), 100),
            VideoSegment('cam1', 4, Path('cam1_4.mp4'), 100),
        ]
        
        warnings = VideoDiscovery.validate_segment_pairing(cam0_segments, cam1_segments)
        
        assert len(warnings) == 4
        # Check that warnings are sorted by segment number
        assert "Segment 2 exists for cam0 but not for cam1" in warnings[0]
        assert "Segment 5 exists for cam0 but not for cam1" in warnings[1]
        assert "Segment 3 exists for cam1 but not for cam0" in warnings[2]
        assert "Segment 4 exists for cam1 but not for cam0" in warnings[3]
    
    def test_validate_segment_pairing_with_empty_lists(self):
        """Test validation with empty segment lists."""
        warnings = VideoDiscovery.validate_segment_pairing([], [])
        
        assert warnings == []
    
    def test_extract_segment_number_from_standard_filename(self):
        """Test extracting segment number from standard filename format."""
        segment_num = VideoDiscovery._extract_segment_number("stereo_cam0_sbs_0042.mp4")
        
        assert segment_num == 42
    
    def test_extract_segment_number_with_multiple_numbers(self):
        """Test that the last number is extracted when multiple numbers exist."""
        segment_num = VideoDiscovery._extract_segment_number("cam0_123_segment_456.mp4")
        
        assert segment_num == 456
    
    def test_extract_segment_number_with_no_numbers(self):
        """Test extracting segment number from filename with no numbers."""
        segment_num = VideoDiscovery._extract_segment_number("video.mp4")
        
        assert segment_num is None
    
    def test_discover_videos_ignores_videos_with_zero_frames(self, temp_dir):
        """Test that videos with zero frames are ignored."""
        # Create an empty file (will have 0 frames)
        empty_video = temp_dir / "stereo_cam0_sbs_0001.mp4"
        empty_video.write_bytes(b'')
        
        result = VideoDiscovery.discover_videos(
            temp_dir,
            "stereo_cam0_sbs_*.mp4",
            "stereo_cam1_sbs_*.mp4"
        )
        
        # Should not include the empty video
        assert result['cam0'] == []


# Property-Based Tests

class TestVideoDiscoveryProperties:
    """Property-based tests for VideoDiscovery class using Hypothesis."""
    
    def create_test_video(self, path: Path, frame_count: int = 10):
        """Create a simple test video with specified frame count."""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(path), fourcc, 30.0, (640, 480))
        
        for i in range(frame_count):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
            out.write(frame)
        
        out.release()
    
    @given(
        cam0_segments=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=0,
            max_size=10,
            unique=True
        ),
        cam1_segments=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=0,
            max_size=10,
            unique=True
        ),
        num_non_matching=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_video_discovery_correctness(self, cam0_segments, cam1_segments, num_non_matching):
        """Property 1: Video Discovery Correctness
        
        **Validates: Requirements 1.1, 1.2**
        
        For any directory containing video files with various naming patterns,
        the video discovery process should only return files that match the
        specified camera patterns, grouped by camera ID, and sorted by segment
        number in ascending order.
        """
        # Create temporary directory for this test
        test_dir = Path(tempfile.mkdtemp())
        
        try:
            # Define patterns
            cam0_pattern = "stereo_cam0_sbs_*.mp4"
            cam1_pattern = "stereo_cam1_sbs_*.mp4"
            
            # Create matching cam0 video files
            created_cam0_segments = []
            for seg_num in cam0_segments:
                filename = f"stereo_cam0_sbs_{seg_num:04d}.mp4"
                video_path = test_dir / filename
                self.create_test_video(video_path, frame_count=10)
                created_cam0_segments.append(seg_num)
            
            # Create matching cam1 video files
            created_cam1_segments = []
            for seg_num in cam1_segments:
                filename = f"stereo_cam1_sbs_{seg_num:04d}.mp4"
                video_path = test_dir / filename
                self.create_test_video(video_path, frame_count=10)
                created_cam1_segments.append(seg_num)
            
            # Create non-matching files (should be ignored)
            for i in range(num_non_matching):
                # Use simple ASCII names that won't cause OpenCV issues
                non_matching_path = test_dir / f"other_video_{i}.mp4"
                self.create_test_video(non_matching_path, frame_count=5)
            
            # Discover videos
            result = VideoDiscovery.discover_videos(test_dir, cam0_pattern, cam1_pattern)
            
            # Property 1: Only matching files are returned
            assert 'cam0' in result, "Result should contain 'cam0' key"
            assert 'cam1' in result, "Result should contain 'cam1' key"
            
            # Verify correct number of segments discovered
            assert len(result['cam0']) == len(created_cam0_segments), \
                f"Expected {len(created_cam0_segments)} cam0 segments, got {len(result['cam0'])}"
            assert len(result['cam1']) == len(created_cam1_segments), \
                f"Expected {len(created_cam1_segments)} cam1 segments, got {len(result['cam1'])}"
            
            # Property 2: Files are grouped by camera
            for segment in result['cam0']:
                assert segment.camera_id == 'cam0', \
                    f"All cam0 segments should have camera_id='cam0', got '{segment.camera_id}'"
            
            for segment in result['cam1']:
                assert segment.camera_id == 'cam1', \
                    f"All cam1 segments should have camera_id='cam1', got '{segment.camera_id}'"
            
            # Property 3: Files are sorted by segment number in ascending order
            cam0_segment_numbers = [seg.segment_number for seg in result['cam0']]
            cam1_segment_numbers = [seg.segment_number for seg in result['cam1']]
            
            assert cam0_segment_numbers == sorted(cam0_segment_numbers), \
                f"cam0 segments should be sorted by segment number, got {cam0_segment_numbers}"
            assert cam1_segment_numbers == sorted(cam1_segment_numbers), \
                f"cam1 segments should be sorted by segment number, got {cam1_segment_numbers}"
            
            # Property 4: Segment numbers match what we created
            assert set(cam0_segment_numbers) == set(created_cam0_segments), \
                f"cam0 segment numbers should match created segments"
            assert set(cam1_segment_numbers) == set(created_cam1_segments), \
                f"cam1 segment numbers should match created segments"
            
            # Property 5: All discovered segments have valid frame counts
            for segment in result['cam0'] + result['cam1']:
                assert segment.frame_count > 0, \
                    f"Segment {segment.segment_number} should have positive frame count, got {segment.frame_count}"
                assert segment.file_path.exists(), \
                    f"Segment file path should exist: {segment.file_path}"
        
        finally:
            # Cleanup
            shutil.rmtree(test_dir)
